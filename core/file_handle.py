import os

from core.utils import helps, embeddings, handler

embedding_api_key = os.environ["EMBEDDING_API_KEY"]
vdb_persist_dir = "./output/vdb/chroma_jina"

def upload_file(file_path):
    """
    上传文件
    
    Args:
        file_path (str): 文件路径
    """

    handle_files([{"type": helps.file_classification(file_path), "path": file_path}])

def upload_dir(dir_path):
    """
    上传文件夹
    
    Args:
        dir_path (str): 文件夹路径
    """
    print(f"开始扫描目录: {dir_path}")
    file_list = []
    can_handle_nums = 0
    for root, dirs, files in os.walk(dir_path):
        for file in files:
            file_path = os.path.join(root, file)
            #print(f"发现文件: {file_path} - {file_classification(file_path)}")
            file_type = helps.file_classification(file_path)
            if file_type != helps.FileType.OTH:
                can_handle_nums += 1
            file_list.append({"type": file_type, "path": file_path})
    print(f"扫描完成，共发现文件 {len(file_list)} 个，实际可处理文件 {can_handle_nums} 个。")
    handle_files(file_list)

def handle_files(file_list):
    """
    处理文件列表
    
    Args:
        file_list (list): 文件路径列表，结构为 ```[{"type": FileType, "path": file_path}, ...]```
    """
    for file_info in file_list:
        file_path = file_info["path"]
        file_type = file_info["type"]
        print("="*60)
        print(f"正在处理文件: {file_path} - {file_type}")

        if file_type == helps.FileType.TXT:
            msg = handler.handle_single_txt_file(
                source=file_path, 
                file_path=file_path, 
                vdb_persist_dir=vdb_persist_dir, 
                embedding_api_key=embedding_api_key
            )
            if msg is not None:
                print(f"处理文件 {file_path} 时发生错误: {msg}")
            else:
                print(f"文件 {file_path} 处理完成。")
        elif file_type == helps.FileType.IMG:
            msg = handler.handle_single_img_file(
                source=file_path, 
                file_path=file_path, 
                vdb_persist_dir=vdb_persist_dir, 
                embedding_api_key=embedding_api_key,
                page_id=0
            )
            if msg is not None:
                print(f"处理文件 {file_path} 时发生错误: {msg}")
            else:
                print(f"文件 {file_path} 处理完成。")
        elif file_type == helps.FileType.PDF:
            msg = handler.handle_single_pdf_file(
                source=file_path, 
                file_path=file_path, 
                vdb_persist_dir=vdb_persist_dir, 
                embedding_api_key=embedding_api_key
            )
            if msg is not None:
                print(f"处理文件 {file_path} 时发生错误: {msg}")
            else:
                print(f"文件 {file_path} 处理完成。")
        elif file_type in [helps.FileType.WRD, helps.FileType.PPT]:
            msg = handler.handle_single_wrd_or_ppt_file(
                source=file_path, 
                file_path=file_path, 
                vdb_persist_dir=vdb_persist_dir, 
                embedding_api_key=embedding_api_key
            )
            if msg is not None:
                print(f"处理文件 {file_path} 时发生错误: {msg}")
            else:
                print(f"文件 {file_path} 处理完成。")

        print("="*60)

