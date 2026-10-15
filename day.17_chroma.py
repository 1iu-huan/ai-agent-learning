import os
from urllib import response

import chromadb
import math

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
#初始化智谱客户端
client = OpenAI(
    api_key=os.getenv("ZHIPU_API_KEY"),
    base_url="https://open.bigmodel.cn/api/paas/v4/"
)
#把文字变为向量
def get_embedding(text):
    response = client.embeddings.create(
        model = "embedding-2",
        input = text,
    )
    return response.data[0].embedding

#初始化 Chroma 本地客户端（chromadb.PersistentClient(...)）（数据会保存在 ./chroma_db 文件夹里）
#PersistentClient 会把数据写进硬盘，重启电脑也在。
chroma_client = chromadb.PersistentClient(path="./chroma_db")
#获取或创建一个集合，后面的存(add)和查(query)都要用到
#get_or_create_collection 获取或创建一个名为 my_docs 的集合
collection = chroma_client.get_or_create_collection(name="my_docs")
#准备数据：模拟 3 个切好的文档块
chunks = [
    "员工迟到或早退超过30分钟，按事假半天处理。",
    "公司为正式员工缴纳养老保险、医疗保险和住房公积金。",
    "智服通专业版每月899元，支持20个并发会话，含数据分析功能。"
]
#生成 ID 和 向量
#D 和内容是通过“位置（索引）”一一对应的。你把它们同时传给 collection.add()，Chroma 就在内部把它们绑定在一起了。
ids = [f'chunk_{i}' for i in range(len(chunks))]
embeddings = [get_embedding(chunk) for chunk in chunks]

#存入 Chroma
#建立映射关系（标签（ids）、内容（documents）和检索索引（embeddings））
collection.add(#这三个参数必须“位置对齐”
    documents = chunks,#内容，切好的文本块
    embeddings = embeddings,#书的检索标签（向量）
    ids = ids,#书（块）的唯一编号
)

print(f'已成功传入{len(chunks)}个文档快到Chroma!')
#测试语义检索
query = "迟到会扣钱吗？"
query_embedding = get_embedding(query)

#拿着用户问题的向量，去chroma仓库里，找出最相似的2个文档块
#collection.query()Chroma自带的检索方法
results = collection.query(
    query_embeddings = [query_embedding],#Chroma 的 query 方法支持批量查询（比如一次查 3 个问题）。为了统一格式，它要求你传一个列表。
    n_results=2
)#当运行完这行代码，results 是一个字典

print(f"\n🔍 查询：{query}")
print("最相关的文档块：")
#results['documents'] 是从 Chroma 查询结果里，专门掏出“原始文本内容”那一列。
#results 是一个字典（字典用方括号 [] 取值），'documents' 是里面的一个键（Key）
#results['documents']是个双层列表
for i, doc in enumerate(results['documents'][0]):#拿到第一个问题的结果（一维列表：['文档1', '文档2']）
    print(f"{i+1}. {doc}")

print("原始结构：", results['documents'])#拿到整个检索结果（二维列表）
print(results["documents"][0][0])#取出最相似的那一条原文