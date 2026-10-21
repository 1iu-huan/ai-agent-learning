
import os
from typing import TypedDict, Literal
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import StateGraph, START, END

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

vectorstore = Chroma(#向量存储
    persist_directory="./chroma_db",
    collection_name="my_docs",
    embedding_function=embeddings,
)

#定义一个“全局共享数据篮子”（在 LangGraph 里叫 State / 状态）
#它的作用是立规矩。它告诉 PyCharm 和开发者：“这个字典里只能装下面这几样东西，而且类型必须对”。
class QAState(TypedDict):
    question: str#用户问题。类型是str
    route: str          # "rag" / "chat" / "reject"          路由决策
    docs: list #检索到的资料。类型是列表（list）
    answer: str#最终回答

def route_question(state: QAState):#分类员      接收全局共享的“数据篮子” QAState
    """路由节点：判断问题该走哪条路"""
    prompt = f"""判断这个问题属于哪一类，只输出一个词：
- rag：需要查企业知识库（考勤、请假、产品价格等）
- chat：闲聊或通用问候
- reject：明显超出知识库范围（如公司年会、竞争对手对比）

问题：{state['question']}"""#从“数据篮子”里把用户刚才问的问题掏出来，塞进提示词里。

    r = llm.invoke(prompt).content.strip().lower()#r 这个变量里，大概率只有 "rag"、"chat" 或 "reject" 这三个词之一。
    route = "rag" if "rag" in r else ("chat" if "chat" in r else "reject")
    #如果 r 里面包含 'rag' 这个词，那就判为 rag；如果包含 'chat'，判为 chat；如果什么都不是，为了安全起见，直接判为 'reject'（拒答）。”
    return {"route": route}#

def retrieve(state: QAState):#检索   图书管理员
    #拿到用户的问题，去向量数据库里把最相关的资料翻出来，然后把资料塞进“全局数据篮子”里，传给下一个节点。
    #现在篮子里有question和route
    docs = vectorstore.similarity_search(state["question"], k=6) # ← 你的库只有 6 块，用 6
    #vectorstore.similarity_search()，LangChain 靠这个函数，在底层自动帮你算向量、查 Chroma、按相似度排序。
    return {"docs": [d.page_content for d in docs]}
    #docs 里装的不是纯字符串，而是 LangChain 封装好的 Document 对象（里面既有文本，也有元数据）。
    #d.page_content 就是把里面的纯文本（也就是你当初切好的那一段段话）抠出来。

def generate(state: QAState):#有question和docs    ！！！查资料generate节点
    context = "\n".join(state["docs"])#取出检索到的文本列表；"\n".join(...)：用换行符 \n 把这 6 段话拼接成一个大字符串
    answer = llm.invoke(f"根据资料回答，标注依据：\n{context}\n\n问题：{state['question']}").content
    return {"answer": answer}

def chat_node(state: QAState):#！！！闲聊chat节点
    return {"answer": llm.invoke(state["question"]).content}#返回文本

def reject_node(state: QAState):#！！！reject节点
    return {"answer": "我没有找到相关资料。"}

#！！！
#-> Literal[...]：这是一个类型提示（Type Hint）；这个函数执行完之后，返回值只能是这三个字符串中的一个（要么是 retrieve，要么是 chat_node，要么是 reject_node）。
#[state["route"]；相当于一个查字典的过程
#当流程走到 route 节点后，不要去固定的下一个节点，而是去执行 pick 函数。pick 返回了哪个字符串，你就去哪个节点。
#决策路由函数
def pick(state: QAState) -> Literal["retrieve", "chat_node", "reject_node"]:
    return {"rag": "retrieve", "chat": "chat_node", "reject": "reject_node"}[state["route"]]

#画图
g = StateGraph(QAState)
#g.add_node("route", route_question) 的潜台词是：“以后流程走到叫 route 的工位，就执行 route_question 这个函数。”
g.add_node("route", route_question)#工位；add_node(名字（工位名字）, 函数)
g.add_node("retrieve", retrieve)
g.add_node("generate", generate)
g.add_node("chat_node", chat_node)
g.add_node("reject_node", reject_node)

#连线
g.add_edge(START, "route")# 起点连到 route

# ★ 今天唯一的新东西
#g.add_conditional_edges("route", pick)：这是条件边
#pick返回的字符串，系统拿到这个字符串，就把数据传送到对应的工位。
g.add_conditional_edges("route", pick)#

#连线
#g.add_edge("retrieve", "generate")：这是固定边。
g.add_edge("retrieve", "generate")#retrieve 连到 generate
g.add_edge("generate", END)
g.add_edge("chat_node", END)
g.add_edge("reject_node", END)

#compile()负责把之前定义的节点（Nodes）和边（Edges）进行静态校验，确保没有孤立节点或死循环
#确保没有孤立节点或死循环，然后将图结构实例化编译为一个可执行的对象
#只有编译后的对象才能调用 .invoke() 或 .stream() 来接收初始状态，并驱动整个状态机运转。
app = g.compile()

for q in ["病假工资怎么算？", "你好", "公司年会在哪办？"]:
    print(q, "->", app.invoke({"question": q})["answer"][:50])
    #.invoke(...)：按下了启动按钮。
    #{"question": q}：你把初始的“数据篮子”扔进机器的入口（START）
    #LangGraph 拿到这个篮子，开始按照你画的图跑：先分拣（route），再查库（retrieve），再生成（generate），最后到达终点（END）。跑完之后，它把装满数据的最终篮子返回给你。
    #app.invoke()执行完后得到一个完整的最终状态字典（包含 question, route, docs, answer）
    #["answer"]：从返回的字典中，精准提取出 answer 这个键对应的值（也就是那段长长的回答文本）。
    #app.invoke(),就是启动流水线，按照节点一步一步到达END节点，途中经过的节点相当于执行的函数。
    """
    LangGraph 采用了声明式的设计。
    刚才那段 add_node 和 add_edge 的代码，
    只是在声明和构建一个状态机的拓扑图（拓扑结构），此时并没有执行任何业务逻辑。
    直到调用 .compile() 将图编译为可执行对象，
    并在之后调用 .invoke() 注入初始 State 时，
    系统才会沿着既定的边和条件路由，真正开始执行各个节点函数并流转数据。
    """

"""
print("问答助手已启动（输入 exit 退出）")
print("-" * 50)

while True:
    try:
        q = input("\n你：").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n再见。")
        break

    if not q:
        continue
    if q.lower() in ("exit", "quit", "q", "退出"):
        print("再见。")
        break

    try:
        out = app.invoke({"question": q})
    except Exception as e:
        print(f"出错了：{e}")
        continue

    print(f"[路由: {out['route']}]")
    print(f"助手：{out['answer']}")
"""