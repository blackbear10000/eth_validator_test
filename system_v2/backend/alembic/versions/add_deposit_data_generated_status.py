"""add deposit_data_generated status to validator_keys

Revision ID: add_deposit_data_generated
Revises: 113ec78fdd17
Create Date: 2025-12-05 00:32:34.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_deposit_data_generated'
down_revision = '113ec78fdd17'  # 依赖于 add_slashed_at_and_status_history 迁移
branch_labels = None
depends_on = None


def upgrade():
    """
    添加 DEPOSIT_DATA_GENERATED 状态支持
    
    注意：由于 validator_keys.status 字段是 String(32) 类型，
    它已经可以接受新的状态值，所以不需要修改数据库表结构。
    这个迁移文件主要用于文档化和版本控制。
    
    新状态：deposit_data_generated
    - 用途：标记已生成 Deposit Data 但尚未提交存款的密钥
    - 状态转换：ACTIVE -> DEPOSIT_DATA_GENERATED -> PENDING
    - 特点：此状态的密钥可以加载到客户端
    """
    # 不需要实际的数据库变更，因为 status 字段已经是 String 类型
    # 但我们可以添加一个注释说明（如果数据库支持）
    pass


def downgrade():
    """
    回滚：移除 DEPOSIT_DATA_GENERATED 状态支持
    
    注意：由于没有实际的数据库变更，回滚也不需要操作。
    但建议将状态为 deposit_data_generated 的密钥迁移回 active 状态。
    """
    # 可选：将 deposit_data_generated 状态的密钥迁移回 active
    # op.execute("""
    #     UPDATE validator_keys
    #     SET status = 'active'
    #     WHERE status = 'deposit_data_generated'
    # """)
    pass

