# -*- coding: utf-8 -*-
"""
project3_rag_langchain_memory.py
用 LangChain + LangGraph 重写 RAG，并加上自动会话记忆。

和你原来那版的区别（每一处都有原因）：
  1. 补了 load_dotenv()          —— 原来靠 import eval_v2 的副作用，删了导入就崩
  2. 删了没用的导入              —— vectorstores / RecursiveCharacterTextSplitter / eval_v2
  3. 加了 format_docs()          —— 原来直接把 Document 对象塞进提示词，模型看到的是 repr
  4. k 从 3 调到 6               —— 知识库只有 6 个块，k=3 会漏掉正确答案
  5. 记忆改用 LangGraph          —— RunnableWithMessageHistory 已废弃
  6. 加了问题改写                —— 否则"那基础版呢"这类追问检索不到东西

运行：
    python project3_rag_langchain_memory.py
"""

import os
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

load_dotenv()

# ---------------------------------------------------------------------------
# 1. 模型与向量库
# ---------------------------------------------------------------------------
llm = ChatOpenAI(
    model="deepseek-flash",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",          # 结尾不要加斜杠
    temperature=0,
    extra_body={"thinking": {"type": "disabled"}},  # 关掉思考模式，降延迟和成本
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

# k 要比你以为的大。知识库小的时候尤其明显：
# 6 个块取 3 个 = 只看了一半，正确答案排第 4-6 名就彻底漏掉。
RETRIEVER_K = 6
retriever = vectorstore.as_retriever(search_kwargs={"k": RETRIEVER_K})


def format_docs(docs):
    """把 Document 列表转成干净文本。

    这一步不能省：直接把 docs 传给提示词，模型看到的是
    "Document(id='chunk_2', metadata={...}, page_content='...')"
    这种 Python repr，既浪费 token，又会诱导模型在答案里写 id。
    """
    if not docs:
        return "（未检索到相关资料）"
    return "\n\n".join(
        f"【文档{i + 1}】{d.page_content}" for i, d in enumerate(docs)
    )


# ---------------------------------------------------------------------------
# 2. 状态定义
# ---------------------------------------------------------------------------
class State(TypedDict):
    messages: Annotated[list, add_messages]   # 自动累积，不用手动 append
    standalone: str                            # 改写后的独立问题
    docs: list                                 # 本轮检索到的文档


# ---------------------------------------------------------------------------
# 3. 节点：问题改写（多轮追问的关键）
# ---------------------------------------------------------------------------
REWRITE_TEMPLATE = """根据对话历史，把用户最新问题改写成不依赖上下文、可独立检索的问题。

要求：
- 只输出改写后的问题本身，不要回答问题，不要解释。
- 如果问题本身已经完整，原样输出。

对话历史：
{history}

用户最新问题：{question}
改写后的问题："""

rewrite_chain = ChatPromptTemplate.from_template(REWRITE_TEMPLATE) | llm | StrOutputParser()


def prepare(state: State):
    """首轮不改写；有历史时结合最近 2 轮改写成独立问题。"""
    history = state["messages"][:-1]
    question = state["messages"][-1].content

    if not history:
        return {"standalone": question}

    recent = history[-4:]          # 只取最近 2 轮，避免被早期内容带偏
    history_text = "\n".join(
        f"{'用户' if m.type == 'human' else '助手'}：{m.content}" for m in recent
    )
    try:
        rewritten = rewrite_chain.invoke(
            {"history": history_text, "question": question}
        ).strip()
        # 防御：改写结果为空、过长、或明显是在回答而不是改写，就回退原问题
        if not rewritten or len(rewritten) > 100 or "没有找到" in rewritten:
            rewritten = question
    except Exception:
        rewritten = question
    return {"standalone": rewritten}


# ---------------------------------------------------------------------------
# 4. 节点：检索
# ---------------------------------------------------------------------------
def retrieve(state: State):
    query = state.get("standalone") or state["messages"][-1].content
    return {"docs": retriever.invoke(query)}


# ---------------------------------------------------------------------------
# 5. 节点：生成
# ---------------------------------------------------------------------------
ANSWER_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "你是企业知识库助手。只依据给定资料回答，并在结论后标注依据的文档编号，如 [文档1]。"
     "允许基于资料做合理的逻辑推理与归纳，但必须说明依据原文。"
     "资料中没有相关信息、也无法从中推断时，只回复：我没有找到相关资料。"),
    MessagesPlaceholder(variable_name="history"),
    ("human", "参考资料：\n{context}\n\n用户问题：{question}"),
])


def generate(state: State):
    history = state["messages"][:-1][-6:]      # 最近 3 轮作为上下文
    question = state["messages"][-1].content
    messages = ANSWER_PROMPT.format_messages(
        history=history,
        context=format_docs(state["docs"]),
        question=question,
    )
    return {"messages": [llm.invoke(messages)]}


# ---------------------------------------------------------------------------
# 6. 组装图 + 持久化
# ---------------------------------------------------------------------------
graph = StateGraph(State)
graph.add_node("prepare", prepare)
graph.add_node("retrieve", retrieve)
graph.add_node("generate", generate)

graph.add_edge(START, "prepare")
graph.add_edge("prepare", "retrieve")
graph.add_edge("retrieve", "generate")
graph.add_edge("generate", END)

# checkpointer 这一行就是"自动存储上下文"的全部秘密：
#   - 每步执行后自动保存状态
#   - 按 thread_id 隔离会话
#   - 换了进程还能续（换成 SqliteSaver / PostgresSaver 即可持久化到磁盘）
app = graph.compile(checkpointer=InMemorySaver())


def ask(question: str, thread_id: str = "default") -> str:
    """对外只暴露这一个函数。相同的 thread_id 自动共享上下文。"""
    result = app.invoke(
        {"messages": [HumanMessage(content=question)]},
        config={"configurable": {"thread_id": thread_id}},
    )
    return result["messages"][-1].content


if __name__ == "__main__":
    # 同一个 thread_id → 有上下文
    print("=" * 64)
    print("会话 A（同一会话，应该有上下文）")
    for q in ["入职满一年有几天年假？", "那需要提前多久申请？", "病假期间工资怎么算？"]:
        print(f"\n用户：{q}")
        print(f"助手：{ask(q, thread_id='session_A')}")

    # 换 thread_id → 上下文隔离
    print("\n" + "=" * 64)
    print("会话 B（新会话，不应该受 A 影响）")
    print(f"用户：那需要提前多久申请？")
    print(f"助手：{ask('那需要提前多久申请？', thread_id='session_B')}")

    # 查看某个会话存了什么
    print("\n" + "=" * 64)
    state = app.get_state({"configurable": {"thread_id": "session_A"}})
    print(f"会话 A 累积消息数：{len(state.values['messages'])}")
