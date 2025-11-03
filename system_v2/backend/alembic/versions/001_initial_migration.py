"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建验证者密钥表
    op.create_table(
        'validator_keys',
        sa.Column('pubkey', sa.String(98), primary_key=True),
        sa.Column('withdrawal_pubkey', sa.String(98), nullable=False),
        sa.Column('signing_key_path', sa.String(64), nullable=False),
        sa.Column('index', sa.Integer(), nullable=False),
        sa.Column('batch_id', sa.String(64), nullable=True),
        sa.Column('status', sa.String(32), nullable=False, server_default='unused'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('activated_at', sa.DateTime(), nullable=True),
        sa.Column('deposited_at', sa.DateTime(), nullable=True),
        sa.Column('exited_at', sa.DateTime(), nullable=True),
        sa.Column('withdrawal_address', sa.String(42), nullable=True),
        sa.Column('client_type', sa.String(32), nullable=True),
        sa.Column('deposit_tx_hash', sa.String(66), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
    )
    
    op.create_index('idx_validator_keys_status', 'validator_keys', ['status'])
    op.create_index('idx_validator_keys_batch_id', 'validator_keys', ['batch_id'])
    op.create_index('idx_validator_keys_client_type', 'validator_keys', ['client_type'])
    op.create_index('idx_validator_keys_created_at', 'validator_keys', ['created_at'])
    
    # 创建客户端实例表
    op.create_table(
        'client_instances',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(128), nullable=False, unique=True),
        sa.Column('client_type', sa.String(32), nullable=False),
        sa.Column('beacon_api_url', sa.String(256), nullable=True),
        sa.Column('grpc_endpoint', sa.String(256), nullable=True),
        sa.Column('web3signer_url', sa.String(256), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('status', sa.String(32), nullable=False, server_default='stopped'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('last_seen_at', sa.DateTime(), nullable=True),
        sa.Column('config_path', sa.String(512), nullable=True),
        sa.Column('pubkey_persistence_path', sa.String(512), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
    )
    
    op.create_index('idx_client_instances_client_type', 'client_instances', ['client_type'])
    op.create_index('idx_client_instances_is_active', 'client_instances', ['is_active'])
    op.create_index('idx_client_instances_created_at', 'client_instances', ['created_at'])
    
    # 创建客户端-密钥映射表
    op.create_table(
        'validator_client_keys',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('pubkey', sa.String(98), nullable=False),
        sa.Column('status', sa.String(32), nullable=False, server_default='active'),
        sa.Column('added_at', sa.DateTime(), nullable=False),
        sa.Column('removed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['client_instances.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['pubkey'], ['validator_keys.pubkey'], ondelete='CASCADE'),
        sa.UniqueConstraint('client_id', 'pubkey', name='uq_client_pubkey'),
    )
    
    op.create_index('idx_validator_client_keys_client_id', 'validator_client_keys', ['client_id'])
    op.create_index('idx_validator_client_keys_pubkey', 'validator_client_keys', ['pubkey'])
    op.create_index('idx_client_pubkey', 'validator_client_keys', ['client_id', 'pubkey'])
    
    # 创建存款交易表
    op.create_table(
        'deposit_transactions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('pubkey', sa.String(98), nullable=False),
        sa.Column('tx_hash', sa.String(66), nullable=False, unique=True),
        sa.Column('batch_id', sa.String(64), nullable=True),
        sa.Column('status', sa.String(32), nullable=False, server_default='pending'),
        sa.Column('amount_wei', sa.Numeric(78, 0), nullable=False),
        sa.Column('amount_eth', sa.Numeric(20, 8), nullable=False),
        sa.Column('submitted_at', sa.DateTime(), nullable=False),
        sa.Column('confirmed_at', sa.DateTime(), nullable=True),
        sa.Column('block_number', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['pubkey'], ['validator_keys.pubkey'], ondelete='CASCADE'),
    )
    
    op.create_index('idx_deposit_transactions_pubkey', 'deposit_transactions', ['pubkey'])
    op.create_index('idx_deposit_transactions_batch_id', 'deposit_transactions', ['batch_id'])
    op.create_index('idx_deposit_transactions_status', 'deposit_transactions', ['status'])
    op.create_index('idx_deposit_transactions_submitted_at', 'deposit_transactions', ['submitted_at'])
    
    # 创建提款事件表
    op.create_table(
        'withdrawal_events',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('pubkey', sa.String(98), nullable=False),
        sa.Column('withdrawal_type', sa.String(32), nullable=False),
        sa.Column('amount_wei', sa.Numeric(78, 0), nullable=False),
        sa.Column('amount_eth', sa.Numeric(20, 8), nullable=False),
        sa.Column('fee_wei', sa.Numeric(78, 0), nullable=False, server_default='0'),
        sa.Column('fee_eth', sa.Numeric(20, 8), nullable=False, server_default='0'),
        sa.Column('fee_rate', sa.Numeric(5, 4), nullable=False, server_default='0.1'),
        sa.Column('withdrawal_index', sa.Integer(), nullable=True),
        sa.Column('slot', sa.Numeric(20, 0), nullable=True),
        sa.Column('epoch', sa.Numeric(20, 0), nullable=True),
        sa.Column('block_number', sa.Integer(), nullable=True),
        sa.Column('withdrawn_at', sa.DateTime(), nullable=False),
        sa.Column('confirmed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['pubkey'], ['validator_keys.pubkey'], ondelete='CASCADE'),
    )
    
    op.create_index('idx_withdrawal_events_pubkey', 'withdrawal_events', ['pubkey'])
    op.create_index('idx_withdrawal_events_withdrawn_at', 'withdrawal_events', ['withdrawn_at'])


def downgrade() -> None:
    op.drop_table('withdrawal_events')
    op.drop_table('deposit_transactions')
    op.drop_table('validator_client_keys')
    op.drop_table('client_instances')
    op.drop_table('validator_keys')

