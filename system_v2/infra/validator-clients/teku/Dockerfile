# Teku Validator Client Dockerfile
# Teku 是 Java 应用，使用官方 OpenJDK 镜像
FROM eclipse-temurin:21-jre-alpine

# 安装必要的运行时依赖
RUN apk add --no-cache tzdata

# 设置 Teku 版本（可以从环境变量覆盖）
ARG TEKU_VERSION=24.1.0
ENV TEKU_VERSION=${TEKU_VERSION}

# 下载 Teku
WORKDIR /opt/teku
RUN wget -q https://artifacts.consensys.net/public/teku/raw/names/teku.tar.gz/versions/${TEKU_VERSION}/teku-${TEKU_VERSION}.tar.gz && \
    tar -xzf teku-${TEKU_VERSION}.tar.gz && \
    rm teku-${TEKU_VERSION}.tar.gz && \
    mv teku-${TEKU_VERSION}/* . && \
    rmdir teku-${TEKU_VERSION}

# 创建配置和数据目录
RUN mkdir -p /config /data

# 设置工作目录
WORKDIR /app

# 创建启动脚本
RUN echo '#!/bin/sh' > /usr/local/bin/teku && \
    echo 'exec java -jar /opt/teku/bin/teku.jar "$@"' >> /usr/local/bin/teku && \
    chmod +x /usr/local/bin/teku

# 默认入口点
ENTRYPOINT ["teku"]

