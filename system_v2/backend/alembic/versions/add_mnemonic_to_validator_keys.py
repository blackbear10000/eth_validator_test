"""add mnemonic fields to validator_keys

Revision ID: c74d483d28d5
Revises: ab34d9f05edb
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c74d483d28d5'
down_revision = 'ab34d9f05edb'
branch_labels = None
depends_on = None


def upgrade():
    # 添加助记词相关字段
    op.add_column('validator_keys', sa.Column('mnemonic_encrypted', sa.Text(), nullable=True, comment='加密后的助记词（同一批次共享）'))
    op.add_column('validator_keys', sa.Column('mnemonic_salt', sa.String(length=64), nullable=True, comment='加密盐值'))


def downgrade():
    # 移除助记词相关字段
    op.drop_column('validator_keys', 'mnemonic_salt')
    op.drop_column('validator_keys', 'mnemonic_encrypted')

