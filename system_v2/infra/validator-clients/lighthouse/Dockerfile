# Lighthouse Validator Client Dockerfile
FROM rust:1.75-alpine AS builder

# 安装构建依赖
RUN apk add --no-cache git musl-dev perl make

# 克隆 Lighthouse 仓库
WORKDIR /tmp
RUN git clone https://github.com/sigp/lighthouse.git

# 构建 lighthouse 二进制文件
WORKDIR /tmp/lighthouse
RUN cargo build --release --bin lighthouse

# 运行时镜像
FROM alpine:latest

# 安装必要的运行时依赖
RUN apk add --no-cache ca-certificates tzdata libgcc

# 从构建阶段复制二进制文件
COPY --from=builder /tmp/lighthouse/target/release/lighthouse /usr/local/bin/lighthouse

# 创建配置和数据目录
RUN mkdir -p /config /data

# 设置工作目录
WORKDIR /app

# 默认入口点
ENTRYPOINT ["lighthouse", "validator"]

