#!/usr/bin/env python3
"""
快速创建管理员账户脚本
用于在系统启动后手动创建管理员账户
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.services.auth_service import AuthService
from app.dependencies import SessionLocal
from app.config import settings

def main():
    """创建管理员账户"""
    print(f"正在创建管理员账户...")
    print(f"用户名: {settings.admin_username}")
    print(f"密码: {'*' * len(settings.admin_password)}")
    
    db = SessionLocal()
    try:
        auth_service = AuthService(db)
        
        # 检查是否已存在
        from app.models.database import User
        existing = db.query(User).filter(
            User.username == settings.admin_username,
            User.role == "admin"
        ).first()
        
        if existing:
            print(f"❌ 管理员账户已存在: {settings.admin_username}")
            print("如果忘记密码，请删除现有账户后重新创建，或直接修改数据库")
            return 1
        
        # 创建管理员账户
        admin = auth_service.create_admin_user(
            settings.admin_username,
            settings.admin_password
        )
        
        if admin:
            print(f"✅ 管理员账户创建成功!")
            print(f"   用户名: {settings.admin_username}")
            print(f"   密码: {settings.admin_password}")
            print(f"\n⚠️  请妥善保管密码，生产环境请修改默认密码！")
            return 0
        else:
            print("❌ 管理员账户创建失败")
            return 1
            
    except Exception as e:
        print(f"❌ 创建管理员账户时出错: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()

if __name__ == "__main__":
    exit(main())

