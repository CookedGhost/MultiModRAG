import base64
from pathlib import Path
import requests
import json
import os
from chromadb import PersistentClient

def vectors_query(inputs: [], api_key: str):
    """
    使用Jina-Embedding-V4在线API获取向量
    Args:
        inputs (list): 数据列表，每个元素的格式应该为```{"iamge": base64编码}或{"text": 文本字符串}```
        api_key (str): API密钥
    Returns:
        Tuple[list,str] :
        list: 向量列表, str: 错误信息（如果有），如果没有错误则为None
    """
    try:
        # 调用Jina V4 API获取向量
        url = "https://api.jina.ai/v1/embeddings"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        data = {
            "model": "jina-embeddings-v4",
            "task": "retrieval.query",
            "input": inputs
        }

        response = requests.post(url, headers=headers, data=json.dumps(data))
        result = response.json()

        if 'data' in result:
            embeddings = [item['embedding'] for item in result['data']]
            msg = None
        else:
            # 处理错误或意外响应
            #print(f"❌ 向量获取发生错误:\n{result}")
            embeddings = []
            msg = f"向量获取发生错误:\n{result}"
        return embeddings, msg
    except Exception as e:
        #print(f"❌ 向量获取时出错:\n{e}")
        return [], f"向量获取时出错: \n{e}"

def embed_to_chroma(persist_dir: str, embeddings: [], documents: [], metadatas: [], ids: []):
    """
    将向量数据存储到Chroma数据库中
    Args:
        persist_dir (str): 持久化目录路径
        embeddings (list): 向量列表
        documents (list): 对应的原始文本/描述列表
        metadatas (list): 元数据信息列表
        ids (list): 唯一标识符列表
    """
    if len(embeddings) == 0 or len(documents) == 0 or len(metadatas) == 0 or len(ids) == 0:
        return 
    # 连接至Chroma并存入向量

    # 连接或创建Chroma客户端
    client = PersistentClient(path=persist_dir)

    # 获取或创建一个集合（Collection）
    collection = client.get_or_create_collection(name="multimodal_collection")

    # 将数据添加到集合中
    collection.add(
        embeddings=embeddings,  # 从Jina API获取的向量列表
        documents=documents,     # 对应的原始文本/描述
        metadatas=metadatas,    # 元数据信息
        ids=ids                 # 唯一标识符
    )

def search_in_chroma_with_embedding(persist_dir: str, query_embedding: [], top_k: int = 5, condition = {}):
    """
    在Chroma数据库中搜索与查询向量最相似的条目
    Args:
        persist_dir (str): 持久化目录路径
        query_embedding (list): 查询向量
        top_k (int): 返回的最相似条目数量，默认为5
        condition (dict): 搜索条件
    Returns:
        list: 包含最相似条目的列表，每个条目包含文档、元数据和ID等信息
    """
    # 连接至Chroma并执行搜索
    client = PersistentClient(path=persist_dir)
    collection = client.get_collection(name="multimodal_collection")
    
    # 执行查询
    if condition == {}:
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=top_k
        )
    else:
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=top_k,
            where=condition
        )
    
    return results

def msg_log(log_entry, log_dir:str, file_name: str):
    """
    记录消息日志
    Args:
        log_entry (dict): 日志内容，应该包含需要记录的信息
        log_dir (str): 日志文件存储目录
        file_name (str): 日志文件名
    """
    # 创建日志目录
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, f"{file_name}")

    # 写入日志文件
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            json.dump(log_entry, f, ensure_ascii=False)
            f.write('\n')
    except Exception as e:
        print(f"日志写入失败: {e}")


