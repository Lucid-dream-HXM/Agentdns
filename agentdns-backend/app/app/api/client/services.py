"""
客户服务调用API - 用于客户前端界面
此模块提供客户服务调用的相关API端点，包括服务详情查看、服务调用、流式服务调用等功能
"""

from fastapi import APIRouter, Depends, HTTPException, Request  # FastAPI核心组件，用于创建API路由、依赖注入和HTTP异常处理
from fastapi.responses import StreamingResponse  # FastAPI流式响应类，用于处理流式数据
from sqlalchemy.orm import Session, joinedload  # SQLAlchemy ORM会话和预加载选项，用于数据库查询优化
from typing import Dict, Any, Optional  # 类型提示，用于字典、任意类型和可选类型的标注
from pydantic import BaseModel  # Pydantic基础模型类，用于数据验证
import json  # Python JSON处理模块
import logging  # Python日志模块，用于记录系统日志

from ...database import get_db  # 数据库会话依赖函数，用于获取数据库会话
from ...models.user import User  # 用户模型，用于数据库操作
from ...models.service import Service  # 服务模型，用于数据库操作
from ...models.organization import Organization  # 组织模型，用于数据库操作
from ...core.permissions import (  # 权限管理模块
    PermissionChecker,      # 权限检查器
    service_to_client_format  # 服务数据转换为客户端格式的函数
)
from ...api.deps import get_current_client_user, get_current_principal

# 复用现有的代理逻辑
from ..proxy import (
    find_service_by_path,
    handle_sync_request,
    handle_stream_request,
    handle_async_request,
    query_async_task_status
)

# 创建API路由器实例
router = APIRouter()
# 创建日志记录器
logger = logging.getLogger(__name__)


class ServiceCallRequest(BaseModel):
    """
    服务调用请求数据模型
    
    定义客户端发起服务调用请求时所需的数据结构
    """
    agentdns_url: str          # AgentDNS服务URL，格式为agentdns://org/category/name
    input_data: Dict[str, Any]  # 输入数据，包含服务调用所需的参数
    method: Optional[str] = "POST"  # HTTP方法，默认为POST


@router.get("/{service_id}")
async def get_service_details(
    service_id: int,  # 服务ID
    current_user: User = Depends(get_current_client_user),  # 当前客户端用户依赖
    db: Session = Depends(get_db)  # 数据库会话依赖
):
    """
    获取服务详情 - 仅客户端可用
    
    返回指定服务的详细信息，客户端用户只能访问公开服务
    
    Args:
        service_id: 服务唯一标识符
        current_user: 当前客户端用户对象
        db: 数据库会话对象
    
    Returns:
        服务详细信息，包括服务名称、描述、端点等
    
    Raises:
        HTTPException: 当服务不存在或无权访问时抛出相应错误
    """
    logger.info(f"客户端用户 {current_user.id} 查看服务详情: {service_id}")  # 记录访问日志
    
    try:
        # 查询服务信息，预加载组织信息
        service = db.query(Service).options(joinedload(Service.organization)).filter(
            Service.id == service_id,  # 筛选指定ID的服务
            Service.is_active == True  # 确保服务处于激活状态
        ).first()
        
        if not service:
            raise HTTPException(404, "服务未找到或已停用")  # 服务未找到或已停用
        
        # 检查权限（客户端只能访问公开服务）
        if not service.is_public:
            raise HTTPException(403, "此服务不是公开服务")  # 此服务不是公开服务
        
        # 获取组织名称
        org_name = service.organization.name if service.organization else "未知"  # 未知
        
        # 转换为客户端安全格式
        service_data = service_to_client_format(service, org_name)
        
        logger.info(f"返回服务详情: {service.name}")  # 记录返回日志
        return service_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取服务详情失败: {e}")  # 记录错误日志
        raise HTTPException(500, f"获取服务详情失败: {str(e)}")  # 获取服务详情失败


@router.post("/call")
async def call_service(
    call_request: ServiceCallRequest,
    principal = Depends(get_current_principal),
    db: Session = Depends(get_db)
):
    """
    调用服务 - 仅客户端可用

    第一阶段中，该接口会复用proxy层逻辑，
    并在成功调用后通过响应头返回 usage_id / request_id
    """
    current_user = principal["user"]
    current_agent = principal["agent"]

    PermissionChecker.check_client_access(current_user)

    logger.info(f"客户端用户 {current_user.id} 调用服务: {call_request.agentdns_url}")

    try:
        agentdns_path = call_request.agentdns_url.replace("agentdns://", "")
        service = find_service_by_path(db, agentdns_path)
        if not service:
            raise HTTPException(404, "AgentDNS服务未找到或已停用")

        if not service.is_public:
            raise HTTPException(403, "此服务不是公开服务")

        if service.price_per_unit > 0 and current_user.balance < service.price_per_unit:
            raise HTTPException(402, "余额不足")

        class MockRequest:
            def __init__(self, method: str, body_data: Dict[str, Any]):
                self.method = method
                self._body_data = json.dumps(body_data).encode()
                self.query_params = {}

            async def body(self):
                return self._body_data

        http_mode = service.http_mode or "sync"

        if http_mode == "sync":
            mock_request = MockRequest(call_request.method or "POST", call_request.input_data)
            return await handle_sync_request(service, mock_request, current_user, db, current_agent)

        elif http_mode == "async":
            mock_request = MockRequest("POST", call_request.input_data)
            return await handle_async_request(service, mock_request, current_user, db, current_agent)

        else:
            raise HTTPException(400, "对于流式服务，请使用流式端点")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"调用服务失败: {e}")
        raise HTTPException(500, f"调用服务失败: {str(e)}")


@router.post("/stream/{agentdns_path:path}")
async def stream_service(
    agentdns_path: str,
    request: Request,
    principal = Depends(get_current_principal),
    db: Session = Depends(get_db)
):
    """
    流式调用服务 - 仅客户端可用
    """
    current_user = principal["user"]
    current_agent = principal["agent"]

    PermissionChecker.check_client_access(current_user)

    logger.info(f"客户端用户 {current_user.id} 流式调用服务: {agentdns_path}")

    try:
        service = find_service_by_path(db, agentdns_path)
        if not service:
            raise HTTPException(404, "AgentDNS服务未找到或已停用")

        if not service.is_public:
            raise HTTPException(403, "此服务不是公开服务")

        if service.http_mode != "stream":
            raise HTTPException(400, "此服务不支持流式传输")

        if service.price_per_unit > 0 and current_user.balance < service.price_per_unit:
            raise HTTPException(402, "余额不足")

        return await handle_stream_request(service, request, current_user, db, current_agent)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"流式调用失败: {e}")
        raise HTTPException(500, f"流式调用失败: {str(e)}")


@router.get("/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    principal = Depends(get_current_principal),
    db: Session = Depends(get_db)
):
    """
    查询异步任务状态 - 仅客户端可用
    """
    current_user = principal["user"]

    PermissionChecker.check_client_access(current_user)

    logger.info(f"客户端用户 {current_user.id} 查询任务: {task_id}")

    try:
        return await query_async_task_status(task_id, current_user, db)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        raise HTTPException(500, f"获取任务状态失败: {str(e)}")


@router.get("/resolve/{agentdns_path:path}")
async def resolve_service(
    agentdns_path: str,  # AgentDNS路径
    current_user: User = Depends(get_current_client_user),  # 当前客户端用户依赖
    db: Session = Depends(get_db)  # 数据库会话依赖
):
    """
    解析AgentDNS路径为服务信息
    
    将AgentDNS路径转换为对应的服务详细信息，便于客户端使用
    
    Args:
        agentdns_path: AgentDNS服务路径
        current_user: 当前客户端用户对象
        db: 数据库会话对象
    
    Returns:
        服务工具格式信息
    
    Raises:
        HTTPException: 当服务不存在或无权访问时抛出相应错误
    """
    logger.info(f"客户端用户 {current_user.id} 解析服务: {agentdns_path}")  # 记录解析日志
    
    try:
        # 查找服务
        service = find_service_by_path(db, agentdns_path)
        if not service:
            raise HTTPException(404, "AgentDNS服务未找到或已停用")  # AgentDNS服务未找到或已停用
        
        # 验证权限
        if not service.is_public:
            raise HTTPException(403, "此服务不是公开服务")  # 此服务不是公开服务
        
        # 获取组织信息
        organization = db.query(Organization).filter(
            Organization.id == service.organization_id  # 筛选服务所属组织
        ).first()
        org_name = organization.name if organization else "未知"  # 未知
        
        # 转换为工具格式（客户端安全）
        from ...core.permissions import service_to_tool_format_safe
        tool_info = service_to_tool_format_safe(service, org_name)
        
        logger.info(f"已解析: {service.name}")  # 记录解析完成日志
        return tool_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"解析服务失败: {e}")  # 记录错误日志
        raise HTTPException(500, f"解析服务失败: {str(e)}")  # 解析服务失败


@router.get("/schema/{service_id}")
async def get_service_schema(
    service_id: int,  # 服务ID
    current_user: User = Depends(get_current_client_user),  # 当前客户端用户依赖
    db: Session = Depends(get_db)  # 数据库会话依赖
):
    """
    获取服务输入/输出模式
    
    返回指定服务的输入输出数据结构定义，帮助客户端正确构造请求
    
    Args:
        service_id: 服务唯一标识符
        current_user: 当前客户端用户对象
        db: 数据库会话对象
    
    Returns:
        服务输入输出模式信息
    
    Raises:
        HTTPException: 当服务不存在或无权访问时抛出相应错误
    """
    logger.info(f"客户端用户 {current_user.id} 获取服务模式: {service_id}")  # 记录模式获取日志
    
    try:
        # 查询服务信息
        service = db.query(Service).filter(
            Service.id == service_id,      # 筛选指定ID的服务
            Service.is_active == True,     # 确保服务激活
            Service.is_public == True      # 确保服务公开
        ).first()
        
        if not service:
            raise HTTPException(404, "服务未找到或无法访问")  # 服务未找到或无法访问
        
        # 返回输入输出描述
        schema_info = {
            "service_id": service.id,                             # 服务ID
            "service_name": service.name,                         # 服务名称
            "agentdns_uri": service.agentdns_uri,                 # AgentDNS URI
            "input_schema": service.input_description or "{}",    # 输入模式
            "output_schema": service.output_description or "{}",  # 输出模式
            "http_method": service.http_method or "POST",         # HTTP方法
            "http_mode": service.http_mode or "sync",             # HTTP模式
            "examples": {                                        # 示例
                "input": "参考输入模式",                          # 参考输入模式
                "output": "参考输出模式"                          # 参考输出模式
            }
        }
        
        logger.info(f"返回模式: {service.name}")  # 记录返回日志
        return schema_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取服务模式失败: {e}")  # 记录错误日志
        raise HTTPException(500, f"获取服务模式失败: {str(e)}")  # 获取服务模式失败


@router.get("/categories/{category}/services")
async def get_services_by_category(
    category: str,  # 服务分类
    limit: int = 20,  # 限制数量
    offset: int = 0,  # 偏移量
    current_user: User = Depends(get_current_client_user),  # 当前客户端用户依赖
    db: Session = Depends(get_db)  # 数据库会话依赖
):
    """
    按分类获取服务列表
    
    返回指定分类下的所有公开服务，支持分页功能
    
    Args:
        category: 服务分类名称
        limit: 返回的最大记录数量（分页限制）
        offset: 跳过的记录数量（分页偏移量）
        current_user: 当前客户端用户对象
        db: 数据库会话对象
    
    Returns:
        分类服务列表信息，包括服务列表、总数等
    
    Raises:
        HTTPException: 当查询失败时抛出错误
    """
    logger.info(f"客户端用户 {current_user.id} 获取分类服务: {category}")  # 记录分类查询日志
    
    try:
        # 查询分类下的公开服务
        services = db.query(Service).options(joinedload(Service.organization)).filter(
            Service.category == category,      # 筛选指定分类
            Service.is_active == True,         # 确保服务激活
            Service.is_public == True          # 确保服务公开
        ).offset(offset).limit(limit).all()
        
        # 转换为客户端格式
        results = []
        for service in services:
            org_name = service.organization.name if service.organization else "未知"  # 未知
            service_data = service_to_client_format(service, org_name)
            results.append(service_data)
        
        logger.info(f"返回 {len(results)} 个分类 {category} 下的服务")  # 记录返回结果日志
        return {
            "category": category,      # 分类名称
            "services": results,       # 服务列表
            "total": len(results),     # 总数
            "offset": offset,          # 偏移量
            "limit": limit             # 限制数量
        }
        
    except Exception as e:
        logger.error(f"按分类获取服务失败: {e}")  # 记录错误日志
        raise HTTPException(500, f"按分类获取服务失败: {str(e)}")  # 按分类获取服务失败