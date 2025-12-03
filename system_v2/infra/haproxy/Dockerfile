FROM haproxy:2.9

# HAProxy 官方镜像默认以非 root 用户运行
# 需要切换到 root 用户来安装软件包
USER root

# 安装 curl 用于健康检查
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# HAProxy 镜像默认以 haproxy 用户运行，但我们需要保持 root 以执行健康检查
# 如果需要，可以切换回 haproxy 用户，但健康检查可能需要 root 权限
# USER haproxy

# 使用默认的 HAProxy 配置
# 配置文件通过 volume 挂载

