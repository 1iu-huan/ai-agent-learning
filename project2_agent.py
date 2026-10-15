import datetime
import time
import os
from openai import OpenAI
from dotenv import load_dotenv
import json



load_dotenv()
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)
#API调用错误和重试，重试防护
def call_llm_with_retry(messages,tools,max_retries=3):
    for attempt in range(max_retries):
        try:#尝试调用API
            return client.chat.completions.create(
                model = 'deepseek-flash',
                messages = messages,
                tools = tools,
                tool_choice= 'auto'
            )
        except Exception as e:
            print(f'API调用失败（第{attempt+1}次):{e}')
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                raise

def calculator(a, b, operation):
    if operation == 'add':
        return a + b
    elif operation == 'subtract':
        return a - b
    elif operation == 'multiply':
        return a * b
    elif operation == 'divide':
        return a / b if b != 0 else '除数不能为0'
    else:
        return '未知运算'


def get_current_time():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def get_weather(city):

    mock_data = {
        "北京":"晴，25°C",
        "上海":"多云，28°C",
        "广州":"雷阵雨，30°C"
    }
    return mock_data.get(city,"暂无该城市天气数据")
#工具tools = tools
tools = [
    {#第一个工具
        "type" : "function",
        "function" :{
            "name" : "calculator",
            "description" : "执行四则运算",
            "parameters": {
                "type" : "object",
                "properties" : {
                    "a" : {"type" : "number", "description" : "第一个数字"},
                    "b" : {"type" : "number", "description" : "第二个数字"},
                    "operation" : {"type" : "string", "enum" : ["add", "subtract", "multiply", "divide"]},
                    },
                "required" : ["a","b","operation"]
            }
        }
    },
    {#第二个工具
        "type" : "function",
        "function" :{
            "name" : "get_current_time",
            "description" : "获取当前日期和时间",
            "parameters": {
                "type" : "object",
                "properties" : {},
                "required" : []
            }
        }
    },
    {#第三个工具
        "type" : "function",
        "function" :{
            "name" : "get_weather",
            "description" : "查询指定城市的天气",
            "parameters": {
                "type" : "object",
                "properties" : {
                    "city" : {"type" : "string", "description" : "城市名称，如北京，上海"},
                },
                "required" : ["city"]
            }
        }
    }
]

messages = [{"role" : "system", "content" : "你是一个多功能助手，可以算数、查天气、查时间。回答要简洁。"}]

print("===多功能助手Agent已启动（输入exit退出）===")

while True:
    user_input = input("\n你：")
    if user_input.lower() in ["exit","quit"]:
        print("再见！")
        break
    #添加客户问题到上下文
    messages.append({"role" : "user", "content" : user_input})

    max_iterations = 5
    for i in range(max_iterations):
        print(f'\n---第{i+1}次思考---')

        try:
            response = call_llm_with_retry(messages,tools)
        except Exception as e:
            print(f'调用API彻底失败：{e}')
            break

        messages.append(response.choices[0].message)
        tool_calls = response.choices[0].message.tool_calls

        if not tool_calls:
            print(f"\nAI:{response.choices[0].message.content}")
            break

        for tool_call in tool_calls:
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)

            print(f'调用的工具：{function_name}')
            print(f'传入参数：{arguments}')

            try:
                if function_name == "calculator":
                    result = calculator(arguments["a"],arguments["b"],arguments["operation"])
                elif function_name == "get_current_time":
                    result = get_current_time()
                elif function_name == "get_weather":
                    result = get_weather(arguments["city"])
                else:
                    result = "未知工具"
            except Exception as e:
                result = f'工具执行失败：{e}'

            print(f'本地执行结果：{result}')

            messages.append({"role" : "tool","tool_call_id": tool_call.id, "content" : str(result)})
    else:
        print(f'达到最大循环次数，强制让模型总结...')
        try:
            final_response = client.chat.completions.create(
                model = 'deepseek-flash',
                messages = messages,
            )
            print(final_response.choices[0].message.content)
        except Exception as e:
            print(f'强制总结失败:{e}')
