"""fix deposit_transaction tx_hash unique constraint

Revision ID: fix_tx_hash_unique
Revises: c74d483d28d5
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fix_tx_hash_unique'
down_revision = 'c74d483d28d5'  # 依赖于 add_mnemonic_to_validator_keys 迁移
branch_labels = None
depends_on = None


def upgrade():
    # 1. 删除旧的唯一约束和索引
    # 先删除唯一约束（如果存在）
    try:
        op.drop_constraint('deposit_transactions_tx_hash_key', 'deposit_transactions', type_='unique')
    except Exception:
        # 约束可能不存在或名称不同，继续
        pass
    
    # 删除旧的索引（如果存在）
    try:
        op.drop_index('ix_deposit_transactions_tx_hash', table_name='deposit_transactions')
    except Exception:
        # 索引可能不存在，继续
        pass
    
    # 2. 重新创建索引（不带唯一约束）
    op.create_index('ix_deposit_transactions_tx_hash', 'deposit_transactions', ['tx_hash'], unique=False)
    
    # 3. 创建复合唯一约束 (pubkey, tx_hash)
    op.create_unique_constraint('uq_deposit_pubkey_tx_hash', 'deposit_transactions', ['pubkey', 'tx_hash'])
    
    # 4. 创建复合索引
    op.create_index('idx_deposit_pubkey_tx_hash', 'deposit_transactions', ['pubkey', 'tx_hash'], unique=False)


def downgrade():
    # 删除复合唯一约束和索引
    op.drop_constraint('uq_deposit_pubkey_tx_hash', 'deposit_transactions', type_='unique')
    op.drop_index('idx_deposit_pubkey_tx_hash', table_name='deposit_transactions')
    
    # 删除 tx_hash 索引
    op.drop_index('ix_deposit_transactions_tx_hash', table_name='deposit_transactions')
    
    # 恢复原来的唯一约束
    op.create_unique_constraint('deposit_transactions_tx_hash_key', 'deposit_transactions', ['tx_hash'])
    op.create_index('ix_deposit_transactions_tx_hash', 'deposit_transactions', ['tx_hash'], unique=True)

