import math

def cosine_similarity(vec1, vec2):
    """手写余弦相似度，理解底层原理"""

    dot_product = sum(a * b for a, b in zip(vec1, vec2))

    norm1 = math.sqrt(sum(a ** 2 for a in vec1))
    norm2 = math.sqrt(sum(b ** 2 for b in vec2))

    if norm1 == 0 or norm2 == 0:
        return 0
    return dot_product / (norm1 * norm2)

# 测试
v1 = [1, 2, 3]
v2 = [1, 2, 3]
v3 = [-1, -2, -3]
v4 = [1, 0, 0]

print("完全相同：", cosine_similarity(v1, v2))  # 输出 1.0
print("完全相反：", cosine_similarity(v1, v3))  # 输出 -1.0
print("毫不相关：", cosine_similarity(v1, v4))  # 输出 0.267...