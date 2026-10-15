if __name__ == '__main__':
    #列表基础
    tools = ["ChatGPT", "Claude", "DeepSeek", "通义千问", "智谱清言"]

    print("第一个工具：", tools[0])
    print("最后一个工具：", tools[-1])
    print("一共有：", len(tools), "个")

    tools.append("文心一言")
    print("加完之后：", tools)

    #for循环
    ai_tools = ["ChatGPT", "Claude", "DeepSeek", "通义千问", "智谱清言"]

    print("我关注的 AI 工具：")
    for i, tool in enumerate(ai_tools):
        print(f"{i + 1}. {tool}")

    #字典基础
    user = {"name": "你的名字", "age": 20, "major": "你的专业"}

    # 用 for 循环打印字典里的每一项
    for key, value in user.items():#items()：同时取出字典里的”键“和”值“
        print(f"{key} = {value}")

    #列表加字典
    messages = [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好，有什么可以帮你？"},
        {"role": "user", "content": "帮我查一下天气"},
    ]
    for msg in messages:
        print(f"[{msg['role']}] {msg['content']}")
