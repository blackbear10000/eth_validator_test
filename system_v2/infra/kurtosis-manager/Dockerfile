FROM python:3.11-slim

# 安装必要的系统依赖
# 注意：不需要安装 docker.io，只需要通过挂载的 socket 访问主机的 Docker
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 Kurtosis CLI
RUN curl -fsSL https://docs.kurtosis.com/install.sh | bash
ENV PATH="/root/.kurtosis/bin:${PATH}"

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 8002

# 启动命令
CMD ["python", "app.py"]

