FROM python:3.11-slim

# 安装必要的系统依赖
# 注意：不需要安装 docker.io，只需要通过挂载的 socket 访问主机的 Docker
RUN apt-get update && apt-get install -y \
    curl \
    bash \
    gnupg \
    ca-certificates \
    dbus \
    && rm -rf /var/lib/apt/lists/*

# 安装 Kurtosis CLI（使用官方 apt 仓库方法）
# 参考：https://docs.kurtosis.com/install
RUN echo "deb [trusted=yes] https://apt.fury.io/kurtosis-tech/ /" | tee /etc/apt/sources.list.d/kurtosis.list && \
    apt-get update && \
    apt-get install -y kurtosis-cli && \
    rm -rf /var/lib/apt/lists/*

# 创建 /etc/machine-id 文件（Kurtosis CLI 需要此文件来生成匿名用户 ID）
# 如果文件不存在，Kurtosis 会尝试创建 metrics client 时失败
# 即使禁用了 telemetry，Kurtosis 可能仍然需要这个文件进行初始化
RUN if [ ! -f /etc/machine-id ]; then \
        echo "生成 machine-id..." && \
        dbus-uuidgen > /etc/machine-id 2>/dev/null || \
        (cat /proc/sys/kernel/random/uuid 2>/dev/null > /etc/machine-id || \
         echo "$(date +%s | sha256sum | head -c 32)" > /etc/machine-id); \
    fi && \
    echo "machine-id 内容:" && \
    cat /etc/machine-id

# 验证 Kurtosis CLI 安装（必须成功）
RUN kurtosis version || \
    (echo "Kurtosis CLI 验证失败，请检查安装" && exit 1)

# 禁用 analytics/metrics（避免网络连接问题）
# 尝试使用命令禁用，如果失败则手动设置配置文件
RUN KURTOSIS_DISABLE_TELEMETRY=true kurtosis analytics disable 2>/dev/null || \
    (echo "注意: analytics disable 命令可能不支持，将在运行时处理")

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

