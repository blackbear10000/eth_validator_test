# Validator Client Docker 镜像

本目录包含 Validator Client（Prysm、Lighthouse、Teku）的 Dockerfile。

## 构建镜像

### Prysm
```bash
cd prysm
docker build -t prysm-validator:latest .
```

### Lighthouse
```bash
cd lighthouse
docker build -t lighthouse-validator:latest .
```

### Teku
```bash
cd teku
docker build -t teku-validator:latest .
```

## 使用官方镜像（推荐）

如果不想从源码构建，可以使用官方镜像：

- **Prysm**: `gcr.io/prysmaticlabs/prysm/validator:latest`
- **Lighthouse**: `sigp/lighthouse:latest`
- **Teku**: `consensys/teku:latest`

## 注意事项

1. 构建时间可能较长（特别是 Lighthouse，需要编译 Rust）
2. 建议使用官方预构建镜像以提高构建速度
3. 确保镜像版本与网络兼容

