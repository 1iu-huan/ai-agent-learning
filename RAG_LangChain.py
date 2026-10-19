import os

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma, vectorstores
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from eval_v2 import retrieve

llm = ChatOpenAI(
    model = "deepseek-flash",
    api_key = os.getenv("DEEPSEEK_API_KEY"),
    base_url = "https://api.deepseek.com/",
    temperature = 0,
    extra_body = {"thinking" : {"type" : "disabled"}},
)

embeddings = OpenAIEmbeddings(
    model = "embedding-2",
    api_key = os.getenv("ZHIPU_API_KEY"),
    base_url = "https://open.bigmodel.cn/api/paas/v4/",
)

vectorstore = Chroma(
    persist_directory = "./chroma_db",
    collection_name = "my_docs",
    embedding_function = embeddings
)
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

prompt = ChatPromptTemplate.from_template(
    "请根据以下资料回答问题，并标注依据的文档编号。\n\n资料：\n{context}\n\n问题：{question}"
)

chain = (
    {"context" : retriever, "question" : RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

print(chain.invoke("病假期间工资按多少发放？"))