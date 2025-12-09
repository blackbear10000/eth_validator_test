"""
管理员 API
数据导出/导入、审计日志查看
"""
import logging
import csv
import json
import io
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime

from app.dependencies import get_db
from app.api.v1.auth import get_current_admin_user
from app.models.database import AuditLog

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/admin/export")
async def export_data(
    format: str = Query("json", regex="^(json|csv)$"),
    tables: Optional[str] = Query(None, description="要导出的表，逗号分隔，如: users,validator_keys"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    """
    导出数据库数据
    
    Args:
        format: 导出格式 (json 或 csv)
        tables: 要导出的表名，逗号分隔。如果为空，导出所有表
    """
    try:
        # 获取所有表名
        if tables:
            table_list = [t.strip() for t in tables.split(",")]
        else:
            # 获取所有表
            result = db.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """))
            table_list = [row[0] for row in result]
        
        if format == "json":
            # JSON 格式导出
            export_data = {}
            for table_name in table_list:
                try:
                    result = db.execute(text(f"SELECT * FROM {table_name}"))
                    rows = result.fetchall()
                    columns = result.keys()
                    
                    export_data[table_name] = [
                        {col: str(val) if val is not None else None for col, val in zip(columns, row)}
                        for row in rows
                    ]
                except Exception as e:
                    logger.error(f"导出表 {table_name} 失败: {e}")
                    export_data[table_name] = {"error": str(e)}
            
            json_str = json.dumps(export_data, indent=2, ensure_ascii=False, default=str)
            return StreamingResponse(
                io.BytesIO(json_str.encode('utf-8')),
                media_type="application/json",
                headers={
                    "Content-Disposition": f"attachment; filename=export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                }
            )
        else:
            # CSV 格式导出（ZIP 压缩多个 CSV 文件）
            import zipfile
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for table_name in table_list:
                    try:
                        result = db.execute(text(f"SELECT * FROM {table_name}"))
                        rows = result.fetchall()
                        columns = result.keys()
                        
                        csv_buffer = io.StringIO()
                        writer = csv.DictWriter(csv_buffer, fieldnames=columns)
                        writer.writeheader()
                        
                        for row in rows:
                            writer.writerow({
                                col: str(val) if val is not None else '' 
                                for col, val in zip(columns, row)
                            })
                        
                        zip_file.writestr(
                            f"{table_name}.csv",
                            csv_buffer.getvalue().encode('utf-8-sig')  # UTF-8 BOM for Excel
                        )
                    except Exception as e:
                        logger.error(f"导出表 {table_name} 失败: {e}")
            
            zip_buffer.seek(0)
            return StreamingResponse(
                zip_buffer,
                media_type="application/zip",
                headers={
                    "Content-Disposition": f"attachment; filename=export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
                }
            )
            
    except Exception as e:
        logger.error(f"导出数据失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")


@router.post("/admin/import")
async def import_data(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    """
    导入数据库数据
    
    支持 JSON 格式导入
    """
    try:
        content = await file.read()
        
        if file.filename.endswith('.json'):
            data = json.loads(content.decode('utf-8'))
            
            imported_tables = []
            errors = []
            
            for table_name, rows in data.items():
                try:
                    if not rows:
                        continue
                    
                    # 获取列名
                    if isinstance(rows, list) and len(rows) > 0:
                        columns = list(rows[0].keys())
                        placeholders = ', '.join([':' + col for col in columns])
                        column_names = ', '.join(columns)
                        
                        # 批量插入
                        insert_sql = f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})"
                        
                        for row in rows:
                            try:
                                db.execute(text(insert_sql), row)
                            except Exception as e:
                                logger.warning(f"插入行失败: {e}")
                                errors.append(f"{table_name}: {str(e)}")
                        
                        db.commit()
                        imported_tables.append(table_name)
                except Exception as e:
                    logger.error(f"导入表 {table_name} 失败: {e}")
                    errors.append(f"{table_name}: {str(e)}")
                    db.rollback()
            
            return JSONResponse({
                "message": "导入完成",
                "imported_tables": imported_tables,
                "errors": errors
            })
        else:
            raise HTTPException(status_code=400, detail="仅支持 JSON 格式")
            
    except Exception as e:
        logger.error(f"导入数据失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


@router.get("/admin/audit-logs")
async def get_audit_logs(
    action: Optional[str] = Query(None, description="操作类型: create/update/delete"),
    resource_type: Optional[str] = Query(None, description="资源类型"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    """
    获取审计日志
    """
    try:
        query = db.query(AuditLog)
        
        if action:
            query = query.filter(AuditLog.action == action)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        if start_date:
            query = query.filter(AuditLog.created_at >= datetime.fromisoformat(start_date))
        if end_date:
            query = query.filter(AuditLog.created_at <= datetime.fromisoformat(end_date))
        
        total = query.count()
        logs = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
        
        return {
            "total": total,
            "items": [
                {
                    "id": log.id,
                    "user_id": log.user_id,
                    "action": log.action,
                    "resource_type": log.resource_type,
                    "resource_id": log.resource_id,
                    "details": log.details,
                    "ip_address": log.ip_address,
                    "created_at": log.created_at.isoformat() if log.created_at else None
                }
                for log in logs
            ]
        }
    except Exception as e:
        logger.error(f"获取审计日志失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取审计日志失败: {str(e)}")

