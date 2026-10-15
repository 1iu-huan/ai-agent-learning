import os
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

client=OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

messages = [
    {'role': 'system','content': '你是一个AI助手'}
]

print("=== AI 命令行助手已启动 (输入 exit 退出) ===")

while True:
    #用户输入
    user_input = input('\n你: ')

    #检查(“设定退出暗号”。它负责在用户输入特定词时，让程序安全退出)
    #.lower()作用把大写字母全部变为小写字母
    if user_input.lower() in ['exit','quit']:
        print('再见')
        break

    #把用户的话加入历史
    messages.append({'role': 'user','content': user_input})

    #发送给大模型（加上try-except防止网络报错）
    try:
        response = client.chat.completions.create(
        model='deepseek-flash',
        messages=messages,
        temperature=1.0,#控制随机性。0-0.3 稳定确定（适合提取、分类）；0.7-1 发散有创意（适合写文章）。
    )

        #提取AI的回复
        ai_reply = response.choices[0].message.content

        #6.打印出来
        print(f'AI: {ai_reply}')

        #打印本次调用的 Token 消耗和花费
        usage = response.usage
        print(f'---Token消耗---')
        print(f'输入:{usage.prompt_tokens} | 输出:{usage.completion_tokens} | 总计:{usage.total_tokens}')

        #DeepSeek 当前价格约为：输入 1元/百万Token，输出 2元/百万Token (按官方最新为准)
        cost = (usage.prompt_tokens / 1000000 * 1.0) + (usage.completion_tokens / 1000000 * 2.0)
        print(f'本次花费:{cost:.6f}')

        #把AI的话也加入历史
        messages.append({'role': 'assistant','content': ai_reply})
    except Exception as e:
        print(f'发生错误:{e}')