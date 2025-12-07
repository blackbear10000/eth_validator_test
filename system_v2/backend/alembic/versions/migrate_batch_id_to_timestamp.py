"""Migrate batch_id from tx_hash to timestamp format

Revision ID: migrate_batch_id_timestamp
Revises: fix_deposit_transaction_tx_hash_unique
Create Date: 2024-12-07 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from datetime import datetime


# revision identifiers, used by Alembic.
revision = 'migrate_batch_id_timestamp'
down_revision = 'add_deposit_data_generated'  # 依赖于最新的迁移
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    将 deposit_transactions 表中的 batch_id 从交易哈希格式迁移为时间戳格式
    
    迁移规则：
    1. 查找所有 batch_id 是交易哈希格式的记录（长度66字符，以 0x 开头）
    2. 对于这些记录，基于 submitted_at 时间生成新的批次ID
    3. 对于同一 tx_hash 的所有记录，使用相同的时间戳（基于最早的 submitted_at）
    """
    connection = op.get_bind()
    
    # 查找所有需要迁移的记录（batch_id 是交易哈希格式：长度66，以 0x 开头）
    result = connection.execute(text("""
        SELECT DISTINCT tx_hash, batch_id
        FROM deposit_transactions
        WHERE batch_id IS NOT NULL
          AND LENGTH(batch_id) = 66
          AND batch_id LIKE '0x%'
    """))
    
    tx_hashes_to_migrate = {}
    for row in result:
        tx_hash = row[0]
        old_batch_id = row[1]
        if tx_hash not in tx_hashes_to_migrate:
            tx_hashes_to_migrate[tx_hash] = old_batch_id
    
    if not tx_hashes_to_migrate:
        print("没有需要迁移的记录")
        return
    
    print(f"找到 {len(tx_hashes_to_migrate)} 个需要迁移的交易")
    
    # 为每个 tx_hash 生成新的批次ID
    for tx_hash, old_batch_id in tx_hashes_to_migrate.items():
        # 获取该交易的所有记录中最早的 submitted_at
        earliest_result = connection.execute(text("""
            SELECT MIN(submitted_at) as earliest_time
            FROM deposit_transactions
            WHERE tx_hash = :tx_hash
        """), {"tx_hash": tx_hash})
        
        earliest_row = earliest_result.fetchone()
        if not earliest_row or not earliest_row[0]:
            # 如果没有 submitted_at，使用当前时间
            batch_timestamp = datetime.utcnow()
            print(f"警告: 交易 {tx_hash[:10]}... 没有 submitted_at，使用当前时间")
        else:
            batch_timestamp = earliest_row[0]
            if isinstance(batch_timestamp, str):
                # 如果是字符串，尝试解析
                try:
                    batch_timestamp = datetime.fromisoformat(batch_timestamp.replace('Z', '+00:00'))
                except:
                    batch_timestamp = datetime.utcnow()
        
        # 生成新的批次ID
        new_batch_id = f"batch-{batch_timestamp.strftime('%Y%m%d-%H%M%S')}"
        
        # 更新该交易的所有记录
        connection.execute(text("""
            UPDATE deposit_transactions
            SET batch_id = :new_batch_id
            WHERE tx_hash = :tx_hash
              AND batch_id = :old_batch_id
        """), {
            "new_batch_id": new_batch_id,
            "tx_hash": tx_hash,
            "old_batch_id": old_batch_id
        })
        
        print(f"迁移交易 {tx_hash[:10]}...: {old_batch_id[:20]}... -> {new_batch_id}")
    
    print(f"迁移完成: 共迁移 {len(tx_hashes_to_migrate)} 个交易的批次ID")


def downgrade() -> None:
    """
    回滚迁移：将时间戳格式的 batch_id 恢复为交易哈希
    
    注意：这个回滚操作会丢失原始的批次ID信息，因为无法从时间戳恢复交易哈希
    因此，回滚时会将 batch_id 设置为 NULL
    """
    connection = op.get_bind()
    
    # 查找所有时间戳格式的 batch_id（以 batch- 开头，格式为 batch-YYYYMMDD-HHMMSS）
    result = connection.execute(text("""
        SELECT DISTINCT tx_hash, batch_id
        FROM deposit_transactions
        WHERE batch_id IS NOT NULL
          AND batch_id LIKE 'batch-%'
          AND LENGTH(batch_id) = 20
    """))
    
    tx_hashes_to_rollback = {}
    for row in result:
        tx_hash = row[0]
        batch_id = row[1]
        if tx_hash not in tx_hashes_to_rollback:
            tx_hashes_to_rollback[tx_hash] = batch_id
    
    if not tx_hashes_to_rollback:
        print("没有需要回滚的记录")
        return
    
    print(f"找到 {len(tx_hashes_to_rollback)} 个需要回滚的交易")
    
    # 由于无法从时间戳恢复交易哈希，将 batch_id 设置为 NULL
    for tx_hash, batch_id in tx_hashes_to_rollback.items():
        connection.execute(text("""
            UPDATE deposit_transactions
            SET batch_id = NULL
            WHERE tx_hash = :tx_hash
              AND batch_id = :batch_id
        """), {
            "tx_hash": tx_hash,
            "batch_id": batch_id
        })
        
        print(f"回滚交易 {tx_hash[:10]}...: {batch_id} -> NULL")
    
    print(f"回滚完成: 共回滚 {len(tx_hashes_to_rollback)} 个交易的批次ID")

