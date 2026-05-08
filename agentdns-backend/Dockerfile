# 基础镜像 - 使用Python 3.11 Slim版本
FROM python:3.11-slim

# 设置工作目录 - 在容器内创建并切换到/app目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*  # 清理apt缓存以减小镜像大小

# 复制依赖文件并安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt  # 安装requirements.txt中的所有依赖包

# 复制应用程序代码
COPY . .

# 设置环境变量
ENV PYTHONPATH=/app

# 暴露端口 - 声明容器运行时监听8000端口
EXPOSE 8000

# 启动命令 - 使用uvicorn运行FastAPI应用
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"] 