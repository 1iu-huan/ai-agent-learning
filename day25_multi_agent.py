# -*- coding: utf-8 -*-
"""
day25_multi_agent.py —— 三 Agent 协作（研究员 / 写作者 / 评审员）

核心认知：多 Agent 不是新东西，就是 Day 4 的条件边 + 循环。
    START → plan → research → writer → reviewer ─┬─(pass)──→ END
                     ↑                            │
                     └──────────(revise)──────────┘

三个设计要点（面试会问）：
  1. 交接用结构化数据（JSON），不用自然语言 —— 自然语言会丢上下文
  2. 每个节点单一职责，输出字段明确
  3. 必须有终止条件（最多 3 轮），否则无限循环烧钱

运行：
    python day25_multi_agent.py
"""

import json
import os
import re
from typing import Literal, TypedDict

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import END, START, StateGraph

load_dotenv()

# ---------------------------------------------------------------------------
# 环境
# ---------------------------------------------------------------------------
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

# 成本单价（deepseek-flash 非高峰，人民币/百万 token）
PRICE_IN = 1.08 / 1_000_000
PRICE_OUT = 4.32 / 1_000_000


# ---------------------------------------------------------------------------
# 调用统计：多 Agent 最容易被忽略的就是成本
# ---------------------------------------------------------------------------
class Tracker:
    def __init__(self):#初始化
        self.calls = 0
        self.in_tokens = 0
        self.out_tokens = 0

    def note(self, msg, label=""):#记账员
        self.calls += 1
        u = getattr(msg, "usage_metadata", None) or {}   #u是字典
        #getattr(msg, "usage_metadata", None)：安全地去取这个属性，如果有就拿出来，如果没有就返回 None。
        self.in_tokens += u.get("input_tokens", 0)
        #.get(..., 0)：同样的安全操作。如果字典里没有这个数据，默认返回 0，防止程序崩溃。
        self.out_tokens += u.get("output_tokens", 0)
        if label:#标签
            print(f"    · {label}: 输入 {u.get('input_tokens', 0):>4} / 输出 {u.get('output_tokens', 0):>3} token")

    def reset(self):
        """每次新任务前清零，避免多次运行的统计混在一起。"""
        self.calls = 0
        self.in_tokens = 0
        self.out_tokens = 0

    #@property（属性装饰器）
    #加了 @property 之后，你直接写 tracker.cost（不带括号）就能拿到结果，看起来就像一个变量，实际上跑了一段计算逻辑。
    @property
    def cost(self):#计算
        return self.in_tokens * PRICE_IN + self.out_tokens * PRICE_OUT

    def report(self):#打印账单
        return (
            f"模型调用 {self.calls} 次 | "
            f"token 输入 {self.in_tokens} / 输出 {self.out_tokens} | "
            f"花费约 ¥{self.cost:.4f}"
        )


tracker = Tracker()


def ask(prompt: str, label: str = "") -> str: #统一调度的大管家
    """统一的模型调用入口，顺便记账。"""
    msg = llm.invoke(prompt)
    tracker.note(msg, label)
    return (msg.content or "").strip()#相当于 msg.content.strip()，做了一道防御
    #(msg.content or "")：如果是 None，就替换成空字符串。

def extract_json(text: str): #专治大模型胡言乱语的清洗工
    """从模型输出里抠出 JSON（容忍 ```json 包裹和前后解释文字）。"""
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)#在text里找
    #(?:json)?：表示 json 这个词是可选的；(.*?)：把代码块里面的内容抓出来
    #\s* 的作用就是：“吃掉”这里可能出现的所有空格、换行符或缩进。
    #re.S:加上它，你的 (.*?) 才能跨行把整个大括号里的 JSON 完整抓取下来（因为Markdown代码块经常包含多行文本）
    if fenced:
        text = fenced.group(1)#group(1) 就是把括号里抓到的纯内容取出来
    m = re.search(r"(\{.*\}|\[.*\])", text, re.S)#强行抓取
    #\{.*\}：匹配从第一个 { 开始，到最后一个 } 结束的所有内容（JSON 对象）；\|：或者
    #\[.*\]：匹配从第一个 [ 开始，到最后一个 ] 结束的所有内容（JSON 数组）；
    if not m:
        return None
    try:
        return json.loads(m.group(1))#json.loads() 尝试转换成 Python 字典/列表
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------------------
# State：节点之间传递的全部数据
# ---------------------------------------------------------------------------
class ReportState(TypedDict):
    topic: str              # 用户给的主题
    sub_questions: list     # 研究员拆出的子问题
    docs: list              # 检索到的原文片段
    facts: list             # [{"claim": "...", "source": "文档N"}]  ← 交接的核心
    report: str             # 写作者产出的报告
    verdict: str            # "pass" / "revise"
    issues: list            # 评审意见
    rounds: int             # 已迭代轮数
    max_rounds: int         # 最大迭代轮数（调用时可覆盖）


# ---------------------------------------------------------------------------
# 节点 1：拆解主题
# ---------------------------------------------------------------------------
def plan(state: ReportState):#任务拆解员
    print("\n[研究员] 拆解主题...")
    prompt = f"""你是研究员。请把下面这个主题拆成 3 个适合去查资料库的子问题。

主题：{state['topic']}

只输出 JSON 数组，不要解释，不要 markdown 代码块。格式：
["子问题1", "子问题2", "子问题3"]"""

    data = extract_json(ask(prompt, "拆解主题"))
    #ask(...)：调用大模型（同时记账）
    #extract_json(...)：用上一条你学的正则大法，把大模型可能带的废话剥得干干净净，只留纯正的 Python 列表或字典。

    if not isinstance(data, list) or not data:#isinstance(data, list) 检查是不是列表，not data 检查是不是为空。
        # 兜底：拆不出来就用主题本身
        data = [state["topic"]]

    subs = [str(x) for x in data][:3]#数据清洗

    for i, s in enumerate(subs, 1):#遍历打印出来，方便你在控制台查看它拆得合不合理。
        print(f"    {i}. {s}")
    return {"sub_questions": subs}
    #把拆好的子问题列表，写进全局状态 ReportState 的 sub_questions 键里，传给下一个节点。


# ---------------------------------------------------------------------------
# 节点 2：检索 + 抽取事实
# ---------------------------------------------------------------------------
def research(state: ReportState):
    print("\n[研究员] 检索资料并提取事实...")
    #去重检索
    seen = set()#set 是 Python 的一种内置数据结构，中文叫集合
    docs = []
    #拿出上一步拆解出的 3 个子问题，挨个去查。
    for q in state["sub_questions"]:
        for d in vectorstore.similarity_search(q, k=6):
            key = d.page_content[:50]
            #截取前 50 个字作为指纹，如果在 seen 里见过，就不往 docs 里加了
            if key not in seen:
                seen.add(key)
                docs.append(d.page_content)


    context = "\n\n".join(
        f"【文档{i + 1}】{c}" for i, c in enumerate(docs)
    )

    prompt = f"""你是研究员。请从下面的资料中提取与主题相关的事实，每条事实必须标明来自哪个文档编号。

主题：{state['topic']}

资料：
{context}

只输出 JSON 数组，不要解释，不要 markdown 代码块。格式：
[{{"claim": "事实内容", "source": "文档1"}}]

要求：
- 只提取资料里明确写了的内容，不要推测
- 最多 8 条
- source 必须是上面出现过的文档编号"""

    facts = extract_json(ask(prompt, "提取事实")) or []
    if not isinstance(facts, list):
        facts = []
    facts = [f for f in facts if isinstance(f, dict) and f.get("claim")][:8]
    #遍历列表里每一个元素，只有满足“它是字典（dict）且里面有 claim 字段”的元素才会保留，
    #并且最后再截取前 8 条（[:8]）。这一行直接把任何可能导致后续崩溃的脏数据全部洗干净了。

    print(f"    提取到 {len(facts)} 条事实，来源文档 {len(docs)} 段")
    return {"docs": docs, "facts": facts}


# ---------------------------------------------------------------------------
# 节点 3：写报告
# ---------------------------------------------------------------------------
def writer(state: ReportState):
    rounds = state.get("rounds", 0) + 1
    print(f"\n[写作者] 撰写报告（第 {rounds} 轮）...")

    #格式化事实清单
    facts_text = "\n".join(
        f"- {f.get('claim')}（来源：{f.get('source', '未标注')}）"
        for f in state["facts"]
    )

    issues = state.get("issues") or []
    issues_text = ("\n上一轮评审意见（请重点修正）：\n" + "\n".join(f"- {i}" for i in issues)) if issues else ""

    prompt = f"""你是写作者。请基于下面的事实清单写一份简洁的报告。

主题：{state['topic']}

事实清单：
{facts_text}
{issues_text}

要求：
- 用 Markdown 格式，分 2-3 个小节
- 每个结论后面用（来源：文档N）标注出处
- 只能使用事实清单里的信息，不要编造
- 控制在 400 字以内"""

    report = ask(prompt, "撰写报告")
    return {"report": report, "rounds": rounds}


# ---------------------------------------------------------------------------
# 节点 4：评审
# ---------------------------------------------------------------------------
def reviewer(state: ReportState):
    print(f"\n[评审员] 审核第 {state.get('rounds', 1)} 轮报告...")

    prompt = f"""你是严格的评审员。请审核下面这份报告。

事实清单（唯一可信来源）：
{json.dumps(state['facts'], ensure_ascii=False, indent=1)}


报告：
{state['report']}

审核标准：
1. 报告里的每个结论是否都能在事实清单里找到依据（有没有编造）
2. 是否都标注了来源
3. 是否覆盖了主要事实

只输出 JSON，不要解释，不要 markdown 代码块。
如果通过：{{"pass": true, "issues": []}}
如果不通过：{{"pass": false, "issues": ["问题1", "问题2"]}}"""

    data = extract_json(ask(prompt, "评审"))
    if not isinstance(data, dict):
        data = {"pass": True, "issues": []}      # 解析失败就放行，避免死循环

    #评估
    verdict = "pass" if data.get("pass") else "revise"
    issues = data.get("issues") or []

    if verdict == "pass":
        print("    ✅ 审核通过")
    else:
        print("    ❌ 需要修改：")
        for i in issues:
            print(f"       - {i}")

    return {"verdict": verdict, "issues": issues}


# ---------------------------------------------------------------------------
# 条件边：决定是结束还是打回重写
# ---------------------------------------------------------------------------
#Literal["writer", "__end__"]：类型提示，约束这个函数只能返回这两个字符串。
def after_review(state: ReportState) -> Literal["writer", "__end__"]:
    # 终止条件 1：审核通过
    if state.get("verdict") == "pass":
        return END
    # 终止条件 2：轮数用尽（防止无限循环）
    if state.get("rounds", 0) >= state.get("max_rounds", 3):
        print("\n⚠️ 已达最大轮数，强制输出（未通过审核）")
        return END
    return "writer"          # ← 这就是"循环"：指回写作者


# ---------------------------------------------------------------------------
# 组装
# ---------------------------------------------------------------------------
graph = StateGraph(ReportState)
graph.add_node("plan", plan)
graph.add_node("research", research)
graph.add_node("writer", writer)
graph.add_node("reviewer", reviewer)

graph.add_edge(START, "plan")
graph.add_edge("plan", "research")
graph.add_edge("research", "writer")
graph.add_edge("writer", "reviewer")
graph.add_conditional_edges("reviewer", after_review)

app = graph.compile()


if __name__ == "__main__":
    topic = "公司考勤与请假制度综述"

    print("=" * 64)
    print(f"主题：{topic}")
    print("=" * 64)

    result = app.invoke({"topic": topic, "rounds": 0, "issues": []})

    print("\n" + "=" * 64)
    print("最终报告")
    print("=" * 64)
    print(result["report"])

    print("\n" + "=" * 64)
    print("运行统计")
    print("=" * 64)
    print(f"迭代轮数：{result['rounds']}")
    print(f"事实条数：{len(result.get('facts', []))}")
    print(tracker.report())
