import os
import chromadb
import uuid
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

# ---------- 初始化两个客户端 ----------
client = OpenAI(
    api_key=os.getenv("ZHIPU_API_KEY"),
    base_url="https://open.bigmodel.cn/api/paas/v4/"
)
deepseek_client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

def get_embedding(text):
    response = client.embeddings.create(
        model="embedding-2",
        input=text
    )
    return response.data[0].embedding

# ---------- 连接 Chroma ----------
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name="my_docs")
memory_collection = chroma_client.get_or_create_collection(name="user_memory")

#写入记忆函数
def save_memory(user_input):
    """从用户输入里提取值得长期记住的信息，存入向量库"""
    prompt = f"""请从下面这句话里提取值得长期记住的用户信息（比如专业、偏好、身份、常用工具等）。
    如果没有值得记住的信息，只输出"无"。
    只输出提取后的信息，不要解释。

    用户说：{user_input}
    """
    response = deepseek_client.chat.completions.create(
        model="deepseek-flash",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    memory = response.choices[0].message.content.strip()

    if memory and memory != "无":
        memory_id = f"mem_{uuid.uuid4().hex[:8]}"
        memory_collection.add(
            documents = [memory],
            embeddings = [get_embedding(memory)],
            ids = [memory_id],
        )
        print(f"💾 已记住：{memory}")

#召回函数
def recall_memory(question, n_results=3):
    """根据当前的回答，召回相关的长期记忆"""
    #判断记忆库里是不是空的，空了就直接返回，结束函数。
    if memory_collection.count() == 0:
        return ""

    query_embedding = get_embedding(question)
    results = memory_collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )
    memories = results['documents'][0]
    if not memories:
        return ""
    return  "\n".join([f"- {m}" for m in memories])


#压缩函数
def compress_history(messages,max_messages=6):
    """当消息超过max_messages时，把最早的部分压缩成摘要"""
    if len(messages) <= max_messages:
        return messages

    old_messages = messages[:-max_messages]
    recent_messages = messages[-max_messages:]

    #列表推导式 [... for m in old_messages]：
    #f'{m["role"]}: {m["content"]}' 会把每个字典变成一条带角色标签的字符串
    old_text = "\n".join([f'{m["role"]}: {m["content"]}' for m in old_messages])

    # 调用 DeepSeek 生成摘要
    prompt = f"""请总结下面这段对话的核心信息，保留关键事实（用户问过什么、助手回答了什么、用户偏好等），不要遗漏重要细节。用简洁的中文输出，不要解释。

    对话历史：
    {old_text}
    """
    response = deepseek_client.chat.completions.create(
        model="deepseek-flash",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    summary = response.choices[0].message.content.strip()

    # 用一条 system 消息代替旧消息
    compressed = [{"role": "system", "content": f"之前的对话摘要：{summary}"}]
    compressed.extend(recent_messages)
    return compressed

#重写函数
def rewrite_query(question, history):
    """结合历史，把追问改写成独立问题"""
    if not history:
        return question
    # 列表推导式 [... for m in old_messages]：
    # f'{m["role"]}: {m["content"]}' 会把每个字典变成一条带角色标签的字符串
    history_text = "\n".join([f"{m['role']}: {m['content']}"for m in history[-4:]])
    prompt = f"""根据下面的对话历史，把用户最新的问题改写成不依赖上下文、可独立检索的问题。
只输出改写后的问题，不要解释。

对话历史：
{history_text}
用户最新问题：{question}
改写后的问题：
"""
    response = deepseek_client.chat.completions.create(
        model="deepseek-flash",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    #.strip() 就是给字符串“修剪边缘”——去掉字符串开头和结尾的多余空格、换行符、制表符等空白字符。
    #.strip()，拿到的就是最纯粹的问题字符串，无论是拿去做 get_embedding() 还是拼进 prompt，都最干净、最安全。
    return response.choices[0].message.content.strip()

#RAG核心流程：加载 → 切块 → 向量化 → 存储 → 检索 → 增强 → 生成。
# ---------- RAG 核心函数 ----------
def rag_query(question, history, n_results=2):

    standalone_question = rewrite_query(question, history)
    print(f"改写后的问题：{standalone_question}")
    #算向量
    query_embedding = get_embedding(standalone_question)
    #查库
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )
    docs = results['documents'][0]
    print(f"🔍 实际检索到的资料：{docs}")
    context = '\n'.join(f'【文档 {i+1}】{doc}' for i, doc in enumerate(docs))#docs传入context

    #召回长期记忆
    memory_text = recall_memory(standalone_question)

    prompt = f"""你是一个企业知识库助手。请根据下面提供的参考资料回答用户问题。
请根据资料的上下文进行合理的逻辑推断和归纳总结，不要直接照搬原文。
如果你从资料中推导出了答案，请在回答中引用原文作为依据。
只有当资料中完全没有相关信息时，才回复“我没有找到相关资料”。

参考资料：
{context}
用户长期偏好：{memory_text}
用户问题：{question}
"""
    response = deepseek_client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1
    )
    #回答和引用文档
    return response.choices[0].message.content, docs

def rag_query_stream(question, history, n_results=2):
     """流式版 RAG：先检索，再流式生成回答，返回 (生成器, docs)"""

     standalone_question = rewrite_query(question, history)

     query_embedding = get_embedding(standalone_question)
     results = collection.query(
         query_embeddings = [query_embedding],
         n_results = n_results
     )
     docs = results['documents'][0]
     context = '\n'.join(f'【文档{i+1}】{doc}'for i, doc in enumerate(docs))

     memory_text = recall_memory(standalone_question)

     prompt = f"""你是一个企业知识库助手。请根据下面提供的参考资料回答用户问题。
     请根据资料的上下文进行合理的逻辑推断和归纳总结，不要直接照搬原文。
     如果你从资料中推导出了答案，请在回答中引用原文作为依据。
     只有当资料中完全没有相关信息时，才回复“我没有找到相关资料”。

     参考资料：
     {context}

     用户长期偏好：
     {memory_text}

     用户问题：{question}
     """
     stream = deepseek_client.chat.completions.create(
         model = "deepseek-flash",
         messages=[{"role" : "user", "content": prompt}],
         temperature=0.1,
         stream = True
     )

     def generate():
         for chunk in stream:#挨个拿出 API 吐出的碎片
             content = chunk.choices[0].delta.content#提取真正的文字
             if content:
                 yield content#函数会在每次循环时暂停，把文字“挤”给外面，然后等待下一次循环(流式）

     return generate(),docs

# ---------- Streamlit 界面 ----------
#with 块里的所有输出，都进入这个容器，不出现在主页面。！！！！！

#大标题和标题下方显示一行小字
st.title("📄 企业文档问答助手")
st.caption("基于 RAG 的智能问答 Demo | 作者：刘欢")

# 侧边栏显示知识库
with st.sidebar:#告诉 Streamlit，下面的代码全都显示在左侧的侧边栏里。
    st.header("📚 知识库")
    all_data = collection.get()#调用 Chroma 的 get() 方法，把数据库里所有的文档块拿出来。
    st.write(f"当前知识库共有 **{len(all_data['documents'])}** 个文档块")
    with st.expander("查看全部文档块"):#创建一个可折叠的抽屉
        for i, doc in enumerate(all_data['documents']):
            st.write(f"**{i+1}.** {doc[:80]}...")#** 在 Markdown 语法里代表“加粗”。

# 初始化对话历史，建立“档案柜”
if "messages" not in st.session_state:
    st.session_state.messages = []

# 渲染历史消息，session_state 能跨交互周期保存数据
# 把档案柜里的内容贴到屏幕上;msg(message的缩写）
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):# 告诉 Streamlit：“根据这个人的身份，画一个聊天气泡。”
        st.write(msg["content"])#把气泡里的文字填进去。

# 输入框
# 在网页底部显示一个输入框。
user_input = st.chat_input("请输入你的问题（例如：迟到会扣钱吗？）")

if user_input:
    with st.chat_message("user"):# 在页面上画出用户的气泡，并把用户的提问显示出来。
        st.write(user_input)
    #把用户的问题存进全局历史记录
    st.session_state.messages.append({"role": "user", "content": user_input})
    save_memory(user_input)

    with st.chat_message("assistant"):
        with st.spinner("检索中，请稍候..."):#转圈，执行完自动消失
            #调用后端 RAG 函数（向量化 -> 查 Chroma -> 拼提示词 -> 调 DeepSeek）。
            stream, source_docs = rag_query_stream(user_input, st.session_state.messages)
        #用 st.write_stream() 渲染流式输出，它返回完整回答
        answer = st.write_stream(stream)#实现流式输出

        with st.expander("📚 引用来源"):#气泡内再折叠
            for i, doc in enumerate(source_docs):
                st.write(f"**[{i+1}]** {doc}")
    #最后，把 AI 的回答也存进历史记录
    st.session_state.messages.append({"role": "assistant", "content": answer})
    #压缩
    st.session_state.messages = compress_history(st.session_state.messages, max_messages=6)