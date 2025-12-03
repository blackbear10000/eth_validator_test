FROM python:3.11-slim

# 安装必要的系统依赖
# 注意：不需要安装 docker.io，只需要通过挂载的 socket 访问主机的 Docker
RUN apt-get update && apt-get install -y \
    curl \
    bash \
    && rm -rf /var/lib/apt/lists/*

# 安装 Kurtosis CLI
# 使用官方安装脚本
RUN curl -fsSL https://get.kurtosis.com | bash || \
    (echo "Kurtosis CLI 安装失败" && exit 1)

# 确保 Kurtosis CLI 在 PATH 中
ENV PATH="/root/.kurtosis/bin:${PATH}"

# 验证 Kurtosis CLI 安装（必须成功）
RUN /root/.kurtosis/bin/kurtosis version || \
    (echo "Kurtosis CLI 验证失败，请检查安装" && exit 1)

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

