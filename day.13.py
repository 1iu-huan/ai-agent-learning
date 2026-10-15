import datetime
import os
from openai import OpenAI
from dotenv import load_dotenv
import json


load_dotenv()

client = OpenAI(
   api_key=os.getenv("DEEPSEEK_API_KEY"),
   base_url="https://api.deepseek.com"
)

def calculator(a, b, operation):
   if operation == "add":
      return a + b
   elif operation == "subtract":
      return a - b
   elif operation == "multiply":
      return a * b
   elif operation == "divide":
      return a / b if b != 0 else '除数不能为0'
   else:
      return '未知运算'

def get_current_time():
   return datetime.datetime.now().strftime('%Y-%m-%d-%H:%M:%S')

def get_weather(city):
    #模拟数据
   mock_data={
      "北京":"晴，25°C",
      "上海":"多云，28°C",
      "广州":"雷阵雨，30°C"
   }
   return mock_data.get(city,"暂无该城市天气数据")

tools = [
   {
      "type":"function",
      "function":{
         "name" : "calculator",
         "description" : "执行数学四则运算",
         "parameters" : {#parameters 是“整张表格”，properties 是“表格里具体的填空项”。
            "type" : "object",
            "properties" : {
                     "a": {"type": "number", "description": "第一个数字"},
                     "b": {"type": "number", "description": "第二个数字"},
                     "operation": {"type": "string", "enum": ["add", "subtract", "multiply", "divide"], "description": "运算类型"}
            },
            "required": ["a","b","operation"]
         }
      }
   },
   {
      "type":"function",
      "function":{
         "name" : "get_current_time",
         "description" : "获取当前日期和时间",
         "parameters" : {
            "type" : "object",
            "properties" : {},#不需要传参数
            "required" : []
         }
      }
   },
   {
      "type":"function",
      "function":{
         "name" : "get_weather",
         "description" : "查询指定城市的天气",
         "parameters" : {
            "type" : "object",
            "properties" : {
               "city": {"type": "string", "description": "城市名称，如北京、上海"}
         },
            "required" : ["city"]
         }
      }
   }
]

messages = [{"role" : "user", "content" : "帮我算一下25乘以4等于多少，然后再查一下北京的天气。"}]

max_iterations = 5

for i in range(max_iterations):
    print(f'\n---第{i+1}轮思考---')

    response = client.chat.completions.create(
        model = 'deepseek-flash',
        messages = messages,
        tools = tools,#告诉模型有什么菜单
        tool_choice = 'auto'
)

    #response.choices[0].message:是整个包裹（包含role、content、tool_calls)
    #response.choices[0].message.content:只提取了包裹里的纸条（纯文本内容）
    messages.append(response.choices[0].message)
    tool_calls = response.choices[0].message.tool_calls

    #没有工具调用，模型给出最终答案
    if not tool_calls:
        print(f'\n AI最终回复：{response.choices[0].message.content}')
        break

    for tool_call in tool_calls:#遍历所有的工具
        function_name = tool_call.function.name#提取名字
        arguments = json.loads(tool_call.function.arguments)#提取参数，把json字符串变成python字典

        print(f"调用的工具：{function_name}")
        print(f"传入参数：{arguments}")

        # 路由到本地函数
        if function_name == "calculator":
            result = calculator(arguments["a"], arguments["b"], arguments["operation"])
        elif function_name == "get_current_time":
            result = get_current_time()
        elif function_name == "get_weather":
            result = get_weather(arguments["city"])
        else:
            result = "未知工具"

        print(f"本地执行结果：{result}")

        messages.append({"role" : "tool", "tool_call_id" : tool_call.id, "content" : str(result)})
        #因为模型可能在一次回复中并行调用多个工具。tool_call_id 是每个调用请求的唯一标识，它相当于订单号。只有带上它，模型才能把返回的多个结果和之前的多个调用请求一一对应起来，避免上下文混淆。如果不带，API 会直接报错。
else:
    print("达不到最大循环次数，Agent强制停止.")