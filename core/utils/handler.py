import time
import uuid
import os
import re
from pathlib import Path

import core.utils.helps as helps
from core.utils.embeddings import vectors_query, embed_to_chroma
from core.utils.layout_analysis import word_or_ppt2pdf, pdf2images, layout_analysis

layout_analysis_pipeline = None

EMBEDDINGS_QUERY_RETRY_COUNT = 4
EMBEDDINGS_QUERY_RETRY_DELAY = 0.3

def set_ppstructure_pipeline(pipeline):
    global layout_analysis_pipeline
    layout_analysis_pipeline = pipeline
    print("成功设置PP-Structure版面分析管道对象。")

def handle_single_txt_file(source, file_path, vdb_persist_dir, embedding_api_key):
    """
    处理单个文本文件的流程：切块、获取向量、存储到Chroma数据库
    Args:
        source (str): 原始文件路径或URL，用于标识数据来源
        file_path (str): 文本文件路径
        vdb_persist_dir (str): Chroma数据库持久化目录
        embedding_api_key (str): 获取向量的API密钥
    Returns:
        str: 处理结果消息，如果成功则为None，否则为错误信息
    """
    # 文本切块
    chunks = helps.txt_file_split(file_path)
    print(f"文本文件切分完成，共切分为 {len(chunks)} 个块。")
    print("正在获取文本块向量...")
    # 向量获取
    query_text = [{"text": chunk} for chunk in chunks]
    embeddings, msg = vectors_query(query_text, embedding_api_key)
    retry_count = EMBEDDINGS_QUERY_RETRY_COUNT
    retry_delay = EMBEDDINGS_QUERY_RETRY_DELAY
    while msg is not None and retry_count > 0:
        print("⚠️ 向量获取失败，正在重试...")
        time.sleep(retry_delay)
        embeddings, msg = vectors_query(query_text, embedding_api_key)
        retry_count -= 1
        retry_count *= 2
    if msg is not None:
        return msg
    # 准备元数据列表
    metadata_factory = helps.MetadataFactory()
    metadatas = [metadata_factory.create_txt_metadata(
            source=source, 
            save_path=file_path, 
            chunk_id=i + 1, 
            description=f"文本块 {i + 1}") 
            for i, chunk in enumerate(chunks)]
    for i, metadata in enumerate(metadatas):
        print(f"元数据 {i + 1}: {metadata}")

    # 为每个条目生成唯一ID
    ids = [str(uuid.uuid4()) for _ in range(len(chunks))]

    embed_to_chroma(
        persist_dir=vdb_persist_dir,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
        ids=ids)

    return None

def handle_single_img_file(source, file_path, vdb_persist_dir, embedding_api_key, page_id = 0):
    """
    处理单个图片文件的流程：获取向量、存储到Chroma数据库
    Args:
        source (str): 原始文件路径或URL，用于标识数据来源
        file_path (str): 图片文件路径
        vdb_persist_dir (str): Chroma数据库持久化目录
        embedding_api_key (str): 获取向量的API密钥
        page_id (int): 图片所在页码，用于标识图片在原文件中的位置，从1开始递增；如果图片不来自文档，则page_id可以设置为0或-1表示无效
    Returns:
        str: 处理结果消息，如果成功则为None，否则为错误信息
    """
    # 向量获取
    print("正在获取图片向量...")
    query = [{"image": helps.image_to_base64(file_path)}]  # 将图片转换为Base64编码
    embeddings, msg = vectors_query(query, embedding_api_key)
    retry_count = EMBEDDINGS_QUERY_RETRY_COUNT
    retry_delay = EMBEDDINGS_QUERY_RETRY_DELAY
    while msg is not None and retry_count > 0:
        print("⚠️ 向量获取失败，正在重试...")
        time.sleep(retry_delay)
        embeddings, msg = vectors_query(query, embedding_api_key)
        retry_count -= 1
        retry_count *= 2
    if msg is not None:
        return msg
    
    # 准备元数据列表，图片作为一个整体存储，块ID和描述信息可以根据实际需求设置
    description = f"图片地址<{file_path}>" + (f"，位于原文件<{source}>第{page_id}页" if page_id > 0 else "")
    metadata_factory = helps.MetadataFactory()
    metadatas = [metadata_factory.create_img_metadata(
            source=source, 
            save_path=file_path, 
            page_id=page_id, 
            description=description)]  
    # page_id=0表示无效

    for i, metadata in enumerate(metadatas):
        print(f"元数据 {i + 1}: {metadata}")

    # 为条目生成唯一ID
    ids = [str(uuid.uuid4())]

    embed_to_chroma(
        persist_dir = vdb_persist_dir, 
        embeddings = embeddings, 
        documents = [description], 
        metadatas = metadatas, 
        ids = ids)

    return None

def handle_single_pdf_file(source, file_path, vdb_persist_dir, embedding_api_key):
    """
    处理单个PDF文件的流程：切页并转换为图片，版面分析分离文本图片，获取向量、存储到Chroma数据库
    Args:
        source (str): 原始文件路径或URL，用于标识数据来源
        file_path (str): PDF文件路径
        vdb_persist_dir (str): Chroma数据库持久化目录
        embedding_api_key (str): 获取向量的API密钥
    Returns:
        str: 处理结果消息，如果成功则为None，否则为错误信息
    """
    try:
        # 设置输出目录
        input_filename = Path(file_path).stem
        output_root_dir = Path(os.environ["OUTPUT_DIR"])
        # output_dir = Path(f"output/{input_filename}")
        output_dir = Path(output_root_dir) / input_filename
        output_dir.mkdir(parents=True, exist_ok=True)

        img_dir_name = 'images'
        # img_output_dir = Path(f"output/{input_filename}/{img_dir_name}")
        img_output_dir = output_dir / img_dir_name
        img_output_dir.mkdir(parents=True, exist_ok=True)
        
        tmp_dir = Path(os.environ["TMP_FILE_DIR"])

        # 版面分析
        layout_analysis(
            pdf_path=file_path,
            pipeline=layout_analysis_pipeline,
            output_dir=output_dir,
            img_output_dir=img_output_dir,
            tmp_dir=tmp_dir
        )

        for root, dirs, files in os.walk(output_dir):
            for file in files:
                sub_file_path = os.path.join(root, file)
                print("-"*40)
                print(f"正在处理子文件: {sub_file_path}")
                sub_file_type = helps.file_classification(sub_file_path)
                if sub_file_type != helps.FileType.OTH:
                    try:
                        if sub_file_type == helps.FileType.TXT:
                            msg = handle_single_txt_file(
                                source=source, 
                                file_path=sub_file_path, 
                                vdb_persist_dir=vdb_persist_dir, 
                                embedding_api_key=embedding_api_key
                            )
                            if msg is not None:
                                print(f"处理子文件 {sub_file_path} 时发生错误: {msg}")
                        elif sub_file_type == helps.FileType.IMG:
                            # 计算page_id
                            sub_filename = os.path.basename(sub_file_path)

                            # 使用正则表达式匹配 "page" 后的数字
                            match = re.search(r'page(\d+)', sub_filename)
                            page_id = 0
                            if match:
                                num_str = match.group(1)  # '0001'
                                page_id = int(num_str)

                            msg = handle_single_img_file(
                                source=source, 
                                file_path=sub_file_path, 
                                vdb_persist_dir=vdb_persist_dir, 
                                embedding_api_key=embedding_api_key,
                                page_id=page_id
                            )
                            if msg is not None:
                                print(f"处理子文件 {sub_file_path} 时发生错误: {msg}")
                    except Exception as e:
                        print(f"处理子文件 {sub_file_path} 时出错: {str(e)}")
        

    except Exception as e:
        print(f"处理文件 {file_path} 时出错: {str(e)}")
    return None

def handle_single_wrd_or_ppt_file(source, file_path, vdb_persist_dir, embedding_api_key):
    """
    处理单个Word或PowerPoint文档的流程：转换为PDF，PDF切页并转换为图片，版面分析分离文本图片，获取向量、存储到Chroma数据库
    Args:
        source (str): 原始文件路径或URL，用于标识数据来源
        file_path (str): 文档文件路径
        vdb_persist_dir (str): Chroma数据库持久化目录
        embedding_api_key (str): 获取向量的API密钥
    Returns:
        str: 处理结果消息，如果成功则为None，否则为错误信息
    """
    # 设置输出目录
    input_filename = Path(file_path).stem
    output_root_dir = Path(os.environ["OUTPUT_DIR"])
    # output_dir = Path(f"output/{input_filename}")
    output_dir = Path(output_root_dir) / input_filename
    output_dir.mkdir(parents=True, exist_ok=True)

    # 将Word文档转换为PDF
    soffice_path = os.environ["SOFFICE_PATH"]
    pdf_path, msg = word_or_ppt2pdf(file_path, output_dir, soffice_path)
    if msg is not None:
        return msg

    handle_single_pdf_file(
        source=source,
        file_path=pdf_path,
        vdb_persist_dir=vdb_persist_dir,
        embedding_api_key=embedding_api_key
    )

    return None





        

