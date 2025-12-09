"""
审计日志中间件
自动记录所有写操作（POST/PUT/DELETE）
"""
import logging
from typing import Callable
from fastapi import Request, Response
from sqlalchemy.orm import Session
from app.dependencies import SessionLocal
from app.models.database import AuditLog
from app.api.v1.auth import get_current_user
from fastapi.security import HTTPBearer
from fastapi import HTTPException

logger = logging.getLogger(__name__)
security = HTTPBearer()


async def audit_middleware(request: Request, call_next: Callable) -> Response:
    """
    审计日志中间件
    记录所有写操作（POST/PUT/DELETE）
    """
    # 只记录写操作
    if request.method not in ["POST", "PUT", "DELETE", "PATCH"]:
        return await call_next(request)
    
    # 跳过某些不需要审计的路径
    skip_paths = ["/health", "/docs", "/redoc", "/openapi.json", "/auth/"]
    if any(request.url.path.startswith(path) for path in skip_paths):
        return await call_next(request)
    
    # 获取用户信息（如果已认证）
    user_id = None
    try:
        # 尝试从 Authorization header 获取 token
        authorization = request.headers.get("Authorization")
        if authorization and authorization.startswith("Bearer "):
            token = authorization.replace("Bearer ", "")
            from app.utils.auth import decode_access_token
            payload = decode_access_token(token)
            if payload:
                user_id = int(payload.get("sub", 0))
    except Exception as e:
        logger.debug(f"获取用户信息失败（可能未登录）: {e}")
    
    # 执行请求
    response = await call_next(request)
    
    # 只记录成功的写操作（2xx 状态码）
    if 200 <= response.status_code < 300:
        try:
            db = SessionLocal()
            try:
                # 提取资源类型和ID（从路径推断）
                resource_type = _extract_resource_type(request.url.path)
                resource_id = _extract_resource_id(request.url.path, request.method)
                
                # 创建审计日志
                audit_log = AuditLog(
                    user_id=user_id if user_id else None,
                    action=request.method.lower(),
                    resource_type=resource_type,
                    resource_id=resource_id,
                    ip_address=request.client.host if request.client else None,
                )
                db.add(audit_log)
                db.commit()
            except Exception as e:
                logger.error(f"记录审计日志失败: {e}", exc_info=True)
                db.rollback()
            finally:
                db.close()
        except Exception as e:
            logger.error(f"创建数据库会话失败: {e}")
    
    return response


def _extract_resource_type(path: str) -> str:
    """从路径提取资源类型"""
    parts = path.strip("/").split("/")
    if len(parts) >= 2:
        # 例如: /api/v1/keys -> keys
        return parts[-1].rstrip("s")  # 移除复数形式
    return "unknown"


def _extract_resource_id(path: str, method: str) -> str:
    """从路径提取资源ID"""
    parts = path.strip("/").split("/")
    if len(parts) >= 3:
        # 例如: /api/v1/keys/123 -> 123
        return parts[-1]
    elif method == "POST":
        # POST 请求可能创建新资源，ID未知
        return "new"
    return "unknown"

