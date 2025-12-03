FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（包括 Node.js 和 npm，用于安装 OpenZeppelin 合约依赖）
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    git \
    ca-certificates \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码（包括诊断脚本）
COPY . .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

