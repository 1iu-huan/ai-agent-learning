import os
from openai import OpenAI
from dotenv import load_dotenv
#引入工具包


#加载.env文件里的环境变量
load_dotenv()
#初始化客户端
client=OpenAI(
    api_key=os.getenv('DEEPSEEK_API_KEY'),
    base_url="https://api.deepseek.com"
)
## ⚠️ 注意：messages 列表必须写在循环外面！
# 如果写在里面，每次对话都会被清空，AI 就失忆了
messaegs = [
    {"role": 'system','content': '你是一个聪明的AI助手'}
]

print('===开始===')

while True:
    user_input=input('\n你：')
    #获取用户输入，检查是否需要退出
    if user_input.lower() in ['exit','quit']:
        print('bye')
        break
    #把用户的话加入历史
    messaegs.append({'role': 'user', 'content': user_input})
    #  发送给大模型（加上 try-except 防止网络报错）
    try:
        response = client.chat.completions.create(
        model = 'deepseek-flash',
        temperature=0.7,
        messages = messaegs,
)
        #提取AI的回复
        ai_reply = response.choices[0].message.content

        print(f'AI:{ai_reply}')
        #打印本次调用的Token消耗和花费
        usage = response.usage
        print('token')
        print(f'输入:{usage.prompt_tokens} | 输出:{usage.completion_tokens} | 总计:{usage.total_tokens}')
        cost = (usage.prompt_tokens / 1000000 * 1.0) + (usage.completion_tokens / 1000000 * 2.0)
        print(f'本次花费：:{cost:.6f}')
        #打印出来，并把AI的话也加入历史
        messaegs.append({'role': 'assistant','content': ai_reply})
    except Exception as e:
        print(f'发生错误:{e}')
