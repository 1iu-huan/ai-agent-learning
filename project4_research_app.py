# -*- coding: utf-8 -*-
"""
project4_research_app.py —— 深度研究助手（项目四）

在 Day 5 的三 Agent 图上加一层产品界面：
    · 输入主题 → 实时显示每个 Agent 的进度 → 输出带出处的报告
    · 报告可下载为 Markdown
    · 展示迭代轮数、调用次数、本次花费

复用 day25_multi_agent.py 里已经调好的图，不重复实现节点逻辑。

运行：
    streamlit run project4_research_app.py
"""

import streamlit as st
from day19_ingest_data import load_data
import day25_multi_agent as core#导入后端多智能体核心逻辑

st.set_page_config(page_title="深度研究助手", page_icon="🔍", layout="wide")

# 云端首次启动时 chroma_db 是空的，自动重建（复用 day19 的导入逻辑）
# 没有这一段，部署上去会出现"提取到 0 条事实"的空报告
try:
    if core.vectorstore._collection.count() == 0:
        with st.spinner("首次启动：正在导入知识库…"):
            load_data()
        st.rerun()#数据导入完了之后，强制网页刷新一次。
except Exception as e:
    st.warning(f"知识库自动导入失败：{e}")

NODE_LABEL = {
    "plan": "拆解主题",
    "research": "检索并提取事实",
    "writer": "撰写报告",
    "reviewer": "审核报告",
}

# ---------------------------------------------------------------------------
# 侧边栏
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ 设置")
    max_rounds = st.slider(#滑动条
        "最大迭代轮数", min_value=1, max_value=5, value=3,
        help="评审不通过时自动打回重写；达到上限强制输出。",#
    )
    st.divider()#在网页界面上画一条水平的“分割线”
    try:
        #st.metric：这是 Streamlit 里专门显示大数字的组件
        st.metric("知识库文档块", core.vectorstore._collection.count())#数量
    except Exception:
        st.caption("知识库状态不可用")
    st.caption("数据来源：./chroma_db（员工手册 / 产品介绍 / 常见问题）")
    st.divider()
    st.markdown(
        "**流程**\n\n"
        "1. 研究员拆主题为子问题\n"
        "2. 逐个子问题检索并抽取事实\n"
        "3. 写作者基于事实写报告\n"
        "4. 评审员检查是否都有出处\n"
        "5. 不通过 → 打回重写（最多 N 轮）"
    )

# ---------------------------------------------------------------------------
# 主区
# ---------------------------------------------------------------------------
st.title("🔍 深度研究助手")
st.caption("研究员 → 写作者 → 评审员 三角色协作｜评审不通过会自动打回重写")

#st.text_input(...)：这是 Streamlit 提供的文本输入组件。它会在网页中央画出一个宽大的输入框。
topic = st.text_input(
    "研究主题",
    placeholder="例如：公司考勤与请假制度综述",#（提示文字）
    label_visibility="collapsed",#“隐藏掉‘研究主题’这四个字”。
)

run = st.button("开始研究", type="primary", use_container_width=True)

if run:
    if not topic.strip():
        st.warning("请先输入研究主题")
        st.stop()

    core.tracker.reset()      # 每次运行独立计数

    #st.status：这是 Streamlit 里的一个高级 UI 组件，它会生成一个可折叠的“实时进度框”
    #expanded=True：默认展开。用户能直观看到里面一行一行蹦出来的文字（比如“拆解主题完成”、“检索资料完成”）。
    status = st.status("研究进行中…", expanded=True)
    bar = st.progress(0.0)#在网页上画一根进度条
    #构造交给后端的“初始数据篮子”！
    state = {"topic": topic.strip(), "rounds": 0, "issues": [], "max_rounds": max_rounds}
    step = 0#记录当前跑了几步，方便计算进度条的百分比。

    try:
        # stream_mode="updates"：每完成一个节点就吐出一块，用来做进度显示
        #每跑完一个节点（比如拆题完了、查资料完了），就立刻把这一步更新的数据（update）吐出来（yield）
        for chunk in core.app.stream(state, stream_mode="updates"):
            for node, update in chunk.items():
                #chunk.items()：把数据包拆开
                #node 是节点的名字（比如 "plan"）
                #update 是这个节点干完活后修改的数据（比如 {"sub_questions": [...]}）
                if not update:
                    continue
                step += 1
                label = NODE_LABEL.get(node, node)#把英文 "plan" 翻译成中文 "拆解主题"。
                detail = ""#空字符串
                if node == "plan" and update.get("sub_questions"):
                    detail = "：" + "；".join(update["sub_questions"][:3])
                elif node == "research" and "facts" in update:
                    detail = f"：提取 {len(update['facts'])} 条事实"
                elif node == "writer" and update.get("rounds"):
                    detail = f"（第 {update['rounds']} 轮）"
                elif node == "reviewer":
                    detail = "：通过" if update.get("verdict") == "pass" else "：不通过，打回重写"

                #status.write(...)：把刚才拼好的中文，一行行写进前面那个“进度框”里。
                #**:加粗
                status.write(f"**{label}**{detail}")
                #防呆设计！ 每次步数加 1，进度条往前推 12%（大约 8 步跑满）
                bar.progress(min(0.95, step * 0.12))
                #state = {**state, **update}：Python 的字典解包语法
                #因为 stream 吐出来的 update 只有局部数据，
                #这里手动把最新数据合并到前端的 state 中，保证后续提取 state['report'] 是完整的
                state = {**state, **update}
    except Exception as e:
        status.update(label="运行出错", state="error")
        st.error(f"研究失败：{e}")
        st.stop()

    bar.progress(1.0)
    passed = state.get("verdict") == "pass"

    #更新那个一开始创建的实时进度框（st.status）
    status.update(
        label="研究完成（已通过审核）" if passed else "研究完成（未通过审核，已达最大轮数）",

        # 告诉 Streamlit：“这个组件已经彻底完事了”
        #它会自动把原本转圈的“Loading”图标，变成一个绿色的对勾（✅）。
        state="complete",
        expanded=False,#进度框折叠
    )

    # ---------- 报告 ----------
    st.divider()
    #把写好的报告渲染到网页上。
    st.markdown(state.get("report") or "（没有产出报告）")

    #把网页横向切成 3 等份的列
    c1, c2, c3 = st.columns(3)


    c1.metric("迭代轮数", state.get("rounds", 0))
    c2.metric("事实条数", len(state.get("facts", [])))
    c3.metric("本次花费", f"¥{core.tracker.cost:.4f}")

    # ---------- 引用 ----------
    with st.expander(f"📚 事实与出处（{len(state.get('facts', []))} 条）", expanded=False):
        for f in state.get("facts", []):
            st.markdown(f"- {f.get('claim')} — `{f.get('source', '未标注')}`")

    # ---------- 评审意见 ----------
    if not passed and state.get("issues"):
        st.warning("未通过的评审意见：" + "；".join(state["issues"]))

    # ---------- 下载 -------------
    st.download_button(
        "⬇️ 下载报告（Markdown）",
        data=state.get("report") or "",
        file_name=f"研究报告-{state.get('topic', 'report')}.md",
        mime="text/markdown",
        use_container_width=True,
    )
    st.caption(core.tracker.report())
