#引入工具包
import os
from openai import OpenAI
from dotenv import load_dotenv


# 1. 加载 .env 文件里的环境变量
load_dotenv()

# 2. 初始化客户端（注意 DeepSeek 的 base_url）
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

# 3. 发送第一条消息
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "你是一个友好的AI助手"},
        {"role": "user", "content": "你好，请用一句话介绍你自己"}
    ]
)

# 4. 打印结果
print("AI 回复：", response.choices[0].message.content)




