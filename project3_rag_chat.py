# -*- coding: utf-8 -*-


import os

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI, OpenAIEmbeddings


load_dotenv()

llm = ChatOpenAI(
    model="deepseek-flash",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
    temperature=0,
    extra_body={"thinking": {"type": "disabled"}},
)

embeddings = OpenAIEmbeddings(
    model="embedding-2",
    api_key=os.getenv("ZHIPU_API_KEY"),
    base_url="https://open.bigmodel.cn/api/paas/v4/",
)

vectorstore = Chroma(
    persist_directory="./chroma_db",
    collection_name="my_docs",
    embedding_function=embeddings,
)

# 【改】k=6：库小的时候宁可按全量取，否则正确答案排第 4-6 名就彻底漏掉
retriever = vectorstore.as_retriever(search_kwargs={"k": 6})


# 【改】把 Document 列表转成干净文本，并加编号方便引用
def format_docs(docs):
    if not docs:
        return "（未检索到相关资料）"
    return "\n\n".join(f"【文档{i + 1}】{d.page_content}" for i, d in enumerate(docs))


# ---------------------------------------------------------------------------
# 问题改写：让"那基础版呢"变成能检索的完整问题
# ---------------------------------------------------------------------------
REWRITE_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "根据对话历史，把用户最新问题改写成不依赖上下文、可独立检索的问题。"
     "只输出改写后的问题本身，不要回答问题，不要解释。"
     "如果问题本身已经完整，原样输出。"),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{question}"),
])
rewrite_chain = REWRITE_PROMPT | llm | StrOutputParser()


def to_retrieval_query(payload):
    """输入是整条链的输入字典，输出是送去检索的字符串。"""
    question = payload["question"]
    history = payload.get("history") or []

    if not history:                     # 首轮不用改写，省一次调用
        return question

    try:
        rewritten = rewrite_chain.invoke({
            "question": question,
            "history": history[-4:],    # 只给最近 2 轮，避免被早期内容带偏
        }).strip()
        # 防御：改写结果异常就回退原问题，不能让主链路挂掉
        if not rewritten or len(rewritten) > 100 or "没有找到" in rewritten:
            return question
        return rewritten
    except Exception:
        return question


# ---------------------------------------------------------------------------
# 主链：结构和你原来的一样，只是多了 history
# ---------------------------------------------------------------------------
prompt = ChatPromptTemplate.from_messages([
    ("system",
     "你是企业知识库助手。只依据给定资料回答，并在结论后标注依据的文档编号，如 [文档1]。"
     "允许基于资料做合理的逻辑推理与归纳，但必须说明依据原文。"
     "资料中没有相关信息、也无法从中推断时，只回复：我没有找到相关资料。"),
    MessagesPlaceholder(variable_name="history"),      # 【改】历史注入点
    ("human", "参考资料：\n{context}\n\n用户问题：{question}"),
])

chain = (
    {
        # 检索时用改写后的问题
        "context": RunnableLambda(to_retrieval_query) | retriever | format_docs,
        # 生成时用原始问题（保留顾客的原话）
        "question": lambda x: x["question"],
        "history": lambda x: x.get("history", []),
    }
    | prompt
    | llm
    | StrOutputParser()
)


# ---------------------------------------------------------------------------
# 交互循环：自动累积上下文
# ---------------------------------------------------------------------------
MAX_HISTORY_MESSAGES = 8       # 最多保留最近 4 轮，防止越聊越贵

history: list = []             # 【改】上下文就存在这里，程序运行期间一直有效

print("企业知识库助手已启动（输入 exit / 退出 结束）")
print("-" * 60)

while True:
    try:
        question = input("\n你：").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n再见。")
        break

    if not question:
        continue
    if question.lower() in ("exit", "quit", "q", "退出"):
        print("再见。")
        break

    try:
        answer = chain.invoke({"question": question, "history": history})
    except Exception as e:
        print(f"出错了：{e}（可以换个问法再试）")
        continue

    print(f"助手：{answer}")

    # 【改】把这轮问答存进历史，下一轮自动带上
    history.append(HumanMessage(content=question))
    history.append(AIMessage(content=answer))

    # 裁剪：只保留最近的 8 条（4 轮）
    if len(history) > MAX_HISTORY_MESSAGES:
        history[:] = history[-MAX_HISTORY_MESSAGES:]
