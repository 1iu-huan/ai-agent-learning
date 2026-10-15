import os
import json
from openai import OpenAI
from dotenv import load_dotenv



load_dotenv()
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

#函数
def calculator(a,b,operation):
    if operation == "add" :
        return a + b
    elif operation == "subtract" :
        return a - b
    elif operation == "multiply" :
        return a * b
    elif operation == "divide" :
        return a / b if b != 0 else '除数不能为0'
    else:
        return '未知运算'
#定义工具描述。json模式
tools = [
    {
        "type" : "function",
        "function" : {
            "name" : "calculator",
            "description" : "执行数学四则运算",
            "parameters": {
                "type": "object",#参数是一个对象（字典）
                "properties": {
                    "a": {"type": "number", "description": "第一个数字"},
                    "b": {"type": "number", "description": "第二个数字"},
                    "operation": {"type": "string", "enum": ["add", "subtract", "multiply", "divide"], "description": "运算类型"}
                },
                "required": ["a", "b", "operation"] # 告诉我：这三个参数必须全给
            }
        }
    }
]
#向模型提问
messages = [{'role' : 'user','content': "请帮我算一下25乘以4等于多少？"}]

response = client.chat.completions.create(
    model = 'deepseek-flash',
    messages = messages,
    tools = tools,
    tool_choice='auto'#让模型自己决定是否调用工具
)

# 4. 检查模型是否决定调用工具
tool_calls = response.choices[0].message.tool_calls

if tool_calls:
    print("模型决定调用工具！")
    for tool_call in tool_calls:
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        print(f"调用的函数：{function_name}")
        print(f"传入参数：{arguments}")

        # 5. 真正在本地执行函数
        result = calculator(arguments["a"], arguments["b"], arguments["operation"])
        print(f"本地计算结果：{result}")

        # 6. 把结果发回给模型，让它生成最终回复
        messages.append(response.choices[0].message)
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": str(result)
        })

        final_response = client.chat.completions.create(
            model="deepseek-flash",
            messages=messages,
            tools=tools
        )
        print(f"AI 最终回复：{final_response.choices[0].message.content}")
else:
        print("模型没有调用工具，直接回复：", response.choices[0].message.content)