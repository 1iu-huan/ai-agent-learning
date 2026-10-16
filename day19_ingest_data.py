import os
import chromadb
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(
    api_key=os.getenv("ZHIPU_API_KEY"),
    base_url="https://open.bigmodel.cn/api/paas/v4/"
)


def get_embedding(text):
    response = client.embeddings.create(
        model="embedding-2",
        input=text
    )
    return response.data[0].embedding


def simple_recursive_split(text, chunk_size=500, overlap=50):
    """简化版递归切块：先按段落切，再按句子切，最后按字符切"""
    separators = ["\n\n", "\n", "。", "！", "？", " "]

    def _split(text, sep_index=0):
        if len(text) <= chunk_size:
            return [text]

        sep = separators[sep_index] if sep_index < len(separators) else ""
        parts = text.split(sep) if sep else list(text)

        chunks = []
        current = ""
        for part in parts:
            if len(current) + len(part) + len(sep) <= chunk_size:
                current += part + sep
            else:
                if current:
                    chunks.append(current)
                current = part + sep
        if current:
            chunks.append(current)

        result = []
        for chunk in chunks:
            if len(chunk) > chunk_size and sep_index < len(separators) - 1:
                result.extend(_split(chunk, sep_index + 1))
            else:
                result.append(chunk)
        return result

    raw_chunks = _split(text)
    overlapped_chunks = []
    for i, chunk in enumerate(raw_chunks):
        if i > 0:
            chunk = raw_chunks[i - 1][-overlap:] + chunk
        overlapped_chunks.append(chunk)
    return overlapped_chunks


def load_data():
    """读取 data 文件夹，切块，存入 Chroma"""
    chroma_client = chromadb.PersistentClient(path="./chroma_db")
    collection = chroma_client.get_or_create_collection(name="my_docs")

    all_chunks = []
    for filename in os.listdir("data"):
        if filename.endswith(".txt"):
            with open(f"data/{filename}", "r", encoding="utf-8") as f:
                text = f.read()
            chunks = simple_recursive_split(text, chunk_size=300, overlap=50)
            all_chunks.extend(chunks)

    print(f"准备导入 {len(all_chunks)} 个文档块...")
    ids = [f"chunk_{i}" for i in range(len(all_chunks))]
    embeddings = [get_embedding(chunk) for chunk in all_chunks]

    collection.add(
        documents=all_chunks,
        embeddings=embeddings,
        ids=ids
    )
    print("✅ 知识库导入完成！")
    return collection


if __name__ == "__main__":
    load_data()