"""
认证服务
处理用户登录、注册、权限验证等
"""
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from web3 import Web3
from eth_account.messages import encode_defunct

from app.models.database import User
from app.utils.auth import verify_password, get_password_hash, create_access_token, decode_access_token

logger = logging.getLogger(__name__)


class AuthService:
    """认证服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def authenticate_wallet(self, wallet_address: str, signature: str, message: str) -> Optional[User]:
        """
        钱包登录认证（验证签名）
        
        Args:
            wallet_address: 钱包地址
            signature: 签名
            message: 签名的消息
            
        Returns:
            User 对象或 None
        """
        try:
            # 验证签名
            message_hash = encode_defunct(text=message)
            w3 = Web3()
            recovered_address = w3.eth.account.recover_message(message_hash, signature=signature)
            
            if recovered_address.lower() != wallet_address.lower():
                logger.warning(f"签名验证失败: 恢复的地址 {recovered_address} 与提供的地址 {wallet_address} 不匹配")
                return None
            
            # 查找或创建用户
            user = self.db.query(User).filter(
                User.wallet_address == wallet_address.lower()
            ).first()
            
            if not user:
                # 自动创建用户（首次登录）
                user = User(
                    wallet_address=wallet_address.lower(),
                    role="user"
                )
                self.db.add(user)
                self.db.commit()
                self.db.refresh(user)
                logger.info(f"自动创建新用户: {wallet_address[:10]}...")
            
            # 更新最后登录时间
            user.last_login = datetime.utcnow()
            self.db.commit()
            
            return user
            
        except Exception as e:
            logger.error(f"钱包认证失败: {e}", exc_info=True)
            self.db.rollback()
            return None
    
    def authenticate_admin(self, username: str, password: str) -> Optional[User]:
        """
        管理员用户名密码认证
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            User 对象或 None
        """
        try:
            user = self.db.query(User).filter(
                User.username == username,
                User.role == "admin"
            ).first()
            
            if not user:
                logger.warning(f"管理员用户不存在: {username}")
                return None
            
            if not user.password_hash:
                logger.warning(f"管理员用户未设置密码: {username}")
                return None
            
            if not verify_password(password, user.password_hash):
                logger.warning(f"管理员密码错误: {username}")
                return None
            
            # 更新最后登录时间
            user.last_login = datetime.utcnow()
            self.db.commit()
            
            return user
            
        except Exception as e:
            logger.error(f"管理员认证失败: {e}", exc_info=True)
            self.db.rollback()
            return None
    
    def create_admin_user(self, username: str, password: str) -> Optional[User]:
        """
        创建管理员用户
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            创建的 User 对象或 None
        """
        try:
            # 检查是否已存在
            existing = self.db.query(User).filter(
                User.username == username
            ).first()
            
            if existing:
                logger.warning(f"用户已存在: {username}")
                return None
            
            user = User(
                username=username,
                password_hash=get_password_hash(password),
                role="admin"
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            
            logger.info(f"创建管理员用户: {username}")
            return user
            
        except Exception as e:
            logger.error(f"创建管理员用户失败: {e}", exc_info=True)
            self.db.rollback()
            return None
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """根据 ID 获取用户"""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_user_by_wallet(self, wallet_address: str) -> Optional[User]:
        """根据钱包地址获取用户"""
        return self.db.query(User).filter(
            User.wallet_address == wallet_address.lower()
        ).first()
    
    def create_token(self, user: User) -> str:
        """为用户创建 JWT token"""
        token_data = {
            "sub": str(user.id),
            "wallet_address": user.wallet_address,
            "username": user.username,
            "role": user.role
        }
        return create_access_token(token_data)
    
    def verify_token(self, token: str) -> Optional[dict]:
        """验证 token 并返回用户信息"""
        payload = decode_access_token(token)
        if payload is None:
            return None
        
        user_id = payload.get("sub")
        if user_id is None:
            return None
        
        user = self.get_user_by_id(int(user_id))
        if user is None:
            return None
        
        return {
            "id": user.id,
            "wallet_address": user.wallet_address,
            "username": user.username,
            "role": user.role
        }

