import os
import json
from dotenv import load_dotenv
from openai import OpenAI
load_dotenv()

client = OpenAI(
    api_key=os.getenv('DEEPSEEK_API_KEY'),
    base_url='https://api.deepseek.com'
)

#待提取的文本
text = "大家好，我叫李明，目前住在杭州。我熟练掌握 Python 和 SQL，对 AI Agent 开发非常感兴趣。"
#构造提示词，明确要求返回JSON；键必须是双引号；字符串必须用双引号
prompt = f"""请从下面的文本中提取信息，并严格按照以下JSON格式输出:
{{
    "name":"姓名",
    "city":"城市",
    "skills":["技能1", "技能2"]
}}

文本: {text}
"""
response = client.chat.completions.create(
    model = "deepseek-flash",
    messages = [{'role': 'user', 'content': prompt}],
    temperature=0.1,
    response_format={'type':"json_object"} #关键：开启JSON模式！！！！
)

#获取AI返回的字符串
raw_output = response.choices[0].message.content
print("AI 原始输出:", raw_output)
#核心步骤：把JSON字符串解析成Python字典(用json.loads()把JSON字符串转换成Python字典，才能
try:
    data = json.loads(raw_output)
    #Python字典
    print('\n解析成功！')
    print('姓名:', data['name'])
    print('城市:', data['city'])
    print('技能:', data['skills'])
except json.JSONDecodeError:
    print('\n解析失败！AI没有返回合法的JSON。')


