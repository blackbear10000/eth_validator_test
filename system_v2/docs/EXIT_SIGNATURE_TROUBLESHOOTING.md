# 退出签名验证失败排查指南

## 当前已知信息
- `fork_version`: `0x10000038`
- `genesis_validators_root`: `0x3f205f08426227952a...`
- `epoch`: `381`
- `validator_index`: `136`
- 错误: `BadSignature`

## 可能的原因和排查方法

### 1. **私钥问题** ⚠️ 最可能的原因

**问题**：从 Vault 读取的签名私钥与验证者公钥不匹配。

**排查方法**：
```python
# 在 exit_generator.py 的 generate_exit_signature 方法中添加验证
from py_ecc.bls import G2ProofOfPossession as bls

# 读取私钥后，验证公钥是否匹配
signing_private_key_int = int(signing_private_key_hex, 16)
derived_pubkey = bls.SkToPk(signing_private_key_int)
derived_pubkey_hex = '0x' + derived_pubkey.hex()

if derived_pubkey_hex.lower() != pubkey.lower():
    raise ValueError(f"私钥与公钥不匹配！期望: {pubkey}, 实际: {derived_pubkey_hex}")
```

**检查点**：
- 确认 Vault 中存储的私钥路径是否正确
- 确认 `pubkey` 参数是否正确（是否包含 `0x` 前缀）
- 确认私钥格式是否正确（应该是 64 个十六进制字符，不带 `0x` 前缀）

### 2. **EXIT_FORK_VERSION vs GENESIS_FORK_VERSION**

**问题**：退出签名使用 `EXIT_FORK_VERSION`，而不是 `GENESIS_FORK_VERSION`。某些网络可能不同。

**排查方法**：
```bash
# 查询 Beacon API 获取当前 fork 信息
curl http://localhost:5052/eth/v1/beacon/states/head/fork

# 检查返回的 fork 信息，特别是：
# - current_version: 当前 fork version
# - previous_version: 之前的 fork version
```

**检查点**：
- 确认 `EXIT_FORK_VERSION` 是否应该与 `GENESIS_FORK_VERSION` 相同
- 对于某些网络，`EXIT_FORK_VERSION` 可能是不同的值（如 mainnet 的 Capella fork）

### 3. **Genesis Validators Root 格式问题**

**问题**：`genesis_validators_root` 的格式可能不正确（应该是 32 字节）。

**排查方法**：
```python
# 在 exit_generator.py 中添加验证
genesis_validators_root = beacon_api.get_genesis_validators_root()
if genesis_validators_root:
    # 移除 0x 前缀
    root_hex = genesis_validators_root.replace('0x', '')
    if len(root_hex) != 64:  # 32 bytes = 64 hex chars
        logger.error(f"genesis_validators_root 长度不正确: {len(root_hex)} (期望 64)")
```

**检查点**：
- 确认 `genesis_validators_root` 是 32 字节（64 个十六进制字符）
- 确认格式是否正确（带或不带 `0x` 前缀）

### 4. **Validator Index 错误**

**问题**：`validator_index` 可能不正确。

**排查方法**：
```bash
# 查询 Beacon API 验证 validator_index
curl "http://localhost:5052/eth/v1/beacon/states/head/validators/0x90416bbb2870978b2aef98c9fbf6a4a2cf453d52daf10ee8c4e7a0585da4d8a6388158e902c2eddcc4e670ffa8904088"

# 检查返回的 index 是否与代码中使用的 validator_index (136) 匹配
```

**检查点**：
- 确认从 Beacon API 获取的 `validator_index` 是否正确
- 确认数据库中的 `validator_index` 是否是最新的

### 5. **Epoch 问题**

**问题**：虽然使用了当前 epoch (381)，但 Beacon Chain 可能期望不同的 epoch。

**排查方法**：
```bash
# 查询当前 epoch
curl http://localhost:5052/eth/v1/beacon/states/head/finality_checkpoints

# 检查 finalized_epoch 和 current_justified_epoch
# 退出签名应该使用 finalized_epoch 或 current_justified_epoch，而不是 head epoch
```

**检查点**：
- 确认使用的是 `finalized_epoch` 而不是 `head_epoch`
- 某些 Beacon Chain 实现可能要求使用特定的 epoch（如 finalized 或 justified）

### 6. **签名域（Signing Domain）计算问题**

**问题**：签名域的计算可能有问题。

**排查方法**：
```python
# 在 exit_generator.py 中添加调试代码
from ethstaker_deposit.utils.ssz import compute_voluntary_exit_domain, compute_signing_root
from ethstaker_deposit.utils.ssz import VoluntaryExit

# 手动计算签名域和签名根
message = VoluntaryExit(epoch=epoch, validator_index=validator_index)
domain = compute_voluntary_exit_domain(
    fork_version=self.chain_setting.EXIT_FORK_VERSION,
    genesis_validators_root=self.chain_setting.GENESIS_VALIDATORS_ROOT
)
signing_root = compute_signing_root(message, domain)

logger.info(f"Signing root: 0x{signing_root.hex()}")
logger.info(f"Domain: 0x{domain.hex()}")
logger.info(f"EXIT_FORK_VERSION: 0x{self.chain_setting.EXIT_FORK_VERSION.hex()}")
logger.info(f"GENESIS_VALIDATORS_ROOT: 0x{self.chain_setting.GENESIS_VALIDATORS_ROOT.hex()}")
```

### 7. **Beacon Chain 节点配置问题**

**问题**：Beacon Chain 节点可能使用了不同的网络配置。

**排查方法**：
```bash
# 检查 Beacon Chain 节点的配置
# 对于 Prysm:
docker exec <beacon_container> cat /data/beacon/config.yaml | grep -i fork

# 对于 Lighthouse:
docker exec <beacon_container> lighthouse --help | grep -i fork

# 检查网络配置中的 fork_version 和 genesis_validators_root
```

### 8. **BLS 签名库版本问题**

**问题**：使用的 BLS 签名库版本可能与 Beacon Chain 节点不兼容。

**排查方法**：
```python
# 检查 py_ecc 版本
import py_ecc
print(py_ecc.__version__)

# 检查 ethstaker-deposit-cli 版本
import ethstaker_deposit
print(ethstaker_deposit.__version__)
```

### 9. **签名格式问题**

**问题**：签名的格式可能不正确（应该是 96 字节的 BLS 签名）。

**排查方法**：
```python
# 在生成签名后验证
signature = signed_exit.signature
if len(signature) != 96:  # BLS signature is 96 bytes
    logger.error(f"签名长度不正确: {len(signature)} (期望 96)")
```

## 推荐的排查顺序

1. **首先检查私钥**（最可能的问题）
   - 验证从 Vault 读取的私钥是否与公钥匹配
   - 检查私钥格式和路径

2. **检查 EXIT_FORK_VERSION**
   - 确认是否应该与 GENESIS_FORK_VERSION 不同
   - 查询 Beacon API 获取实际的 fork 信息

3. **验证 validator_index**
   - 从 Beacon API 查询实际的 validator_index
   - 确认与代码中使用的值匹配

4. **检查 epoch**
   - 确认使用的是 finalized_epoch 而不是 head_epoch
   - 某些实现可能要求使用特定的 epoch

5. **检查 genesis_validators_root 格式**
   - 确认长度和格式正确

6. **添加详细日志**
   - 记录签名域、签名根、所有参数的值
   - 便于对比和调试

## 调试代码示例

在 `exit_generator.py` 的 `generate_exit_signature` 方法中添加：

```python
# 验证私钥
from py_ecc.bls import G2ProofOfPossession as bls
derived_pubkey = bls.SkToPk(signing_private_key_int)
derived_pubkey_hex = '0x' + derived_pubkey.hex()
if derived_pubkey_hex.lower() != pubkey.lower():
    logger.error(f"私钥验证失败！期望: {pubkey}, 实际: {derived_pubkey_hex}")
    raise ValueError("私钥与公钥不匹配")

# 记录所有参数
logger.info(f"退出签名参数:")
logger.info(f"  - pubkey: {pubkey}")
logger.info(f"  - validator_index: {validator_index}")
logger.info(f"  - epoch: {epoch}")
logger.info(f"  - EXIT_FORK_VERSION: 0x{self.chain_setting.EXIT_FORK_VERSION.hex()}")
logger.info(f"  - GENESIS_FORK_VERSION: 0x{self.chain_setting.GENESIS_FORK_VERSION.hex()}")
logger.info(f"  - GENESIS_VALIDATORS_ROOT: 0x{self.chain_setting.GENESIS_VALIDATORS_ROOT.hex()}")

# 手动计算签名域（用于调试）
from ethstaker_deposit.utils.ssz import compute_voluntary_exit_domain, compute_signing_root
from ethstaker_deposit.utils.ssz import VoluntaryExit

message = VoluntaryExit(epoch=epoch, validator_index=validator_index)
domain = compute_voluntary_exit_domain(
    fork_version=self.chain_setting.EXIT_FORK_VERSION,
    genesis_validators_root=self.chain_setting.GENESIS_VALIDATORS_ROOT
)
signing_root = compute_signing_root(message, domain)
logger.info(f"  - Signing root: 0x{signing_root.hex()}")
logger.info(f"  - Domain: 0x{domain.hex()}")
```

