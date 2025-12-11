FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（包括 Node.js 和 npm，用于安装 OpenZeppelin 合约依赖）
# 同时安装 Docker CLI，用于管理 Validator Client 容器
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    git \
    ca-certificates \
    gnupg \
    lsb-release \
    wget \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && chmod a+r /etc/apt/keyrings/docker.gpg \
    && echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
    $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y docker-cli \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 预安装 Solidity 编译器 0.8.29（从 GitHub releases 下载，避免 solc-bin.ethereum.org 的 Cloudflare 403 错误）
# solcx 会在 ~/.solcx 目录下查找已安装的版本
RUN SOLC_VERSION="0.8.29" && \
    SOLCX_DIR="/root/.solcx" && \
    mkdir -p $SOLCX_DIR && \
    wget -q "https://github.com/ethereum/solidity/releases/download/v${SOLC_VERSION}/solc-static-linux" -O "${SOLCX_DIR}/solc-v${SOLC_VERSION}" && \
    chmod +x "${SOLCX_DIR}/solc-v${SOLC_VERSION}" && \
    # 验证安装
    "${SOLCX_DIR}/solc-v${SOLC_VERSION}" --version && \
    echo "✅ Solidity 编译器 ${SOLC_VERSION} 已预安装到 ${SOLCX_DIR}"

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

