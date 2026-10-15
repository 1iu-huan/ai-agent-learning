import os
import time
import json
from openai import OpenAI
from dotenv import load_dotenv
from project3_rag_app import rag_query, get_embedding  # 复用你已有的函数

load_dotenv()

deepseek_client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

# 1. 准备 20 条测试用例（问题 + 标准答案要点）
test_cases = [
    {"question": "员工迟到超过30分钟怎么处理？", "expected": "按事假半天处理"},
    {"question": "每月迟到超过几次会扣全勤奖？", "expected": "3次"},
    {"question": "事假期间发工资吗？", "expected": "不发放工资"},
    {"question": "病假工资按多少发放？", "expected": "基本工资的80%"},
    {"question": "入职满一年有几天年假？", "expected": "5天"},
    {"question": "工作满三年后年假几天？", "expected": "7天"},
    {"question": "公司为员工缴纳哪些保险？", "expected": "养老保险、医疗保险、失业保险、工伤保险、生育保险和住房公积金"},
    {"question": "智服通基础版多少钱？", "expected": "299元/月"},
    {"question": "智服通专业版支持多少并发会话？", "expected": "20个"},
    {"question": "智服通支持私有化部署吗？", "expected": "企业版支持"},
    {"question": "如何注册智服通账号？", "expected": "访问官网填写信息获得14天免费试用"},
    {"question": "知识库支持哪些文件格式？", "expected": "PDF、Word、txt、Markdown"},
    {"question": "智能客服回答不准怎么办？", "expected": "在后台补充文档或调整问答对"},
    {"question": "技术支持热线电话是多少？", "expected": "400-800-1234"},
    {"question": "员工迟到超过30分钟算旷工吗？", "expected": "按事假半天处理，不算旷工"},
    {"question": "年假需要提前多久申请？", "expected": "提前一周"},
    {"question": "病假需要提供什么证明？", "expected": "医院出具的病假证明"},
    {"question": "智服通能接入微信公众号吗？", "expected": "能"},
    {"question": "迟到早退累计超过3次会怎么样？", "expected": "扣除当月全勤奖"},
    {"question": "事假需要提前多久申请？", "expected": "提前一天"}
]


# 2. 用 LLM 当裁判，判断回答是否正确
def judge_answer(question, expected, actual):
    prompt = f"""请判断下面这个回答是否与标准答案一致。
问题：{question}
标准答案要点：{expected}
模型回答：{actual}

如果模型回答包含了标准答案的核心意思，输出"正确"；否则输出"错误"。
只输出"正确"或"错误"，不要解释。
"""
    response = deepseek_client.chat.completions.create(
        model="deepseek-flash",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return response.choices[0].message.content.strip()#只输出"正确"或"错误"，不要解释。


# 3. 跑测试，统计指标
correct = 0
total_time = 0
total_tokens = 0

for i, case in enumerate(test_cases):
    print(f"测试 {i + 1}/{len(test_cases)}：{case['question']}")
    start = time.time()#开始时间
    answer, docs = rag_query(case["question"], [])  # 不传历史，单轮测试
    elapsed = time.time() - start#耗时时间

    verdict = judge_answer(case["question"], case["expected"], answer)
    if verdict == "正确":
        correct += 1

    total_time += elapsed
    # 粗略估算 tokens（实际应从 response.usage 获取，这里简化）
    total_tokens += len(case["question"]) + len(answer)

    print(f"  判定：{verdict} | 耗时：{elapsed:.2f}s")

# 4. 输出成绩单
print("\n" + "=" * 40)
print("📊 RAG 系统评测报告")
print("=" * 40)
print(f"总测试数：{len(test_cases)}")
print(f"正确数：{correct}")
print(f"准确率：{correct / len(test_cases) * 100:.1f}%")
print(f"平均响应时间：{total_time / len(test_cases):.2f}s")
print(f"预估总 Token 消耗：约 {total_tokens} tokens")
print(f"预估总成本：约 ¥{total_tokens / 1000000 * 2:.4f}")