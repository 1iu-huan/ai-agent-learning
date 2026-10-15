import os
from urllib import response

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv('DEEPSEEK_API_KEY'),
    base_url="https://api.deepseek.com"
)

review = "等了5天才收到货，包装还破了，客服也不理人。"

prompt1 = f"请把下面这条评论分类为‘物流问题'、'产品质量'或'售后服务': {review}"

prompt2 = f"你是一个专业的电商客服质检员。请把下面这条评论分为'物流问题'、'产品质量'或'售后服务': {review}"

prompt3 = f"你是一个专业的电商客服质检员。"

for i, prompt in enumerate([prompt1, prompt2, prompt3], start=1):
    response = client.chat.completions.create(
        model = "deepseek-flash",
        messages = [{'role': 'user', 'content': prompt}],
        temperature=0.1
    )
    print(f'\n====写法{i}====')
    print(response.choices[0].message.content)