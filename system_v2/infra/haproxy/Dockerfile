FROM haproxy:2.9

# 安装 curl 用于健康检查
RUN apt-get update && \
    apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/*

# 使用默认的 HAProxy 配置
# 配置文件通过 volume 挂载

