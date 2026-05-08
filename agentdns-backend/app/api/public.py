"""
公开API - 不需要认证的端点
提供公开的服务信息、类别、协议和统计数据
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import logging

from ..database import get_db
from ..models.service import Service
from ..models.organization import Organization
from ..core.permissions import service_to_tool_format_safe, service_to_client_format

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/trending")
async def get_public_trending_services(
    limit: int = Query(10, ge=1, le=50),
    return_tool_format: bool = Query(True),
    db: Session = Depends(get_db)
):
    """
    获取热门服务 - 公开端点，无需认证
    
    返回公开且活跃的热门服务列表，支持返回Tool格式或客户端安全格式
    
    Args:
        limit: 返回服务数量限制，默认10，范围1-50
        return_tool_format: 是否返回Tool格式，默认True
        db: 数据库会话
    
    Returns:
        List[dict]: 服务列表
    """
    logger.info(f"获取公开热门服务, limit: {limit}")
    
    try:
        # 查询公开且活跃的服务，按创建时间排序（简单热门算法）
        services_query = db.query(Service).filter(
            Service.is_public == True,
            Service.is_active == True
        ).order_by(Service.created_at.desc()).limit(limit)
        
        services = services_query.all()
        
        if return_tool_format:
            # 转换为Tool格式
            result = []
            for service in services:
                # 获取组织名称
                organization_name = "Unknown"
                if service.organization_id:
                    organization = db.query(Organization).filter(
                        Organization.id == service.organization_id
                    ).first()
                    if organization:
                        organization_name = organization.name
                
                tool_data = service_to_tool_format_safe(service, organization_name)
                result.append(tool_data)
            
            return result
        else:
            # 转换为客户端安全格式
            result = []
            for service in services:
                organization_name = "Unknown"
                if service.organization_id:
                    organization = db.query(Organization).filter(
                        Organization.id == service.organization_id
                    ).first()
                    if organization:
                        organization_name = organization.name
                
                client_data = service_to_client_format(service, organization_name)
                result.append(client_data)
            
            return result
            
    except Exception as e:
        logger.error(f"获取公开热门服务失败: {str(e)}")
        return []


@router.get("/categories")
async def get_public_service_categories(
    db: Session = Depends(get_db)
):
    """
    获取服务类别 - 公开端点
    
    返回所有公开且活跃的服务类别列表
    
    Args:
        db: 数据库会话
    
    Returns:
        List[str]: 服务类别列表
    """
    logger.info("获取公开服务类别")
    
    try:
        # 从公开服务中查询类别
        categories = db.query(Service.category).filter(
            Service.is_public == True,
            Service.is_active == True,
            Service.category.isnot(None)
        ).distinct().all()
        
        # 提取类别名称并过滤空值
        category_list = [cat[0] for cat in categories if cat[0]]
        
        return sorted(category_list)
        
    except Exception as e:
        logger.error(f"获取公开服务类别失败: {str(e)}")
        return []


@router.get("/protocols")
async def get_public_service_protocols(
    db: Session = Depends(get_db)
):
    """
    获取服务协议 - 公开端点
    
    返回所有公开且活跃的服务协议列表
    
    Args:
        db: 数据库会话
    
    Returns:
        List[str]: 服务协议列表
    """
    logger.info("获取公开服务协议")
    
    try:
        # 从公开服务中查询协议
        protocols = db.query(Service.protocol).filter(
            Service.is_public == True,
            Service.is_active == True,
            Service.protocol.isnot(None)
        ).distinct().all()
        
        # 提取协议名称并过滤空值
        protocol_list = [proto[0] for proto in protocols if proto[0]]
        
        return sorted(protocol_list)
        
    except Exception as e:
        logger.error(f"获取公开服务协议失败: {str(e)}")
        return []


@router.get("/stats")
async def get_public_stats(
    db: Session = Depends(get_db)
):
    """
    获取公开统计信息
    
    返回系统的公开统计信息，包括服务数量、类别数量和协议数量
    
    Args:
        db: 数据库会话
    
    Returns:
        dict: 统计信息
    """
    logger.info("获取公开统计信息")
    
    try:
        # 统计公开服务数量
        total_services = db.query(Service).filter(
            Service.is_public == True,
            Service.is_active == True
        ).count()
        
        # 统计类别数量
        categories_count = db.query(Service.category).filter(
            Service.is_public == True,
            Service.is_active == True,
            Service.category.isnot(None)
        ).distinct().count()
        
        # 统计协议数量
        protocols_count = db.query(Service.protocol).filter(
            Service.is_public == True,
            Service.is_active == True,
            Service.protocol.isnot(None)
        ).distinct().count()
        
        return {
            "total_services": total_services,
            "categories_count": categories_count,
            "protocols_count": protocols_count
        }
        
    except Exception as e:
        logger.error(f"获取公开统计信息失败: {str(e)}")
        return {
            "total_services": 0,
            "categories_count": 0,
            "protocols_count": 0
        }