"""
认证 API
处理用户登录、登出、获取当前用户信息
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.dependencies import get_db
from app.services.auth_service import AuthService

router = APIRouter()
security = HTTPBearer()


class WalletLoginRequest(BaseModel):
    """钱包登录请求"""
    wallet_address: str
    signature: str
    message: str


class AdminLoginRequest(BaseModel):
    """管理员登录请求"""
    username: str
    password: str


class LoginResponse(BaseModel):
    """登录响应"""
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    """用户信息响应"""
    id: int
    wallet_address: Optional[str] = None
    username: Optional[str] = None
    role: str


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> dict:
    """获取当前用户（依赖注入）"""
    token = credentials.credentials
    auth_service = AuthService(db)
    user_info = auth_service.verify_token(token)
    
    if user_info is None:
        raise HTTPException(status_code=401, detail="无效的 token")
    
    return user_info


def get_current_admin_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """获取当前管理员用户（依赖注入）"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


@router.post("/auth/wallet-login", response_model=LoginResponse)
async def wallet_login(
    request: WalletLoginRequest,
    db: Session = Depends(get_db)
):
    """钱包登录"""
    auth_service = AuthService(db)
    user = auth_service.authenticate_wallet(
        request.wallet_address,
        request.signature,
        request.message
    )
    
    if user is None:
        raise HTTPException(status_code=401, detail="钱包认证失败")
    
    token = auth_service.create_token(user)
    
    return LoginResponse(
        access_token=token,
        user={
            "id": user.id,
            "wallet_address": user.wallet_address,
            "username": user.username,
            "role": user.role
        }
    )


@router.post("/auth/admin-login", response_model=LoginResponse)
async def admin_login(
    request: AdminLoginRequest,
    db: Session = Depends(get_db)
):
    """管理员登录"""
    auth_service = AuthService(db)
    user = auth_service.authenticate_admin(request.username, request.password)
    
    if user is None:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    token = auth_service.create_token(user)
    
    return LoginResponse(
        access_token=token,
        user={
            "id": user.id,
            "wallet_address": user.wallet_address,
            "username": user.username,
            "role": user.role
        }
    )


@router.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user)
):
    """获取当前用户信息"""
    return UserResponse(**current_user)


@router.post("/auth/logout")
async def logout():
    """登出（客户端删除 token 即可）"""
    return {"message": "登出成功"}

