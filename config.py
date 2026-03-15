import os
from pathlib import Path

os.environ["TMP_FILE_DIR"] = "./tmp"

os.environ["SOFFICE_PATH"] = ""

# 嵌入模型的api key
os.environ["EMBEDDING_API_KEY"] = ""

os.environ["OUTPUT_DIR"] = "./output"

# 视觉语言模型配置
os.environ['VLLM_MODEL_API_KEY'] = ""
os.environ['VLLM_MODEL_URL'] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
os.environ['VLLM_MODEL_NAME'] = "qwen2.5-vl-3b-instruct"

def config_init():
    # 确保临时文件目录存在
    tmp_file_dir = Path(os.environ["TMP_FILE_DIR"])
    if not os.path.exists(tmp_file_dir):
        os.makedirs(tmp_file_dir, exist_ok=True)

    # 确保输出目录存在
    output_dir = Path(os.environ["OUTPUT_DIR"])
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    # 生成PPStructure管线
    from paddleocr import PPStructureV3
    # pipeline = PPStructureV3(use_table_recognition=False)
    pipeline = PPStructureV3()

    from core.utils.handler import set_ppstructure_pipeline
    set_ppstructure_pipeline(pipeline)