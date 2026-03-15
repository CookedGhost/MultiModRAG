from app import app

from core import file_handle

@app.command(name='upload_file', description='上传文件到知识库中')
def upload_file(file: str):
    """
    上传文件到知识库中
    
    Args:
        file (str): 文件路径
    """
    # Here you would add the logic to handle the file uploads
    file_handle.upload_file(file)

@app.command(name='upload_dir', description='上传文件夹到知识库中')
def upload_dir(dir: str):
    """
    上传文件夹到知识库中
    
    Args:
        dir (str): 文件夹路径
    """
    # Here you would add the logic to handle the file uploads
    file_handle.upload_dir(dir)