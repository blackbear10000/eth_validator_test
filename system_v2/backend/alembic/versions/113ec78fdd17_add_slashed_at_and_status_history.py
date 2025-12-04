"""add slashed_at and status_history to validator_keys

Revision ID: 113ec78fdd17
Revises: fix_tx_hash_unique
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '113ec78fdd17'
down_revision = 'fix_tx_hash_unique'  # 依赖于 fix_deposit_transaction_tx_hash_unique 迁移
branch_labels = None
depends_on = None


def upgrade():
    # 添加 slashed_at 字段
    op.add_column('validator_keys', sa.Column('slashed_at', sa.DateTime(), nullable=True, comment='被惩罚时间'))
    
    # 添加 status_history 字段（JSON 类型）
    op.add_column('validator_keys', sa.Column('status_history', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='状态变更历史'))


def downgrade():
    # 移除 status_history 字段
    op.drop_column('validator_keys', 'status_history')
    
    # 移除 slashed_at 字段
    op.drop_column('validator_keys', 'slashed_at')

