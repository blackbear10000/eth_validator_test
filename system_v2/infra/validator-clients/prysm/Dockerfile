# Prysm Validator Client Dockerfile
FROM golang:1.21-alpine AS builder

# 安装构建依赖
RUN apk add --no-cache git make gcc musl-dev linux-headers

# 克隆 Prysm 仓库
WORKDIR /tmp
RUN git clone https://github.com/prysmaticlabs/prysm.git

# 构建 validator 二进制文件
WORKDIR /tmp/prysm
RUN go build -o /usr/local/bin/prysm-validator ./cmd/validator

# 运行时镜像
FROM alpine:latest

# 安装必要的运行时依赖
RUN apk add --no-cache ca-certificates tzdata

# 从构建阶段复制二进制文件
COPY --from=builder /usr/local/bin/prysm-validator /usr/local/bin/prysm

# 创建配置和钱包目录
RUN mkdir -p /config /wallet /data

# 设置工作目录
WORKDIR /app

# 默认入口点
ENTRYPOINT ["prysm", "validator"]

