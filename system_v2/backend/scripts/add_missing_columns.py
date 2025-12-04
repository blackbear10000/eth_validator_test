#!/usr/bin/env python3
"""
直接添加缺失的数据库字段
用于修复现有数据库，无需运行 Alembic 迁移
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.dialects import postgresql
from app.config import settings

def main():
    print("=" * 60)
    print("添加缺失的数据库字段")
    print("=" * 60)
    
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    inspector = inspect(engine)
    
    with engine.connect() as conn:
        # 开始事务
        trans = conn.begin()
        
        try:
            # 1. 检查并添加 validator_keys 表的字段
            if 'validator_keys' in inspector.get_table_names():
                print("\n1. 检查 validator_keys 表...")
                columns = {col['name'] for col in inspector.get_columns('validator_keys')}
                
                # 添加 slashed_at
                if 'slashed_at' not in columns:
                    print("   ➕ 添加 slashed_at 字段...")
                    conn.execute(text("""
                        ALTER TABLE validator_keys 
                        ADD COLUMN slashed_at TIMESTAMP WITHOUT TIME ZONE;
                        COMMENT ON COLUMN validator_keys.slashed_at IS '被惩罚时间';
                    """))
                    print("   ✅ slashed_at 已添加")
                else:
                    print("   ✅ slashed_at 已存在")
                
                # 添加 status_history
                if 'status_history' not in columns:
                    print("   ➕ 添加 status_history 字段...")
                    conn.execute(text("""
                        ALTER TABLE validator_keys 
                        ADD COLUMN status_history JSONB;
                        COMMENT ON COLUMN validator_keys.status_history IS '状态变更历史';
                    """))
                    print("   ✅ status_history 已添加")
                else:
                    print("   ✅ status_history 已存在")
                
                # 添加 mnemonic_encrypted
                if 'mnemonic_encrypted' not in columns:
                    print("   ➕ 添加 mnemonic_encrypted 字段...")
                    conn.execute(text("""
                        ALTER TABLE validator_keys 
                        ADD COLUMN mnemonic_encrypted TEXT;
                        COMMENT ON COLUMN validator_keys.mnemonic_encrypted IS '加密后的助记词（同一批次共享）';
                    """))
                    print("   ✅ mnemonic_encrypted 已添加")
                else:
                    print("   ✅ mnemonic_encrypted 已存在")
                
                # 添加 mnemonic_salt
                if 'mnemonic_salt' not in columns:
                    print("   ➕ 添加 mnemonic_salt 字段...")
                    conn.execute(text("""
                        ALTER TABLE validator_keys 
                        ADD COLUMN mnemonic_salt VARCHAR(64);
                        COMMENT ON COLUMN validator_keys.mnemonic_salt IS '加密盐值';
                    """))
                    print("   ✅ mnemonic_salt 已添加")
                else:
                    print("   ✅ mnemonic_salt 已存在")
            
            # 2. 检查并添加 deposit_transactions 表的字段
            if 'deposit_transactions' in inspector.get_table_names():
                print("\n2. 检查 deposit_transactions 表...")
                columns = {col['name'] for col in inspector.get_columns('deposit_transactions')}
                
                fields_to_add = [
                    ('validated_at', 'TIMESTAMP WITHOUT TIME ZONE', '验证时间'),
                    ('validator_index', 'INTEGER', '验证者索引（beacon chain）'),
                    ('activation_epoch', 'INTEGER', '激活 epoch'),
                    ('exit_epoch', 'INTEGER', '退出 epoch'),
                    ('effective_balance_gwei', 'NUMERIC(20, 0)', '有效余额（gwei）'),
                    ('validation_error', 'TEXT', '验证错误信息（如果无效）'),
                    ('status_history', 'JSONB', '状态变更历史'),
                ]
                
                for field_name, field_type, comment in fields_to_add:
                    if field_name not in columns:
                        print(f"   ➕ 添加 {field_name} 字段...")
                        conn.execute(text(f"""
                            ALTER TABLE deposit_transactions 
                            ADD COLUMN {field_name} {field_type};
                            COMMENT ON COLUMN deposit_transactions.{field_name} IS '{comment}';
                        """))
                        print(f"   ✅ {field_name} 已添加")
                    else:
                        print(f"   ✅ {field_name} 已存在")
                
                # 添加 validator_index 索引
                indexes = {idx['name'] for idx in inspector.get_indexes('deposit_transactions')}
                if 'ix_deposit_transactions_validator_index' not in indexes:
                    print("   ➕ 添加 validator_index 索引...")
                    conn.execute(text("""
                        CREATE INDEX ix_deposit_transactions_validator_index 
                        ON deposit_transactions(validator_index);
                    """))
                    print("   ✅ validator_index 索引已添加")
                else:
                    print("   ✅ validator_index 索引已存在")
            
            # 3. 检查并创建 batch_deposit_contracts 表
            if 'batch_deposit_contracts' not in inspector.get_table_names():
                print("\n3. 创建 batch_deposit_contracts 表...")
                conn.execute(text("""
                    CREATE TABLE batch_deposit_contracts (
                        id SERIAL PRIMARY KEY,
                        contract_address VARCHAR(42) NOT NULL UNIQUE,
                        network_name VARCHAR(64) NOT NULL,
                        rpc_url VARCHAR(256) NOT NULL,
                        deployer_address VARCHAR(42) NOT NULL,
                        deployment_tx_hash VARCHAR(66) NOT NULL UNIQUE,
                        block_number INTEGER,
                        gas_used NUMERIC(20, 0),
                        deployed_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
                        notes TEXT
                    );
                    
                    CREATE INDEX ix_batch_deposit_contracts_contract_address 
                    ON batch_deposit_contracts(contract_address);
                    
                    CREATE INDEX ix_batch_deposit_contracts_deployment_tx_hash 
                    ON batch_deposit_contracts(deployment_tx_hash);
                    
                    CREATE INDEX ix_batch_deposit_contracts_deployed_at 
                    ON batch_deposit_contracts(deployed_at);
                    
                    CREATE INDEX ix_batch_deposit_contracts_network_name 
                    ON batch_deposit_contracts(network_name);
                    
                    CREATE INDEX idx_network_contract 
                    ON batch_deposit_contracts(network_name, contract_address);
                """))
                print("   ✅ batch_deposit_contracts 表已创建")
            else:
                print("\n3. ✅ batch_deposit_contracts 表已存在")
            
            # 4. 修复 deposit_transactions 的唯一约束（如果需要）
            if 'deposit_transactions' in inspector.get_table_names():
                print("\n4. 检查 deposit_transactions 唯一约束...")
                constraints = inspector.get_unique_constraints('deposit_transactions')
                constraint_names = {c['name'] for c in constraints}
                
                # 检查是否有旧的 tx_hash 唯一约束
                has_old_constraint = any('tx_hash' in c['name'] and len(c['column_names']) == 1 
                                       for c in constraints)
                has_new_constraint = 'uq_deposit_pubkey_tx_hash' in constraint_names
                
                if has_old_constraint and not has_new_constraint:
                    print("   ⚠️  检测到旧的 tx_hash 唯一约束，需要修复...")
                    print("   ⚠️  注意：此操作可能需要删除旧约束，请确保没有重复数据")
                    print("   ⚠️  建议手动执行以下 SQL:")
                    print("""
      -- 删除旧的唯一约束
      ALTER TABLE deposit_transactions DROP CONSTRAINT IF EXISTS deposit_transactions_tx_hash_key;
      
      -- 创建新的复合唯一约束
      ALTER TABLE deposit_transactions 
      ADD CONSTRAINT uq_deposit_pubkey_tx_hash UNIQUE (pubkey, tx_hash);
      
      -- 创建复合索引
      CREATE INDEX IF NOT EXISTS idx_deposit_pubkey_tx_hash 
      ON deposit_transactions(pubkey, tx_hash);
                    """)
                elif has_new_constraint:
                    print("   ✅ 唯一约束已正确设置")
                else:
                    print("   ⚠️  未检测到唯一约束，可能需要手动添加")
            
            # 提交事务
            trans.commit()
            print("\n" + "=" * 60)
            print("✅ 所有字段添加完成！")
            print("=" * 60)
            
        except Exception as e:
            trans.rollback()
            print(f"\n❌ 错误: {e}")
            import traceback
            traceback.print_exc()
            raise

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        sys.exit(1)

