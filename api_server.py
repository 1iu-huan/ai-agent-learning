import os
import chromadb
from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ---------- 初始化两个客户端 ----------
client = OpenAI(
    api_key=os.getenv("ZHIPU_API_KEY"),
    base_url="https://open.bigmodel.cn/api/paas/v4/"
)
deepseek_client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

def get_embedding(text):
    response = client.embeddings.create(model="embedding-2", input=text)
    return response.data[0].embedding

# ---------- 连接 Chroma ----------
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name="my_docs")

# ---------- 定义请求体 ----------
#BaseModel 是 Pydantic（FastAPI 背后的数据校验库）提供的基类(“自动校验数据格式”)
class QuestionRequest(BaseModel):
    question: str
    history: list = []
# ---------- 定义 FastAPI 应用 ----------
app = FastAPI(title="企业文档问答 API", version="1.0")#Web应用实例


#async 是 Python 里的异步编程关键字。用一句大白话解释：它让程序在等待网络请求时，不傻等，而是去处理别的事情。
@app.post("/ask")#装饰器（Decorator）
async def ask(request: QuestionRequest):#async def：定义了一个异步函数
    """接收问题，返回 RAG 回答"""
    question = request.question
    history = request.history

    # 1. 查询改写
    if history:
        history_text = "\n".join(
            [f"{m['role']}: {m['content']}" for m in history[-4:]]#挑出最近 4 条历史，拼成一段纯文本，为下一步让大模型改写问题做准备。
        )
        rewrite_prompt = f"""根据下面的对话历史，把用户最新的问题改写成不依赖上下文、可独立检索的问题。
只输出改写后的问题，不要解释。

对话历史：
{history_text}
用户最新问题：{question}
改写后的问题："""
        r = deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": rewrite_prompt}],
            temperature=0
        )
        standalone_question = r.choices[0].message.content.strip()
    else:
        standalone_question = question

    # 2. 检索
    query_embedding = get_embedding(standalone_question)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=2
    )
    docs = results['documents'][0]
    context = "\n".join([f"【文档{i+1}】{doc}" for i, doc in enumerate(docs)])

    # 3. 生成回答
    prompt = f"""你是一个企业知识库助手。请根据下面提供的参考资料回答用户问题。
请根据资料的上下文进行合理的逻辑推断和归纳总结，不要直接照搬原文。
如果你从资料中推导出了答案，请在回答中引用原文作为依据。
只有当资料中完全没有相关信息时，才回复"我没有找到相关资料"。

参考资料：
{context}

用户问题：{question}
"""
    response = deepseek_client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1
    )

    return {
        "answer": response.choices[0].message.content,
        "sources": docs,
        "standalone_question": standalone_question
    }

#这是一个 GET 接口，路径是 /health。它的作用是让运维人员或监控系统随时检查你的服务是否还活着。
@app.get("/health")
async def health():
    """健康检查接口"""
    return {"status": "ok", "docs_count": collection.count()}