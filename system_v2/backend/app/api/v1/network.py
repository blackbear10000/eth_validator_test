"""
网络管理 API
管理 Kurtosis 开发网络的启动、停止和状态查询
"""
from fastapi import APIRouter, HTTPException
from app.services.network_service import NetworkService
from app.models.schemas import NetworkStatusResponse, NetworkInfoResponse

router = APIRouter()


def get_network_service() -> NetworkService:
    """获取网络管理服务"""
    return NetworkService()


@router.get("/network/status", response_model=NetworkStatusResponse)
async def get_network_status():
    """获取网络状态"""
    try:
        service = get_network_service()
        status = service.get_status()
        return NetworkStatusResponse(**status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/network/start")
async def start_network():
    """启动 Kurtosis 网络"""
    try:
        service = get_network_service()
        result = service.start()
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("message", "启动失败"))
        return result
    except Exception as e:
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

