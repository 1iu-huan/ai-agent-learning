#1.使用官方Python镜像作为基础
FROM python:3.11-slim

#2.设置工作目录
WORKDIR /app

#3.复制依赖清单（利用Docker缓存加速）
COPY requirements.txt .

#4.安装依赖（使用清华源加速）
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

#5.复制项目
COPY . .

# 6. 暴露端口（FastAPI 默认 8000）
EXPOSE 8000

# 7. 启动命令
CMD ["uvicorn", "api_server:app", "--host", "0.0.0. ", "--port", "8000"]