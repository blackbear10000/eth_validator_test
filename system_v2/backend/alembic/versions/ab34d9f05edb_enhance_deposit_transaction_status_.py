"""enhance_deposit_transaction_status_fields

Revision ID: ab34d9f05edb
Revises: 742b2ef76cff
Create Date: 2025-12-04 15:04:25.596374

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'ab34d9f05edb'
down_revision = '742b2ef76cff'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 添加新字段
    op.add_column('deposit_transactions', sa.Column('validated_at', sa.DateTime(), nullable=True, comment='验证时间'))
    op.add_column('deposit_transactions', sa.Column('validator_index', sa.Integer(), nullable=True, comment='验证者索引（beacon chain）'))
    op.add_column('deposit_transactions', sa.Column('activation_epoch', sa.Integer(), nullable=True, comment='激活 epoch'))
    op.add_column('deposit_transactions', sa.Column('exit_epoch', sa.Integer(), nullable=True, comment='退出 epoch'))
    op.add_column('deposit_transactions', sa.Column('effective_balance_gwei', sa.Numeric(precision=20, scale=0), nullable=True, comment='有效余额（gwei）'))
    op.add_column('deposit_transactions', sa.Column('validation_error', sa.Text(), nullable=True, comment='验证错误信息（如果无效）'))
    op.add_column('deposit_transactions', sa.Column('status_history', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='状态变更历史'))
    
    # 创建索引
    op.create_index(op.f('ix_deposit_transactions_validator_index'), 'deposit_transactions', ['validator_index'], unique=False)
    
    # 迁移现有数据：将 PENDING 状态改为 SUBMITTED
    op.execute("""
        UPDATE deposit_transactions 
        SET status = 'submitted' 
        WHERE status = 'pending'
    """)


def downgrade() -> None:
    # 删除索引
    op.drop_index(op.f('ix_deposit_transactions_validator_index'), table_name='deposit_transactions')
    
    # 删除新字段
    op.drop_column('deposit_transactions', 'status_history')
    op.drop_column('deposit_transactions', 'validation_error')
    op.drop_column('deposit_transactions', 'effective_balance_gwei')
    op.drop_column('deposit_transactions', 'exit_epoch')
    op.drop_column('deposit_transactions', 'activation_epoch')
    op.drop_column('deposit_transactions', 'validator_index')
    op.drop_column('deposit_transactions', 'validated_at')
    
    # 恢复 PENDING 状态（如果需要）
    op.execute("""
        UPDATE deposit_transactions 
        SET status = 'pending' 
        WHERE status = 'submitted'
    """)
