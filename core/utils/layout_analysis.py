import fitz  # PyMuPDF
import os
from PIL import Image
from pathlib import Path
import subprocess
from tqdm import tqdm
import base64
import shutil
from openai import OpenAI
import textwrap

import core.utils.helps as helps

os.environ['CUDA_VISIBLE_DEVICES'] = '1'
client = OpenAI(
    api_key = os.environ['VLLM_MODEL_API_KEY'],
    base_url = os.environ['VLLM_MODEL_URL'],
)

prompt_text = textwrap.dedent("""
    请简要描述图片中的内容，生成的回答中需要包含图片中的重点与关键内容。
    只需要回答你所描述的内容，无需附带其他追加性的回答。
""")

VLLM_MODEL_NAME = os.environ['VLLM_MODEL_NAME']

def pdf2images(pdf_path, output_dir=None, dpi=200, 
                          output_format='png', start_page=0, end_page=None):
    """
    将PDF文件的每一页转换为图片
    
    Args:
        pdf_path (str): PDF文件路径
        output_dir (str): 输出目录，默认与PDF文件同目录
        dpi (int): 输出图片的DPI，默认200
        output_format (str): 输出图片格式，支持png/jpg/jpeg/tiff/bmp
        start_page (int): 开始页码（从0开始）
        end_page (int): 结束页码（不包含），默认None表示到最后
    Returns:
        image_infos (list of dict): 包含转换后图片信息的列表，每个字典包含页码、路径、尺寸和格式等信息，结构为
        \n```[{'page': int, 'path': str, 'size': (width, height), 'format': str}, ...]
    """
    
    # 检查PDF文件是否存在
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
    
    # 设置输出目录
    if output_dir is None:
        # 默认输出到PDF文件同目录下的pdf_images文件夹
        pdf_dir = os.path.dirname(pdf_path)
        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
        output_dir = os.path.join(pdf_dir, f"{pdf_name}_images")
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 打开PDF文件
    pdf_document = fitz.open(pdf_path)
    
    # 确定页码范围
    total_pages = len(pdf_document)
    if end_page is None or end_page > total_pages:
        end_page = total_pages
    
    # 确保开始页码和结束页码有效
    if start_page < 0:
        start_page = 0
    if end_page < start_page:
        end_page = start_page + 1
    
    # 转换每一页
    image_infos = []
    
    for page_num in range(start_page, end_page):
        # 获取页面
        page = pdf_document[page_num]
        
        # 计算缩放因子：将PDF的72DPI转换为目标DPI
        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)
        
        # 将页面转换为图片（pixmap）
        pix = page.get_pixmap(matrix=mat, alpha=False)
        
        # 生成输出文件名
        output_filename = f"page{page_num+1:04d}.{output_format.lower()}"
        output_path = os.path.join(output_dir, output_filename)
        
        # 保存图片
        if output_format.lower() in ['jpg', 'jpeg']:
            # JPEG格式需要先转换为PIL图像
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img.save(output_path, 'JPEG', quality=95)
        else:
            # PNG等其他格式直接保存
            pix.save(output_path)
        
        image_infos.append({
            'page': page_num + 1,
            'path': output_path,
            'size': (pix.width, pix.height),
            'format': output_format
        })
        
        print(f"已转换第 {page_num+1} 页 -> {output_path} ({pix.width}x{pix.height})")
    
    # 关闭PDF文件
    pdf_document.close()
    
    return image_infos

def word_or_ppt2pdf(input_path: str, output_dir: str, soffice_path: str):
    """
    将Word或PowerPoint文件转换为PDF格式
    Args:
        input_path (str): 输入文件路径
        output_dir (str): 输出目录路径
        soffice_path (str): soffice可执行文件路径
    Returns:
        tuple (Tuple[Path, (str|None)]): 转换成功返回None，失败返回错误信息
    """
    # 构建输出文件名（与输入相同，但扩展名为 .pdf）
    output_pdf = Path(output_dir) / f"{Path(input_path).stem}.pdf"
    if output_pdf.exists():
        return output_pdf, None

    # 调用 soffice 命令
    cmd = [
        soffice_path,
        "--headless",           # 无界面模式
        "--convert-to", "pdf",  # 转换为 PDF
        "--outdir", str(output_dir),  # 输出目录
        str(input_path)         # 输入文件
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        #print(f"转换成功: {input_path} -> {output_pdf}")
        return output_pdf, None
    except subprocess.CalledProcessError as e:
        return output_pdf, f"转换失败 [{input_path}]: {e}"

def generate_image_description(image_path):
    if not os.path.exists(image_path):
        print(f"图片文件不存在: {image_path}")
        return "（图片文件不存在）"

    try:
        img_base64 = helps.image_to_base64(image_path)

        prompt = prompt_text

        response = client.chat.completions.create(
            model=VLLM_MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": img_base64}},
                    ],
                }
            ],
            temperature=0.3,
            max_tokens=4096,
        )

        content = response.choices[0].message.content
        description = content.strip() if content else "（模型未返回内容）"
        # print(f"✅ 图片描述生成成功: {image_path}")
        return description

    except Exception as e:
        print(f"❌ 生成失败: {e}")
        return f"【图片/表格描述】: （识别失败，原因：{str(e)[:100]}）"

def layout_analysis(pdf_path: str, pipeline, output_dir: str, img_output_dir: str, tmp_dir: str):
    """
    对PDF文件进行版面分析，分离文本和图片
    Args:
        pdf_path (str): PDF文件路径
        pipeline: PPStructureV3对象
        output_dir (str): 输出目录路径
        img_output_dir (str): 图片输出目录路径
        tmp_dir (str): 临时目录路径
    """
    # 分页切片
    page_infos = pdf2images(pdf_path = pdf_path, output_dir = img_output_dir)

    # 根据页面尺寸判断文档类型（宽大于高为PPT，反之为Word）
    width, height = page_infos[0]['size']
    if width < height:
        file_type = helps.FileType.WRD
    elif width > height:
        file_type = helps.FileType.PPT

    md_path_list = []
    
    # 版面分析
    for page_idx in tqdm(range(len(page_infos)), desc="版面分析中", unit="页"):
        page_path = page_infos[page_idx]["path"]
        page_name = Path(page_path).stem
        output = pipeline.predict(page_path)

        for res in output:
            for item_idx, item in enumerate(res['parsing_res_list']):
                item = item.to_dict()
                if item['label'] in ['chart', 'table', 'image']:
                    # Word文档中将图片等非文本元素替换为Markdown格式的图片链接，链接路径指向切页生成的图片
                    if file_type == helps.FileType.WRD:
                        img = item['image']['img']
                        save_img_name = f"page{page_idx+1:04d}_{item['label']}_{item_idx+1}.png"
                        img_dir_name = Path(img_output_dir).name
                        save_img_path = Path(img_dir_name) / save_img_name
                            
                        item['image']['path'] = save_img_path
                        img.save(Path(img_output_dir) / save_img_name, format="PNG")

                        item['label'] = 'text'
                        content = f"{'='*5}以下内容为图片简要描述{'='*5}\n"
                        content = content + generate_image_description(Path(img_output_dir) / save_img_name)
                        content = content + f'\n图片内更多细节请查看![{save_img_name}]({save_img_path})\n'
                        item['content'] = content
                    # PPT中直接忽略图片等非文本元素，不进行处理
                    elif file_type == helps.FileType.PPT:
                        item['label'] = 'none'
            
            res.save_to_markdown(save_path=output_dir)
            md_path_list.append(output_dir / f"{page_name}.md")
    
    assert len(page_infos) == len(md_path_list), "错误！文档页数与导出的Markdown文档数不一致！"

    # 将所有Markdown文档保存到一个文件中
    input_filename = Path(pdf_path).stem
    md_save_path = output_dir / f"{input_filename}.md"
    with open(md_save_path, 'w', encoding='utf-8') as f:
        for idx in range(len(md_path_list)):
            page_path = page_infos[idx]["path"]
            page_name = Path(page_path).stem
            with open(md_path_list[idx], 'r', encoding='utf-8') as tf:
                content = tf.read()
                f.write(content)
                if file_type == helps.FileType.PPT:
                    f.write(f"\n\n以上内容可参考图片: ![{page_name}]({page_path})\n\n")

    # 清理临时文件
    for temp_md in md_path_list:
        if os.path.exists(temp_md):
            os.remove(temp_md)
    tmp_img_dir = output_dir / "imgs"
    if os.path.exists(tmp_img_dir):
        shutil.rmtree(tmp_img_dir)
    if file_type == helps.FileType.WRD:
        for page_info in page_infos:
            page_path = page_info["path"]
            if os.path.exists(page_path):
                os.remove(page_path)
    print("临时文件清理完成")