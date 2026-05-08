"""
客户端服务发现API - 用于客户前端
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from pydantic import BaseModel, Field
import logging

from ...database import get_db
from ...models.user import User
from ...models.service import Service
from ...models.organization import Organization
from ...models.review import ServiceTrustStats
from ...services.search_engine import SearchEngine
from ...core.permissions import (
    PermissionChecker,
    service_to_client_format,
    service_to_tool_format_safe,
    attach_trust_summary
)
from ...api.deps import get_current_client_user

router = APIRouter()
logger = logging.getLogger(__name__)


class ServiceSearchRequest(BaseModel):
    """客户端服务搜索请求"""
    query: str = Field(..., min_length=1)
    category: Optional[str] = None
    organization: Optional[str] = None
    protocol: Optional[str] = None
    max_price: Optional[float] = Field(None, ge=0)
    limit: int = Field(10, ge=1, le=50)
    return_tool_format: bool = True
    sort_by: Optional[str] = "balanced"
    include_trust: Optional[bool] = True
    min_trust_score: Optional[float] = Field(None, ge=0, le=100)


class ServiceSearchResponse(BaseModel):
    """客户端服务搜索响应"""
    tools: List[dict] = []
    services: List[dict] = []
    total: int = 0
    query: str


@router.post("/search", response_model=ServiceSearchResponse)
async def search_services(
    search_request: ServiceSearchRequest,
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """
    智能AI服务搜索 - 仅客户端可用
    支持自然语言搜索，仅返回公开服务
    """
    logger.info(f"客户端用户 {current_user.id} 搜索服务: {search_request.query}")
    
    try:
        # 创建搜索引擎
        search_engine = SearchEngine(db)
        
        # 执行搜索（客户端只能搜索公开服务）
        results, total = search_engine.search(
            query=search_request.query,
            category=search_request.category,
            organization=search_request.organization,
            protocol=search_request.protocol,
            max_price=search_request.max_price,
            limit=search_request.limit,
            return_tool_format=search_request.return_tool_format,
            sort_by=search_request.sort_by or "balanced",
            include_trust=search_request.include_trust if search_request.include_trust is not None else True,
            min_trust_score=search_request.min_trust_score
        )
        
        logger.info(f"搜索完成，返回 {len(results)} 个服务")
        
        # 根据格式构建响应
        if search_request.return_tool_format:
            return ServiceSearchResponse(
                tools=results,
                services=[],
                total=total,
                query=search_request.query
            )
        else:
            return ServiceSearchResponse(
                tools=[],
                services=results,
                total=total,
                query=search_request.query
            )
            
    except Exception as e:
        logger.error(f"搜索服务失败: {e}")
        raise HTTPException(500, f"搜索失败: {str(e)}")


@router.get("/trending")
async def get_trending_services(
    limit: int = Query(10, ge=1, le=50),
    return_tool_format: bool = Query(True),
    db: Session = Depends(get_db)
):
    """获取热门服务 - 基于使用情况（无需认证）"""
    logger.info(f"获取热门服务, limit: {limit}")

    try:
        services_query = db.query(Service).filter(
            Service.is_active == True,
            Service.is_public == True
        ).options(joinedload(Service.organization)).order_by(
            Service.created_at.desc()
        ).limit(limit)

        services = services_query.all()

        service_ids = [service.id for service in services]
        trust_map = {}

        if service_ids:
            trust_stats_list = db.query(ServiceTrustStats).filter(
                ServiceTrustStats.service_id.in_(service_ids)
            ).all()
            trust_map = {item.service_id: item for item in trust_stats_list}

        if return_tool_format:
            results = []
            for service in services:
                trust_stats = trust_map.get(service.id)
                service = attach_trust_summary(service, trust_stats)
                org_name = service.organization.name if service.organization else "Unknown"
                tool = service_to_tool_format_safe(service, org_name)
                results.append(tool)
        else:
            results = []
            for service in services:
                trust_stats = trust_map.get(service.id)
                service = attach_trust_summary(service, trust_stats)
                org_name = service.organization.name if service.organization else "Unknown"
                service_dict = service_to_client_format(service, org_name)
                results.append(service_dict)
        
        logger.info(f"返回 {len(results)} 个热门服务")
        return results
        
    except Exception as e:
        logger.error(f"获取热门服务失败: {e}")
        raise HTTPException(500, f"获取热门服务失败: {str(e)}")


@router.get("/categories")
async def get_service_categories(
    db: Session = Depends(get_db)
):
    """获取服务类别（无需认证）"""
    try:
        # 查询公开服务的类别
        categories = db.query(Service.category).filter(
            Service.is_active == True,
            Service.is_public == True,
            Service.category.isnot(None)
        ).distinct().all()
        
        # 提取类别名称
        category_list = [cat[0] for cat in categories if cat[0]]
        category_list.sort()
        
        logger.info(f"返回 {len(category_list)} 个类别")
        return category_list
        
    except Exception as e:
        logger.error(f"获取类别失败: {e}")
        raise HTTPException(500, f"获取类别失败: {str(e)}")


@router.get("/organizations")
async def get_service_organizations(
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """获取提供公开服务的组织"""
    try:
        # 查询提供公开服务的组织
        organizations = db.query(Organization).join(Service).filter(
            Service.is_active == True,
            Service.is_public == True
        ).distinct().all()
        
        org_list = [{"id": org.id, "name": org.name} for org in organizations]
        org_list.sort(key=lambda x: x["name"])
        
        logger.info(f"返回 {len(org_list)} 个组织")
        return org_list
        
    except Exception as e:
        logger.error(f"获取组织失败: {e}")
        raise HTTPException(500, f"获取组织失败: {str(e)}")


@router.get("/protocols")
async def get_supported_protocols(
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """获取支持的协议"""
    try:
        # 查询所有公开服务支持的协议
        protocols = db.query(Service.protocol).filter(
            Service.is_active == True,
            Service.is_public == True,
            Service.protocol.isnot(None)
        ).distinct().all()
        
        protocol_list = [proto[0] for proto in protocols if proto[0]]
        protocol_list.sort()
        
        logger.info(f"返回 {len(protocol_list)} 个协议")
        return protocol_list
        
    except Exception as e:
        logger.error(f"获取协议失败: {e}")
        raise HTTPException(500, f"获取协议失败: {str(e)}")


@router.get("/featured")
async def get_featured_services(
    limit: int = Query(6, ge=1, le=20),
    return_tool_format: bool = Query(True),
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """获取推荐服务"""
    logger.info(f"客户端用户 {current_user.id} 获取推荐服务")

    try:
        services = db.query(Service).filter(
            Service.is_active == True,
            Service.is_public == True,
            Service.tags.isnot(None)
        ).options(joinedload(Service.organization)).limit(limit).all()

        service_ids = [service.id for service in services]
        trust_map = {}

        if service_ids:
            trust_stats_list = db.query(ServiceTrustStats).filter(
                ServiceTrustStats.service_id.in_(service_ids)
            ).all()
            trust_map = {item.service_id: item for item in trust_stats_list}

        if return_tool_format:
            results = []
            for service in services:
                trust_stats = trust_map.get(service.id)
                service = attach_trust_summary(service, trust_stats)
                org_name = service.organization.name if service.organization else "Unknown"
                tool = service_to_tool_format_safe(service, org_name)
                results.append(tool)
        else:
            results = []
            for service in services:
                trust_stats = trust_map.get(service.id)
                service = attach_trust_summary(service, trust_stats)
                org_name = service.organization.name if service.organization else "Unknown"
                service_dict = service_to_client_format(service, org_name)
                results.append(service_dict)
        
        logger.info(f"返回 {len(results)} 个推荐服务")
        return results
        
    except Exception as e:
        logger.error(f"获取推荐服务失败: {e}")
        raise HTTPException(500, f"获取推荐服务失败: {str(e)}")


@router.get("/stats")
async def get_discovery_stats(
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """获取发现统计信息"""
    try:
        # 统计公开服务数量
        total_services = db.query(Service).filter(
            Service.is_active == True,
            Service.is_public == True
        ).count()
        
        # 统计类别数量
        category_count = db.query(Service.category).filter(
            Service.is_active == True,
            Service.is_public == True,
            Service.category.isnot(None)
        ).distinct().count()
        
        # 统计组织数量
        org_count = db.query(Organization).join(Service).filter(
            Service.is_active == True,
            Service.is_public == True
        ).distinct().count()
        
        return {
            "total_services": total_services,
            "total_categories": category_count,
            "total_organizations": org_count
        }
        
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(500, f"获取统计信息失败: {str(e)}")
