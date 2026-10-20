import os
from simpleeval import simple_eval
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.tools import tool  # 1. 从 langchain.tools 导入 tool
from langchain.agents import create_agent  # 2. 导入 create_agent
from langgraph.checkpoint.memory import MemorySaver

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
    system_prompt = "你是一个得力的助手。",
    checkpointer = MemorySaver()
)

config = {"configurable" : {"thread_id" : "cli-session"}}

print("开始对话（输入exit退出）\n")

while True:
    user_input = input("你：").strip()

    if not user_input:
        continue
    if user_input.lower() in ["exit", "quit", "退出"]:
        print("再见!")
        break

    # 每次只传这一条消息，历史框架自动捞
    result = agent.invoke(
 {"messages": [{"role" : "user", "content" : user_input}]},
         config,
    )

    # 取最后一条的文本
    print("AI:", result["messages"][-1].content, "\n")
    # 打印完整状态
    for msg in result["messages"]:
        role = msg.type
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            print(f"[{role}] 调用工具:", msg.tool_calls)
        else:
            print(f"[{role}]", msg.content)


