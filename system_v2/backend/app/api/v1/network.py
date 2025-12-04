"""
网络管理 API
管理 Kurtosis 开发网络的启动、停止和状态查询
"""
import logging
from fastapi import APIRouter, HTTPException
from app.services.network_service import NetworkService
from app.models.schemas import NetworkStatusResponse, NetworkInfoResponse

logger = logging.getLogger(__name__)
router = APIRouter()


def get_network_service() -> NetworkService:
    """获取网络管理服务"""
    return NetworkService()


@router.get("/network/status", response_model=NetworkStatusResponse)
async def get_network_status():
    """获取网络状态"""
    try:
        service = get_network_service()
        # 设置较短的超时时间，避免阻塞
        status = service.get_status()
        return NetworkStatusResponse(**status)
    except Exception as e:
        logger.error(f"获取网络状态失败: {e}", exc_info=True)
        # 返回错误状态而不是抛出异常，避免前端完全无法加载
        return NetworkStatusResponse(
            enclave_name=service.enclave_name,
            status="error",
            is_running=False,
            error=str(e)
        )


@router.post("/network/start")
async def start_network():
    """启动 Kurtosis 网络"""
    try:
        service = get_network_service()
        result = service.start()
        
        # 记录详细日志以便调试
        logger.info(f"启动网络结果: success={result.get('success')}, message={result.get('message')}, error={result.get('error')}")
        
        if not result.get("success"):
            error_msg = result.get("message") or result.get("error") or "启动失败"
            logger.error(f"启动网络失败: {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动网络异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/network/stop")
async def stop_network():
    """停止 Kurtosis 网络"""
    try:
        service = get_network_service()
        result = service.stop()
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("message", "停止失败"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/network/info", response_model=NetworkInfoResponse)
async def get_network_info():
    """获取网络详细信息"""
    try:
        service = get_network_service()
        info = service.get_info()
        return NetworkInfoResponse(**info)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/network/rpc-endpoints")
async def get_rpc_endpoints():
    """获取网络的 RPC 端点信息"""
    try:
        service = get_network_service()
        endpoints = service.get_rpc_endpoints()
        return endpoints
    except Exception as e:
        logger.error(f"获取 RPC 端点失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

