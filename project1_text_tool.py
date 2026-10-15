import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

def process_text(text,mode):
    """根据模式，调用AI处理文本"""
    if mode == "1":
        prompt = f'请为以下文本写一个简短摘要，控制在100字以内：\n\n{text}'
    elif mode == "2":
        prompt = f'请将以下文本翻译成英文，保持愿意，语言流程：\n\n{text}'
    elif mode == "3":
        prompt = f'请提取以下文本中的3-5个核心关键词，用逗号分隔，不要解释：\n\n{text}'
    else:
        return '无效的选择，请重新输入'

    try:
        response = client.chat.completions.create(
            model = 'deepseek-flash',
            messages=[
                {'role': 'system', 'content': '你是一个专业的文本处理助手，回答尽量简洁、准确。'},
                {'role': 'user', 'content': prompt},
            ],
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        return f'API调用失败：{e}'


def main():
    print("===AI文本处理小工具===")
    print("功能：1.摘要  2.翻译  3.提取关键词" )

    while True:
        user_text = input('\n请输入一段文本（输入exit退出）：')
        if user_text.lower() in ['exit','quit']:
            print('再见')
            break

        print('请选择操作：1.摘要  2.翻译  3.提取关键词')
        choice = input('你的选择（1/2/3）：')

        print('\n处理中...')
        result = process_text(user_text,choice)#result = 这个函数return的值
        print(f'结果：\n{result}')

if __name__ == '__main__':
    main()

