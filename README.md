# ai-agent-learning

# 企业文档问答助手（RAG Agent）

基于 RAG（检索增强生成）架构的智能文档问答系统，支持上传企业私有文档（PDF/Word/txt），实现带引用来源的精准问答。

---

## 🌐 在线 Demo
- API 文档：https://ai-agent-learning-production-c310.up.railway.app/docs
- 健康检查：https://ai-agent-learning-production-c310.up.railway.app/health
- 根路径导航：https://ai-agent-learning-production-c310.up.railway.app/

---


## 📖 项目简介

本项目是一个基于 **RAG（Retrieval-Augmented Generation）** 架构的企业级文档问答助手。用户上传企业内部文档（员工手册、产品介绍、FAQ 等）后，系统可以基于文档内容回答用户提问，并给出引用来源，有效解决大模型"不知道私有数据"和"幻觉编造"的问题。

---


## ✨ 核心功能


- **📚 私有知识库问答**：基于企业文档回答问题，答案有据可查
- **🔍 语义检索**：使用向量数据库实现"意思相近"的检索，而非关键词匹配
- **💬 多轮对话**：通过查询改写（Query Rewriting）理解"那第三条呢"这类追问
- **🧠 长期记忆**：记住用户偏好（如专业、身份），下次对话自动召回
- **📝 历史压缩**：自动将冗长对话摘要化，控制 Token 消耗
- **⚡ 流式输出**：打字机效果，提升用户体验
- **🛡️ 防幻觉**：资料中无答案时，明确回复"没有找到相关资料"
- **🚀 API 服务**：通过 FastAPI 提供 HTTP 接口，可被任意程序调用



---


## 🛠️ 技术栈

| 模块 | 技术 |
| :--- | :--- |
| 编程语言 | Python 3.11 |
| 前端界面 | Streamlit |
| 后端 API | FastAPI + Uvicorn |
| 向量数据库 | ChromaDB |
| Embedding 模型 | 智谱AI `embedding-2` |
| 大语言模型 | DeepSeek `deepseek-chat` |
| 文档解析 | pypdf |
| 环境管理 | python-dotenv |

---


## 🏗️ 架构图


```
┌─────────────────────────────────────────────────────────┐
│                     离线阶段（数据准备）                  │
│                                                         │
│  本地文档 → 递归切块 → Embedding → 存入 Chroma 向量库    │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                     在线阶段（用户问答）                  │
│                                                         │
│  用户提问                                                │
│     ↓                                                   │
│  查询改写（结合历史，把追问补全为独立问题）               │
│     ↓                                                   │
│  问题向量化（智谱 Embedding API）                        │
│     ↓                                                   │
│  相似度检索（Chroma 余弦相似度匹配）                      │
│     ↓                                                   │
│  召回长期记忆（用户偏好）                                 │
│     ↓                                                   │
│  拼装提示词（参考资料 + 用户问题）                        │
│     ↓                                                   │
│  大模型生成回答（DeepSeek API）                          │
│     ↓                                                   │
│  返回答案 + 引用来源                                     │
└─────────────────────────────────────────────────────────┘
```

---

## 📊 评测数据

基于 20 条测试用例，使用 **LLM-as-Judge** 自动化评测：

| 指标 | 结果 |
| :--- | :--- |
| 测试用例数 | 20 |
| 回答准确率 | **100%** |
| 平均响应时间 | **1.71 秒** |
| 单次调用成本 | **约 ¥0.0002** |
| 20 次调用总成本 | 约 ¥0.0044 |

> 说明：测试集基于当前知识库构建，题目相对直接。生产环境中会引入更复杂的多跳问题与模糊问题来测试系统边界。

---

## 🚀 本地运行指南

### 1. 环境准备

```bash
# 克隆项目
git clone https://github.com/1iu-huan/ai-agent-learning.git
cd ai-agent-learning

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Mac/Linux

# 安装依赖
pip install chromadb pypdf streamlit fastapi uvicorn openai python-dotenv
```

### 2ey

在项目根目录新建 `.env` 文件，填入以下内容：

```env
ZHIPU_API_KEY=
DEEPSEEK_API_KEY=
```

> ⚠️ **安全提醒**：`.env` 文件已加入 `.gitignore`，切勿提交到 GitHub！

### 3. 导入知识库数据

将你的 txt/PDF 文档放入 `data/` 文件夹，然后运行：

```bash
python day19_ingest_data.py
```

看到 `✅ 知识库导入完成！` 表示成功。

### 4. 启动网页 Demo

```bash
streamlit run project3_rag_app.py
```

浏览器会自动打开 `http://localhost:8501`。

### 5. 启动 API 服务（可选）

```bash
uvicorn api_server:app --reload --port 8000
```

访问 `http://localhost:8000/docs` 查看自动生成的 API 文档。

---


## 📁 项目结构

```
ai-agent-learning/
├── data/                       # 知识库原始文档（txt/PDF）
├── chroma_db/                  # Chroma 向量数据库（本地持久化，不提交）
├── .env                        # API Key 配置（不提交）
├── .gitignore
├── day19_ingest_data.py        # 数据导入脚本：读取 → 切块 → 向量化 → 入库
├── project3_rag_app.py         # Streamlit 网页版 RAG 应用
├── api_server.py               # FastAPI 接口服务
├── test_rag.py                 # 自动化评测脚本（20 条测试用例）
└── README.md
```

---

## 🎯 项目亮点

1. **手写底层逻辑**：递归字符切块、查询改写、余弦相似度、ReAct 循环均为手写实现，未使用 LangChain 等框架，能清晰讲清每一步原理。
2. **工程化设计**：离线建库与在线问答分离，通过 Chroma 数据库解耦。
3. **可量化评测**：构建自动化评测流水线，用数据证明系统效果。
4. **用户体验优化**：流式输出 + 多轮记忆 + 引用溯源。

---

## 📄 License

MIT License
```
