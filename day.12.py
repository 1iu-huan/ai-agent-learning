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
         "parameters" : {
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

messages = [{"role" : "user", "content" : "现在几点"}]

response = client.chat.completions.create(
   model = 'deepseek-flash',
   messages = messages,
   tools = tools,
   tool_choice = 'auto'
)

tool_calls = response.choices[0].message.tool_calls

if tool_calls:
   for tool_call in tool_calls:
      function_name = tool_call.function.name
      arguments = json.loads(tool_call.function.arguments)#把字符串变成真正的Python字典
      #json.loads()
      # ✅ 多工具路由：根据名字调用不同函数
      if function_name == "calculator":
         result = calculator(arguments["a"], arguments["b"], arguments["operation"])
      elif function_name == "get_current_time":
         result = get_current_time()
      elif function_name == "get_weather":
         result = get_weather(arguments["city"])
      else:
         result = "未知工具"

      print(f"调用的工具：{function_name}")
      print(f"执行结果：{result}")

      messages.append(response.choices[0].message)
      messages.append({
         "role": "tool",
         "tool_call_id": tool_call.id,
         "content": str(result)
      })

      final_response = client.chat.completions.create(
         model = 'deepseek-flash',
         messages = messages,
         tools = tools,
      )

      print(f'AI最终回复：{final_response.choices[0].message.content}')
else:
   print("模型没有调用工具，直接回复：", response.choices[0].message.content)