# 使用官方Python镜像作为基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 创建数据目录
RUN mkdir -p /data/rss /data/cache

# 设置数据目录的环境变量
ENV AI_RSS_FILTER_DATA_DIR=/data

# 暴露端口
EXPOSE 8000

# 设置启动命令
CMD ["python", "-m", "src.main"]
