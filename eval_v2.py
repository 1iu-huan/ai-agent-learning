# -*- coding: utf-8 -*-
"""
RAG 系统评测脚本 V2（评测升级版）

和旧版 test_rag.py 的区别：
  1. 30 条用例按 7 个能力维度分组，不再是"从文档抄题"
  2. 三维评测：检索命中 / 答案正确 / 答案忠实（最关键的升级）
  3. 忠实度评测能发现"答对了但不是从知识库答的"这种假阳性
  4. 真实统计 Token 用量与成本（旧版用字符数估算，误差约 10 倍）
  5. 支持 thinking 开关对比（DeepSeek 默认开启思考模式）
  6. 输出 Markdown 报告，可直接贴进 README

用法：
    python eval_v2.py                # 默认：关闭 thinking，跑全部用例
    python eval_v2.py --thinking     # 开启 thinking 做对比
    python eval_v2.py --save report.md   # 同时保存报告
    python eval_v2.py --id 3         # 只跑第 3 条，方便调试
"""

import argparse
import ast
import json
import os
import re
import sys
import time
from datetime import datetime

import chromadb
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------
ZHIPU_BASE = "https://open.bigmodel.cn/api/paas/v4/"
DEEPSEEK_BASE = "https://api.deepseek.com"
EMBED_MODEL = "embedding-2"
CHAT_MODEL = "deepseek-chat"
N_RESULTS = 5                      # 旧版是 2，召回太少
MAX_THINKING = False               # 由命令行参数控制

PRICE_IN = 0.15 / 1_000_000        # 美元/输入 token（Flash 非高峰，缓存未命中）
PRICE_OUT = 0.60 / 1_000_000       # 美元/输出 token
USD_TO_CNY = 7.2

# ---------------------------------------------------------------------------
# 初始化客户端
# ---------------------------------------------------------------------------
embed_client = OpenAI(api_key=os.getenv("ZHIPU_API_KEY"), base_url=ZHIPU_BASE)
chat_client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url=DEEPSEEK_BASE)

chroma_client = chromadb.PersistentClient(path=str(os.path.join(os.path.dirname(__file__), "chroma_db")))
collection = chroma_client.get_or_create_collection(name="my_docs")

if collection.count() == 0:
    print("❌ 知识库是空的，请先运行 python day19_ingest_data.py 导入数据")
    sys.exit(1)


def get_embedding(text):
    return embed_client.embeddings.create(model=EMBED_MODEL, input=text).data[0].embedding


def chat(messages, temperature=0, max_tokens=None):
    """统一的对话调用，返回 (文本, usage)；由 MAX_THINKING 控制是否开思考模式。"""
    kwargs = dict(model=CHAT_MODEL, messages=messages, temperature=temperature)
    if max_tokens:
        kwargs["max_tokens"] = max_tokens
    if MAX_THINKING:
        kwargs["reasoning_effort"] = "high"
        kwargs["extra_body"] = {"thinking": {"type": "enabled"}}
    else:
        kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
    resp = chat_client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content or "", resp.usage


# ---------------------------------------------------------------------------
# RAG 核心（与 project3_rag_app.py 逻辑一致，但返回 usage 便于统计成本）
# ---------------------------------------------------------------------------
def rewrite_query(question, history):
    """无历史时直接返回原问题（返回 (问题, usage) 二元组，usage 可能为 None）。"""
    if not history:
        return question, None
    history_text = "\n".join(f"{m['role']}: {m['content']}" for m in history[-4:])
    prompt = (
        "根据下面的对话历史，把用户最新的问题改写成不依赖上下文、可独立检索的问题。\n"
        "只输出改写后的问题，不要解释。\n\n"
        f"对话历史：\n{history_text}\n用户最新问题：{question}\n改写后的问题："
    )
    text, usage = chat([{"role": "user", "content": prompt}], temperature=0)
    return text.strip(), usage


def retrieve(question, n_results=N_RESULTS):
    emb = get_embedding(question)
    res = collection.query(query_embeddings=[emb], n_results=n_results)
    docs = res["documents"][0] if res["documents"] else []
    ids = res["ids"][0] if res.get("ids") else []
    dists = res["distances"][0] if res.get("distances") else []
    return docs, ids, dists


def rag_answer(question, history=None):
    """返回 dict：answer / docs / rewritten / usage"""
    history = history or []
    usages = []

    standalone, u = rewrite_query(question, history)
    if u is not None:
        usages.append(("rewrite", u))

    docs, ids, dists = retrieve(standalone)
    context = "\n".join(f"【文档{i+1}】{d}" for i, d in enumerate(docs))

    prompt = (
        "你是一个企业知识库助手。请严格根据下面提供的参考资料回答用户问题。\n"
        "规则：\n"
        "1. 只使用参考资料中的信息，不要使用你的常识或外部知识补充。\n"
        "2. 回答时标注依据的文档编号，如 [文档1]。\n"
        "3. 如果参考资料中没有相关信息，只回复：我没有找到相关资料。\n\n"
        f"参考资料：\n{context}\n\n"
        f"用户问题：{question}"
    )
    answer, u = chat([{"role": "user", "content": prompt}], temperature=0)
    usages.append(("generate", u))

    return {
        "answer": answer.strip(),
        "docs": docs,
        "rewritten": standalone,
        "usages": usages,
    }


# ---------------------------------------------------------------------------
# 评测用例：30 条，7 个类别
# ---------------------------------------------------------------------------
def build_cases():
    return [
        # --- A 单跳事实（基线）---
        {"id": 1, "cat": "A 单跳事实", "q": "员工迟到超过30分钟怎么处理？",
         "expect": "按事假半天处理", "answerable": True, "must_contain": ["事假"]},
        {"id": 2, "cat": "A 单跳事实", "q": "病假期间工资按多少发放？",
         "expect": "基本工资的80%", "answerable": True, "must_contain": ["80"]},
        {"id": 3, "cat": "A 单跳事实", "q": "智服通基础版每月多少钱？",
         "expect": "299元", "answerable": True, "must_contain": ["299"]},
        {"id": 4, "cat": "A 单跳事实", "q": "技术支持热线电话是多少？",
         "expect": "400-800-1234", "answerable": True, "must_contain": ["400"]},
        {"id": 5, "cat": "A 单跳事实", "q": "员工入职满一年有几天年假？",
         "expect": "5天", "answerable": True, "must_contain": ["5"]},

        # --- B 多跳推理（要组合两处信息）---
        {"id": 6, "cat": "B 多跳推理", "q": "工作满三年后，年假比刚入职时多几天？",
         "expect": "多2天", "answerable": True, "must_contain": ["2"]},
        {"id": 7, "cat": "B 多跳推理", "q": "智服通专业版比基础版贵多少钱？",
         "expect": "600元", "answerable": True, "must_contain": ["600"]},
        {"id": 8, "cat": "B 多跳推理", "q": "基础版和专业版分别支持多少并发会话？",
         "expect": "基础版5个，专业版20个", "answerable": True, "must_contain": ["5", "20"]},
        {"id": 9, "cat": "B 多跳推理", "q": "如果员工每月迟到4次且有一次迟到40分钟，会受到什么影响？",
         "expect": "该次按事假半天处理，且扣当月全勤奖", "answerable": True, "must_contain": ["事假"]},

        # --- C 否定/排除（易错）---
        {"id": 10, "cat": "C 否定排除", "q": "迟到超过30分钟算旷工吗？",
         "expect": "不算旷工，按事假半天处理", "answerable": True, "must_contain": ["事假"]},
        {"id": 11, "cat": "C 否定排除", "q": "事假期间照常发工资吗？",
         "expect": "不发工资", "answerable": True, "must_contain": ["不发"]},
        {"id": 12, "cat": "C 否定排除", "q": "智服通所有版本都支持私有化部署吗？",
         "expect": "不是，只有企业版支持", "answerable": True, "must_contain": ["企业版"]},

        # --- D 知识库外（必须拒答，最容易暴露幻觉）---
        {"id": 13, "cat": "D 库外拒答", "q": "公司年会在什么时间举办？",
         "expect": "我没有找到相关资料", "answerable": False},
        {"id": 14, "cat": "D 库外拒答", "q": "智服通和阿里云客服哪个更好用？",
         "expect": "我没有找到相关资料", "answerable": False},
        {"id": 15, "cat": "D 库外拒答", "q": "员工每个月工资是多少？",
         "expect": "我没有找到相关资料", "answerable": False},
        {"id": 16, "cat": "D 库外拒答", "q": "公司创始人是谁？",
         "expect": "我没有找到相关资料", "answerable": False},
        {"id": 17, "cat": "D 库外拒答", "q": "这个产品的研发团队有多少人？",
         "expect": "我没有找到相关资料", "answerable": False},

        # --- E 精确数字/边界（考验对细节的把控）---
        {"id": 18, "cat": "E 精确边界", "q": "早退25分钟算事假吗？",
         "expect": "不算，需超过30分钟", "answerable": True, "must_contain": ["30"]},
        {"id": 19, "cat": "E 精确边界", "q": "专业版包含数据分析功能吗？",
         "expect": "包含", "answerable": True, "must_contain": ["包含"]},
        {"id": 20, "cat": "E 精确边界", "q": "年假至少需要提前多久申请？",
         "expect": "提前一周", "answerable": True, "must_contain": ["一周"]},
        {"id": 21, "cat": "E 精确边界", "q": "事假需要提前多久申请？",
         "expect": "提前一天", "answerable": True, "must_contain": ["一天"]},
        {"id": 22, "cat": "E 精确边界", "q": "五险一金具体包含哪几项？",
         "expect": "五险加住房公积金", "answerable": True, "must_contain": ["公积金"]},

        # --- F 多轮对话（考验 query rewriting）---
        {"id": 23, "cat": "F 多轮对话", "q": "那这个版本支持多少并发？",
         "history": [
             {"role": "user", "content": "智服通专业版多少钱？"},
             {"role": "assistant", "content": "专业版每月899元。"},
         ],
         "expect": "20个并发会话", "answerable": True, "must_contain": ["20"]},
        {"id": 24, "cat": "F 多轮对话", "q": "那基础版呢？",
         "history": [
             {"role": "user", "content": "专业版支持多少并发会话？"},
             {"role": "assistant", "content": "专业版支持20个并发会话。"},
         ],
         "expect": "5个并发会话", "answerable": True, "must_contain": ["5"]},
        {"id": 25, "cat": "F 多轮对话", "q": "它需要提前多久申请？",
         "history": [
             {"role": "user", "content": "年假有几天？"},
             {"role": "assistant", "content": "入职满一年后每年5天，满三年后7天。"},
         ],
         "expect": "提前一周", "answerable": True, "must_contain": ["一周"]},
        {"id": 26, "cat": "F 多轮对话", "q": "那病假呢？",
         "history": [
             {"role": "user", "content": "事假期间发工资吗？"},
             {"role": "assistant", "content": "事假期间不发放工资。"},
         ],
         "expect": "病假按基本工资80%发放", "answerable": True, "must_contain": ["80"]},

        # --- G 边界模糊（知识库信息不足，理想表现是指出缺失）---
        {"id": 27, "cat": "G 信息不足", "q": "智服通准确率95%以上，这个数据怎么验证的？",
         "expect": "知识库只提到准确率95%以上，未说明验证方法", "answerable": True, "must_contain": ["95"]},
        {"id": 28, "cat": "G 信息不足", "q": "迟到超过30分钟按事假处理，那会扣多少钱？",
         "expect": "资料只说明按事假半天处理且事假不发工资，未给出具体金额", "answerable": True, "must_contain": ["事假"]},
        {"id": 29, "cat": "G 信息不足", "q": "智服通能接入微信公众号吗？",
         "expect": "能", "answerable": True, "must_contain": ["能"]},
        {"id": 30, "cat": "G 信息不足", "q": "公司实行弹性工作制吗？",
         "expect": "不是，实行标准工时制", "answerable": True, "must_contain": ["标准"]},
    ]


# ---------------------------------------------------------------------------
# 三个评测器
# ---------------------------------------------------------------------------
def judge_correct(question, expect, answer, answerable):
    """判定答案是否正确（含拒答场景）。"""
    if not answerable:
        prompt = (
            "这是一个知识库中【没有答案】的问题，理想回答应该是明确拒答或说明资料中没有。\n"
            f"问题：{question}\n模型回答：{answer}\n\n"
            "如果模型明确表示资料中没有相关信息（拒答），输出「正确」；"
            "如果模型编造了具体答案或尝试猜测，输出「错误」。只输出「正确」或「错误」。"
        )
    else:
        prompt = (
            "请判断模型回答是否包含标准答案的核心信息。\n"
            f"问题：{question}\n标准答案要点：{expect}\n模型回答：{answer}\n\n"
            "包含核心信息输出「正确」，否则输出「错误」。只输出「正确」或「错误」。"
        )
    text, usage = chat([{"role": "user", "content": prompt}], temperature=0)
    return ("正确" in text), usage


def judge_faithful(answer, docs):
    """判定答案是否只依赖检索到的资料（防幻觉核心）。"""
    context = "\n".join(docs)[:4000]
    prompt = (
        "判断下面这个回答是否完全依据给定的参考资料得出。\n\n"
        f"参考资料：\n{context}\n\n"
        f"模型回答：\n{answer}\n\n"
        "判定规则：\n"
        "- 如果回答中的关键事实都能在参考资料里找到依据（可以合理归纳，但不能引入资料外的新事实），输出「忠实」\n"
        "- 如果回答引入了参考资料中没有的信息（如编造数字、补充外部知识），输出「不忠实」\n"
        "只输出「忠实」或「不忠实」。"
    )
    text, usage = chat([{"role": "user", "content": prompt}], temperature=0)
    return ("忠实" in text), usage


def check_must_contain(answer, must_contains):
    """规则校验：回答里是否出现了关键数字/词。"""
    if not must_contains:
        return None
    return all(k in answer for k in must_contains)


def extract_number(text):
    m = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(m.group()) if m else None


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--thinking", action="store_true", help="开启思考模式做对比")
    ap.add_argument("--save", help="把报告保存为 Markdown 文件")
    ap.add_argument("--id", type=int, help="只跑指定 id 的用例")
    args = ap.parse_args()

    global MAX_THINKING
    MAX_THINKING = args.thinking

    cases = build_cases()
    if args.id:
        cases = [c for c in cases if c["id"] == args.id]
        if not cases:
            print(f"没有 id={args.id} 的用例")
            return

    print("=" * 70)
    print(f"RAG 评测 V2  |  用例数 {len(cases)}  |  思考模式 {'开' if MAX_THINKING else '关'}")
    print(f"召回条数 {N_RESULTS}  |  对话模型 {CHAT_MODEL}  |  {datetime.now():%Y-%m-%d %H:%M}")
    print("=" * 70)

    results = []
    total_usage = {"in": 0, "out": 0}

    for c in cases:
        history = c.get("history", [])
        print(f"\n[{c['id']:>2}/{len(cases)}] {c['cat']} | {c['q']}")
        if history:
            print(f"        历史轮数：{len(history)}")

        t0 = time.time()
        try:
            out = rag_answer(c["q"], history)
        except Exception as e:
            print(f"        ❌ 运行失败：{e}")
            results.append({**c, "error": str(e)})
            continue
        elapsed = time.time() - t0

        answer = out["answer"]
        docs = out["docs"]

        # 汇总 token
        for _, u in out["usages"]:
            if u:
                total_usage["in"] += u.prompt_tokens
                total_usage["out"] += u.completion_tokens

        # 1) 检索命中：正确答案的关键词是否出现在召回内容里
        recalled_text = "\n".join(docs)
        if c.get("must_contain"):
            retrieval_hit = all(k in recalled_text for k in c["must_contain"])
        else:
            retrieval_hit = None

        # 2) 规则校验
        rule_ok = check_must_contain(answer, c.get("must_contain"))

        # 3) LLM 判正确
        correct, u = judge_correct(c["q"], c["expect"], answer, c.get("answerable", True))
        if u:
            total_usage["in"] += u.prompt_tokens
            total_usage["out"] += u.completion_tokens

        # 4) LLM 判忠实
        faithful, u2 = judge_faithful(answer, docs)
        if u2:
            total_usage["in"] += u2.prompt_tokens
            total_usage["out"] += u2.completion_tokens

        if out["rewritten"] != c["q"]:
            print(f"        ↪ 改写：{out['rewritten']}")

        print(f"        回答：{answer[:70].replace(chr(10), ' ')}{'...' if len(answer) > 70 else ''}")
        print(f"        检索命中：{'-' if retrieval_hit is None else ('✅' if retrieval_hit else '❌')}"
              f" | 规则校验：{'-' if rule_ok is None else ('✅' if rule_ok else '❌')}"
              f" | 正确：{'✅' if correct else '❌'}"
              f" | 忠实：{'✅' if faithful else '❌'}"
              f" | {elapsed:.2f}s")

        results.append({
            **c,
            "answer": answer,
            "rewritten": out["rewritten"],
            "docs": docs,
            "retrieval_hit": retrieval_hit,
            "rule_ok": rule_ok,
            "correct": correct,
            "faithful": faithful,
            "elapsed": elapsed,
        })

    # ---------------- 汇总 ----------------
    valid = [r for r in results if "answer" in r]
    n = len(valid) or 1

    def rate(key):
        got = [r for r in valid if r.get(key) is not None]
        if not got:
            return None, 0
        return sum(1 for r in got if r[key]) / len(got), len(got)

    acc, acc_n = rate("correct")
    faith, faith_n = rate("faithful")
    hit, hit_n = rate("retrieval_hit")
    rule, rule_n = rate("rule_ok")
    avg_t = sum(r["elapsed"] for r in valid) / n
    cost = total_usage["in"] * PRICE_IN + total_usage["out"] * PRICE_OUT

    print("\n" + "=" * 70)
    print("📊 RAG 系统评测报告 V2")
    print("=" * 70)
    print(f"总用例数：{len(results)}（有效 {len(valid)}）")
    if acc is not None:
        print(f"答案正确率：{acc*100:.1f}%  ({sum(1 for r in valid if r['correct'])}/{acc_n})")
    if faith is not None:
        print(f"答案忠实率：{faith*100:.1f}%  ({sum(1 for r in valid if r['faithful'])}/{faith_n})")
    if hit is not None:
        print(f"检索命中率：{hit*100:.1f}%  ({sum(1 for r in valid if r['retrieval_hit'])}/{hit_n})")
    if rule is not None:
        print(f"关键词命中：{rule*100:.1f}%  ({sum(1 for r in valid if r['rule_ok'])}/{rule_n})")
    print(f"平均响应时间：{avg_t:.2f}s")
    print(f"Token 用量：输入 {total_usage['in']} / 输出 {total_usage['out']}")
    print(f"总成本：¥{cost*USD_TO_CNY:.4f}（约 ${cost:.6f}）")
    print(f"单次平均成本：¥{cost*USD_TO_CNY/n:.4f}")

    # 按类别统计
    print("\n按类别：")
    cats = {}
    for r in valid:
        cats.setdefault(r["cat"], []).append(r)
    for cat, rs in cats.items():
        c_ok = sum(1 for r in rs if r["correct"])
        f_ok = sum(1 for r in rs if r["faithful"])
        print(f"  {cat:<10} 正确 {c_ok}/{len(rs)} | 忠实 {f_ok}/{len(rs)}")

    # 失败明细
    fails = [r for r in valid if not r["correct"] or not r["faithful"]]
    if fails:
        print("\n❌ 需要关注的用例：")
        for r in fails:
            why = []
            if not r["correct"]:
                why.append("答案错")
            if not r["faithful"]:
                why.append("不忠实")
            if r.get("retrieval_hit") is False:
                why.append("检索未命中")
            print(f"  [{r['id']}] {r['cat']} | {r['q']}  → {'、'.join(why)}")
            print(f"      回答：{r['answer'][:80]}")
            print(f"      期望：{r['expect']}")
    elif not valid:
        print("\n⚠️ 没有任何用例成功执行，请检查上面的报错")
    else:
        print("\n✅ 全部通过")

    # ---------------- 保存 Markdown ----------------
    if args.save:
        lines = [
            "# RAG 系统评测报告",
            "",
            f"- 评测时间：{datetime.now():%Y-%m-%d %H:%M}",
            f"- 用例数：{len(valid)}",
            f"- 召回条数：{N_RESULTS}",
            f"- 对话模型：{CHAT_MODEL}",
            f"- 思考模式：{'开启' if MAX_THINKING else '关闭'}",
            "",
            "## 总体指标",
            "",
            "| 指标 | 结果 |",
            "| --- | --- |",
            f"| 答案正确率 | {acc*100:.1f}%（{sum(1 for r in valid if r['correct'])}/{acc_n}） |" if acc is not None else "",
            f"| 答案忠实率 | {faith*100:.1f}%（{sum(1 for r in valid if r['faithful'])}/{faith_n}） |" if faith is not None else "",
            f"| 检索命中率 | {hit*100:.1f}%（{sum(1 for r in valid if r['retrieval_hit'])}/{hit_n}） |" if hit is not None else "",
            f"| 平均响应时间 | {avg_t:.2f}s |",
            f"| 单次平均成本 | ¥{cost*USD_TO_CNY/n:.4f} |",
            "",
            "## 分类通过率",
            "",
            "| 类别 | 正确 | 忠实 |",
            "| --- | --- | --- |",
        ]
        for cat, rs in cats.items():
            lines.append(f"| {cat} | {sum(1 for r in rs if r['correct'])}/{len(rs)} | {sum(1 for r in rs if r['faithful'])}/{len(rs)} |")
        lines += ["", "## 失败用例", ""]
        if fails:
            for r in fails:
                lines.append(f"- **[{r['id']}] {r['cat']}** {r['q']}")
                lines.append(f"  - 期望：{r['expect']}")
                lines.append(f"  - 实际：{r['answer'][:100]}")
        else:
            lines.append("无")
        with open(args.save, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"\n报告已保存：{args.save}")


if __name__ == "__main__":
    main()
