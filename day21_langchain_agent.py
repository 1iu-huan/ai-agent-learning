import os
from simpleeval import simple_eval
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.tools import tool  # 1. 从 langchain.tools 导入 tool
from langchain.agents import create_agent  # 2. 导入 create_agent

load_dotenv()

# 初始化模型
llm = ChatOpenAI(
    model="deepseek-flash",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
    temperature=0
)

# 定义工具（保持不变）
@tool
def calculator(expression: str) -> str:
    """执行数学计算。输入应该是一个合法的 Python 数学表达式，例如 '25 * 4'。"""
    try:
        return str(simple_eval(expression))
    except Exception as e:
        return f"计算错误: {e}"

@tool
def get_weather(city: str) -> str:
    """查询指定城市的天气。输入应该是城市名称，如 '北京'。"""
    mock_data = {"北京": "晴，25°C", "上海": "多云，28°C"}
    return mock_data.get(city, "暂无该城市天气数据")

tools = [calculator, get_weather]

# 3. 使用 create_agent 直接创建 Agent
agent = create_agent(
    model = llm,
    tools = tools,
    system_prompt = "你是一个得力的助手。"
)

# 4. 调用方式也变了：传入一个包含 messages 列表的字典
print("\n--- 测试 1：单工具调用 ---")
response1 = agent.invoke({"messages": [{"role": "user", "content": "帮我算一下 25 乘以 4 等于多少？"}]})
# 最终回答在 messages 列表的最后一条
print("最终回复:", response1["messages"][-1].content)

print("\n--- 测试 2：多工具混合调用 ---")
response2 = agent.invoke({"messages": [{"role": "user", "content": "帮我算一下 100 除以 4，再查一下北京的天气。"}]})
print("最终回复:", response2["messages"][-1].content)