"""
服务发现API - 用于服务发现和解析
提供自然语言服务搜索、AgentDNS URI解析、服务类别查询等功能
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query  # FastAPI核心组件，用于创建路由和处理请求
from sqlalchemy.orm import Session, joinedload  # SQLAlchemy ORM组件，用于数据库操作
from typing import List, Optional  # 类型提示，用于指定列表和可选类型
import re  # 正则表达式库，用于模式匹配
import json  # JSON处理库，用于序列化和反序列化JSON数据

from ..database import get_db, get_redis
from ..core.config import settings  # 数据库和Redis连接函数
from ..models.user import User
from ..models.service import Service, ServiceMetadata
from ..models.organization import Organization
from ..models.review import ServiceTrustStats
from ..schemas.service import (
    ServiceSearch, ServiceDiscovery, Service as ServiceSchema,
    ToolsListResponse, Tool, ToolCost
)
from .deps import get_current_active_user
from ..services.search_engine import SearchEngine, service_to_tool_format
from ..core.permissions import attach_trust_summary

# 创建服务发现API路由器
router = APIRouter()


@router.post("/search", response_model=ToolsListResponse)
def search_services(  # 套schemas里的规则
    search_data: ServiceSearch,  # 服务搜索请求数据
    current_user: User = Depends(get_current_active_user),  # 当前认证用户
    db: Session = Depends(get_db)  # 数据库会话
):
    """
    自然语言服务发现 - 按SDK规范返回工具列表
    
    通过自然语言查询发现可用服务，返回符合SDK规范的工具列表
    
    Args:
        search_data: 服务搜索请求数据，包含查询语句、类别、组织、协议等筛选条件
        current_user: 当前认证用户
        db: 数据库会话
    
    Returns:
        ToolsListResponse: 工具列表响应，包含工具列表、总结果数和查询语句
    """
    # 创建搜索引擎实例
    search_engine = SearchEngine(db)
    
    # 执行搜索，返回Tool格式的服务列表
    tools, total = search_engine.search(
        query=search_data.query,
        category=search_data.category,
        organization=search_data.organization,
        protocol=search_data.protocol,
        max_price=search_data.max_price,
        limit=search_data.limit,
        return_tool_format=True,
        sort_by=search_data.sort_by or "balanced",
        include_trust=search_data.include_trust if search_data.include_trust is not None else True,
        min_trust_score=search_data.min_trust_score
    )
    
    # 返回工具列表响应
    return ToolsListResponse(
        tools=tools,  # 工具列表
        total=total,  # 总结果数
        query=search_data.query  # 搜索查询语句
    )


@router.get("/resolve/{agentdns_uri:path}", response_model=Tool)
def resolve_service(
    agentdns_uri: str,  # AgentDNS URI路径参数
    current_user: User = Depends(get_current_active_user),  # 当前认证用户
    db: Session = Depends(get_db)  # 数据库会话
):
    """
    解析AgentDNS URI为工具格式
    
    将AgentDNS URI解析为对应的工具对象，用于直接访问特定服务
    
    Args:
        agentdns_uri: AgentDNS URI路径参数
        current_user: 当前认证用户
        db: 数据库会话
    
    Returns:
        Tool: 工具对象，包含服务的详细信息
    
    Raises:
        HTTPException: 当服务未找到或无访问权限时抛出
    """
    
    # 规范化URI - 如果不是以agentdns://开头，则添加前缀
    if not agentdns_uri.startswith("agentdns://"):
        agentdns_uri = f"agentdns://{agentdns_uri}"
    
    # 查找服务并预加载组织信息
    service = db.query(Service).options(
        joinedload(Service.organization)  # 预加载组织信息，避免N+1查询问题
    ).filter(
        Service.agentdns_uri == agentdns_uri,  # 匹配AgentDNS URI
        Service.is_active == True  # 服务必须处于激活状态
    ).first()
    
    if not service:
        # 服务未找到或已禁用
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found or disabled"  # 服务未找到或已禁用
        )
    
    # 检查访问权限
    if not service.is_public:
        # 对于私有服务，检查用户是否为组织所有者
        organization = service.organization
        if organization and organization.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to access"  # 无访问权限
            )

    trust_stats = db.query(ServiceTrustStats).filter(
        ServiceTrustStats.service_id == service.id
    ).first()

    service = attach_trust_summary(service, trust_stats)

    # 转换为工具格式
    tool_data = service_to_tool_format(service)
    return Tool(**tool_data)


@router.get("/categories", response_model=List[str])
def get_categories(
    current_user: User = Depends(get_current_active_user),  # 当前认证用户
    db: Session = Depends(get_db)  # 数据库会话
):
    """
    获取可用的服务类别
    
    返回系统中所有活跃的公开服务类别列表
    
    Args:
        current_user: 当前认证用户
        db: 数据库会话
    
    Returns:
        List[str]: 服务类别列表
    """
    # 查询所有活跃的公开服务类别
    categories = db.query(Service.category).filter(
        Service.category.isnot(None),  # 类别不为空
        Service.is_active == True,  # 服务处于激活状态
        Service.is_public == True  # 服务为公开服务
    ).distinct().all()
    
    # 返回去重的类别列表
    return [cat[0] for cat in categories if cat[0]]


@router.get("/protocols", response_model=List[str])
def get_protocols(
    current_user: User = Depends(get_current_active_user),  # 当前认证用户
    db: Session = Depends(get_db)  # 数据库会话
):
    """
    获取支持的协议列表
    
    返回系统中所有活跃的公开服务所使用的协议列表
    
    Args:
        current_user: 当前认证用户
        db: 数据库会话
    
    Returns:
        List[str]: 协议列表
    """
    # 从所有活跃服务中提取协议
    protocols = db.query(Service.protocol).filter(
        Service.is_active == True,  # 服务处于激活状态
        Service.is_public == True,  # 服务为公开服务
        Service.protocol.isnot(None)  # 协议不为空
    ).distinct().all()
    
    # 返回排序后的协议列表
    return sorted([protocol[0] for protocol in protocols if protocol[0]])


@router.get("/trending", response_model=List[Tool])
def get_trending_services(
    limit: int = Query(10, ge=1, le=50),  # 限制参数，默认10，范围1-50
    current_user: User = Depends(get_current_active_user),  # 当前认证用户
    db: Session = Depends(get_db)  # 数据库会话
):
    """
    获取热门服务（工具格式）
    
    返回最近创建的活跃公开服务列表
    
    Args:
        limit: 限制返回的服务数量，默认10，范围1-50
        current_user: 当前认证用户
        db: 数据库会话
    
    Returns:
        List[Tool]: 工具列表
    """
    # 简单实现：按创建时间降序排列，仅包含活跃和公开服务
    services = db.query(Service).options(
        joinedload(Service.organization)
    ).filter(
        Service.is_active == True,
        Service.is_public == True
    ).order_by(Service.created_at.desc()).limit(limit).all()

    service_ids = [service.id for service in services]
    trust_map = {}

    if service_ids:
        trust_stats_list = db.query(ServiceTrustStats).filter(
            ServiceTrustStats.service_id.in_(service_ids)
        ).all()
        trust_map = {item.service_id: item for item in trust_stats_list}

    tools = []
    for service in services:
        trust_stats = trust_map.get(service.id)
        service = attach_trust_summary(service, trust_stats)
        tool_data = service_to_tool_format(service)
        tools.append(Tool(**tool_data))
    
    return tools


@router.get("/vector-stats")
def get_vector_search_stats(
    current_user: User = Depends(get_current_active_user),  # 当前认证用户
    db: Session = Depends(get_db)  # 数据库会话
):
    """
    获取向量搜索统计信息
    
    返回向量搜索系统的统计信息和配置详情
    
    Args:
        current_user: 当前认证用户
        db: 数据库会话
    
    Returns:
        dict: 包含向量搜索统计、数据库统计和嵌入配置的字典
    """
    # 创建搜索引擎实例
    search_engine = SearchEngine(db)
    # 获取向量搜索统计信息
    vector_stats = search_engine.get_vector_search_stats()
    
    # 添加数据库统计信息
    db_stats = {
        "total_services": db.query(Service).filter(
            Service.is_active == True  # 活跃服务总数
        ).count(),
        "public_services": db.query(Service).filter(
            Service.is_active == True,  # 活跃的公开服务数
            Service.is_public == True
        ).count(),
        "http_agent_services": db.query(Service).filter(
            Service.is_active == True,  # 活跃的HTTP代理服务数
            Service.is_public == True,
            Service.agentdns_path.isnot(None)
        ).count()
    }
    
    # 添加嵌入配置信息
    embedding_config = {
        "provider": "OpenAI",  # 嵌入服务提供商
        "model": settings.OPENAI_EMBEDDING_MODEL,  # 使用的嵌入模型
        "dimension": settings.MILVUS_DIMENSION,  # 向量维度
        "max_tokens": settings.OPENAI_MAX_TOKENS,  # 最大令牌数
        "api_key_configured": bool(settings.OPENAI_API_KEY)  # API密钥是否已配置
    }
    
    # 如果可能，添加成本估算示例
    try:
        # 创建嵌入服务实例
        embedding_service = EmbeddingService()
        # 示例文本
        sample_text = "This is a sample service for AI-powered text processing"
        # 估算成本
        cost_estimate = embedding_service.estimate_cost(sample_text)
        # 获取令牌数
        token_count = embedding_service.get_token_count(sample_text)
        
        embedding_config.update({
            "cost_per_embedding_example": {
                "text": sample_text,  # 示例文本
                "tokens": token_count,  # 令牌数
                "estimated_cost_usd": round(cost_estimate, 6)  # 估算成本（美元）
            }
        })
    except Exception as e:
        # 如果初始化嵌入服务失败，记录错误
        embedding_config["error"] = f"Failed to initialize embedding service: {str(e)}"  # 初始化嵌入服务失败
    
    # 返回综合统计信息
    return {
        "vector_search": vector_stats,  # 向量搜索统计
        "database": db_stats,  # 数据库统计
        "embedding_config": embedding_config  # 嵌入配置
    }