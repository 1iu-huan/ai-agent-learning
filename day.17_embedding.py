import math
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(
    api_key=os.getenv("ZHIPU_API_KEY"),
    base_url="https://open.bigmodel.cn/api/paas/v4/",
)


def cosine_similarity(vec1, vec2):
    """手写余弦相似度，理解底层原理"""
    #点积；把两个向量对应位置的数字相乘，然后全部加起来。zip(...):把两个列表“拉链”一样对齐
    #um(...)：把所有乘积加起来
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    #计算模长;math.sqrt(...)：开平方根。
    norm1 = math.sqrt(sum(a ** 2 for a in vec1))
    norm2 = math.sqrt(sum(b ** 2 for b in vec2))

    if norm1 == 0 or norm2 == 0:
        return 0
    return dot_product / (norm1 * norm2)#!!!


def get_embedding(text):
    """调用Embeeding API，把文字变成向量"""
    response = client.embeddings.create(
        model = "embedding-2",
        input = text
    )
    return response.data[0].embedding

# 测试两句话
text1 = "今天天气真不错，适合出去玩。"
text2 = "阳光明媚，是个郊游的好日子。"
text3 = "这道数学题好难，我完全不会做。"

#把文字变向量
vec1 = get_embedding(text1)
vec2 = get_embedding(text2)
vec3 = get_embedding(text3)

print(f"向量维度：{len(vec1)}")  # 智谱 embedding-2 通常是 1024 维

# 用你刚才手写的函数算相似度
print("天气 vs 郊游：", cosine_similarity(vec1, vec2))  # 应该比较高，比如 0.8
print("天气 vs 数学：", cosine_similarity(vec1, vec3))  # 应该比较低，比如 0.3