from enum import Enum
import time
import base64
import os
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter

class FileType(Enum):
    TXT = 'txt' # 纯文本文件
    IMG = 'img' # 图片文件
    WRD = 'wrd' # 文档文件，包括docx、doc等
    PPT = 'ppt' # 演示文件，包括pptx、ppt等
    PDF = 'pdf' # 文档文件，包括pdf等
    XLS = 'xls' # 表格文件，包括csv、xlsx、xls等
    VID = 'vid' # 视频文件，包括mp4、avi、mkv、mov
    AUD = 'aud' # 音频文件，包括mp3、wav、aac、flac、ogg等
    OTH = 'oth' # 其他文件

ext_dict = {
    FileType.TXT: ['.txt', '.md'],
    FileType.IMG: ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg'],
    FileType.WRD: ['.docx', '.doc'],
    FileType.PPT: ['.pptx', '.ppt'],
    FileType.PDF: ['.pdf'],
    FileType.XLS: ['.csv', '.xlsx', '.xls'],
    FileType.VID: ['.mp4', '.avi', '.mkv', '.mov', '.flv'],
    FileType.AUD: ['.mp3', '.wav', '.aac', '.flac', '.ogg']
}

def file_classification(file_path):
    """
    根据文件扩展名对文件进行分类
    
    Args:
        file_path (str): 文件路径
        
    Returns:
        file_type (FileType): 文件类型枚举值
    """
    
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    
    if ext in ext_dict[FileType.TXT]:
        return FileType.TXT
    elif ext in ext_dict[FileType.IMG]:
        return FileType.IMG
    elif ext in ext_dict[FileType.WRD]:
        return FileType.WRD
    elif ext in ext_dict[FileType.PPT]:
        return FileType.PPT
    elif ext in ext_dict[FileType.PDF]:
        return FileType.PDF
    elif ext in ext_dict[FileType.XLS]:
        return FileType.XLS
    elif ext in ext_dict[FileType.VID]:
        return FileType.VID
    elif ext in ext_dict[FileType.AUD]:
        return FileType.AUD
    else:
        return FileType.OTH

class MetadataFactory:
    def __init__(self):
        """
        **元数据工厂类，提供创建不同类型文件元数据的方法**\n
        在创建元数据时所需要的source和save_path参数含义为：
        - **source**: 原始文件的来源，可以是文件路径、URL链接等，用于标识数据的来源位置。
        - **save_path**: 处理后文件的保存路径，可以是本地路径或云存储路径，用于标识数据的存储位置。
        """
        pass
    
    def create_metadata(self, source: str, save_path: str):
        return {
            "source": source,
            "save_path": save_path,
            "create_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        }

    def create_txt_metadata(self, source: str, save_path: str, chunk_id: int, description: str):
        """
        创建文本文件块的元数据，包含基本信息和文本特有的字段
        Args:
            source (str): 原始文件的来源
            save_path (str): 处理后文件的保存路径
            chunk_id (int): 文本块的块号，用于标识文本在原文件中的位置，从1开始递增
            description (str): 文本块的描述信息
        """
        return self.create_metadata(source, save_path) | {
            "type": FileType.TXT.name,
            "chunk_id": chunk_id,
            "description": description
        }
    
    def create_img_metadata(self, source: str, save_path: str, page_id: int, description: str):
        """
        创建图片文件的元数据，包含基本信息和图片特有的字段
        Args:
            source (str): 原始文件的来源
            save_path (str): 处理后文件的保存路径
            page_id (int): 图片所在页码，用于标识图片在原文件中的位置，从1开始递增；如果图片不来自文档，则page_id可以设置为0或-1表示无效
            description (str): 图片的描述信息（可为空）
        """
        return self.create_metadata(source, save_path) | {
            "type": FileType.IMG.name,
            "page_id": page_id,
            "description": description
        }

def txt_file_split(
    file_path: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 100
) -> list[str]:
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,          # 使用字符长度计数
        separators=["\n\n", "\n", " ", ""]  # 优先按段落、换行、空格切分
    )
    
    chunks = splitter.split_text(text)
    return chunks

def image_to_base64(image_path, use_data_url=True):
    """
    将图片文件转换为Base64字符串
    Args:
        image_path (str): 图片文件路径
        use_data_url (bool): 是否返回Data URL格式的字符串，默认为True
    """
    # 读取图片文件为二进制数据
    with open(image_path, 'rb') as image_file:
        image_binary = image_file.read()

    # 进行Base64编码
    base64_bytes = base64.b64encode(image_binary)
    base64_string = base64_bytes.decode('utf-8')  # 转换为字符串

    # 根据选择返回不同格式
    if use_data_url:
        # 获取文件扩展名以确定MIME类型
        ext = Path(image_path).suffix.lower()
        mime_type = f"image/{ext[1:]}" if ext in ext_dict[FileType.IMG] else 'image/jpeg'
        return f"data:{mime_type};base64,{base64_string}"
    else:
        return base64_string





