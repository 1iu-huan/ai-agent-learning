import os
import chromadb
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key = os.getenv("ZHIPU_API_KEY"),
    base_url = "https://open.bigmodel.cn/api/paas/v4/"
)

deepseek_client = OpenAI(
    api_key = os.getenv("DEEPSEEK_API_KEY"),
    base_url = "https://api.deepseek.com"
)

#获取向量
def get_embedding(text):
    response = client.embeddings.create(
        model = "embedding-2",
        input = text
    )
    return response.data[0].embedding

#创建一个本地持久化的Chroma客户端。连接数据库
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name='my_docs')


def rag_query(question,n_results = 2):
    #问路（算向量）
    query_embedding = get_embedding(question)
    #找资料（查库）
    results = collection.query(
        query_embeddings = [query_embedding],
        n_results = n_results
    )
    docs = results['documents'][0]#Chroma库根据语义相似度，把最相关的文档传给docs(列表）

    #把一堆零散的文档块，排版成一段人类和 AI 都能轻松看懂的结构化文本。
    context = '\n'.join(f'【文档 {i+1}】{doc}' for i, doc in enumerate(docs))
    #如：【文档 1】员工迟到或早退超过30分钟，按事假半天处理。

    prompt = f"""你是一个企业知识库助手。请根据下面提供的参考资料回答用户问题。
    请根据资料的上下文进行合理的逻辑推断和归纳总结，不要直接照搬原文。
    如果你从资料中推导出了答案，请在回答中引用原文作为依据。
    只有当资料中完全没有相关信息时，才回复“我没有找到相关资料”。
    #注入上下文
    参考资料：
    {context}
    用户问题：{question}
    """
    response = deepseek_client.chat.completions.create(
        model = "deepseek-flash",
        messages = [{"role" : "user", "content" : prompt}],
        temperature = 0.1
    )
    #response.choices[0].message.content：从 API 的返回包裹里，掏出大模型生成的最终文本回答。
    #docs：把你检索到的原始文档块也一起返回。（（while 循环里）要打印“引用来源”）
    return response.choices[0].message.content, docs


print("===企业文档问答助手已启动（输入exit退出）===")
while True:
    user_input = input("\n你：")
    if user_input.lower() in ["exit", "quit"]:
        print("再见！")
        break

    print("检索中...")
    #rag_query return了两个，answer接住了response，source_docs接住了docs
    answer,source_docs = rag_query(user_input)

    print(f'\nAI: {answer}')
    print(f"\n📚 引用来源：")
    for i,doc in enumerate(source_docs):
        print(f"[{i+1}] {doc[:60]}...")

