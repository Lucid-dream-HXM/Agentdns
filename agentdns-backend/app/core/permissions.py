"""
权限控制 - 区分管理员和客户端权限
该模块定义了用户角色和权限检查逻辑，确保不同类型的用户只能访问其被授权的资源
"""

from enum import Enum  # 枚举类型，用于定义用户角色
from typing import List, Optional  # 类型提示，用于指定列表和可选类型
from fastapi import HTTPException, status  # FastAPI异常处理
from sqlalchemy.orm import Session  # SQLAlchemy数据库会话类型

from ..models.user import User  # 用户模型
from ..models.service import Service  # 服务模型
from ..models.organization import Organization  # 组织模型


class UserRole(str, Enum):
    """用户角色枚举 - 定义系统中的不同用户角色"""
    ADMIN = "admin"                    # 系统管理员
    CLIENT = "client"                  # 客户端用户
    ORGANIZATION_OWNER = "org_owner"   # 组织所有者


class PermissionChecker:
    """权限检查器 - 提供各种权限验证方法"""
    
    @staticmethod
    def check_admin_access(user: User) -> None:
        """
        检查管理员权限
        验证用户是否具有管理员权限
        
        Args:
            user: 当前用户对象
        
        Raises:
            HTTPException: 如果用户不是管理员
        """
        if not user or user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="需要管理员权限"
            )
    
    @staticmethod
    def check_client_access(user: User) -> None:
        """
        检查客户端访问权限
        验证用户是否具有客户端访问权限
        
        Args:
            user: 当前用户对象
        
        Raises:
            HTTPException: 如果用户权限不足
        """
        if not user or user.role not in ["client", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足"
            )
    
    @staticmethod
    def check_service_access(user: User, service: Service, db: Session) -> None:
        """
        检查服务访问权限
        验证用户是否有权访问特定服务
        
        Args:
            user: 当前用户对象
            service: 要访问的服务对象
            db: 数据库会话
        
        Raises:
            HTTPException: 如果用户无权访问服务
        """
        # 管理员可以访问所有服务
        if user.role == "admin":
            return
            
        # 公开服务对所有人可访问
        if service.is_public:
            return
            
        # 私有服务仅对组织成员可访问
        if service.organization_id:
            organization = db.query(Organization).filter(
                Organization.id == service.organization_id  # 按组织ID筛选
            ).first()
            
            # 如果组织存在且用户是组织所有者，则可以访问
            if organization and organization.owner_id == user.id:
                return
                
        # 无权访问此服务
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此服务"
        )
    
    @staticmethod
    def filter_services_by_permission(services: List[Service], user: User) -> List[Service]:
        """
        按权限筛选服务
        根据用户权限过滤服务列表
        
        Args:
            services: 服务列表
            user: 当前用户对象
        
        Returns:
            根据用户权限过滤后的服务列表
        """
        if user.role == "admin":
            # 管理员可以看到所有服务
            return services
            
        # 客户端用户只能看到公开服务
        return [s for s in services if s.is_public]
    
    @staticmethod
    def can_manage_service(user: User, service: Service, db: Session) -> bool:
        """
        检查用户是否可以管理服务
        判断用户是否有权管理特定服务
        
        Args:
            user: 当前用户对象
            service: 要管理的服务对象
            db: 数据库会话
        
        Returns:
            如果用户可以管理服务返回True，否则返回False
        """
        # 管理员可以管理所有服务
        if user.role == "admin":
            return True
            
        # 组织所有者可以管理其组织的服务
        if service.organization_id:
            organization = db.query(Organization).filter(
                Organization.id == service.organization_id  # 按组织ID筛选
            ).first()
            # 返回组织是否存在且用户是组织所有者的结果
            return organization and organization.owner_id == user.id
            
        return False


def attach_trust_summary(service: Service, trust_stats=None) -> Service:
    """
    将信任摘要字段附加到Service对象上（动态属性）
    """
    if trust_stats:
        service.trust_score = trust_stats.trust_score
        service.success_rate = trust_stats.success_rate
        service.rating_count = trust_stats.rating_count
        service.avg_response_time_ms = trust_stats.avg_response_time_ms
    else:
        service.trust_score = None
        service.success_rate = None
        service.rating_count = None
        service.avg_response_time_ms = None

    return service


def service_to_client_format(service: Service, organization_name: str = None) -> dict:
    """
    将服务转换为客户端安全的字典格式（不含敏感字段）
    生成适合客户端显示的服务信息，排除敏感字段
    
    Args:
        service: 服务对象
        organization_name: 组织名称（可选）
    
    Returns:
        客户端安全的服务信息字典
    """
    return {
        "id": service.id,  # 服务ID
        "name": service.name,  # 服务名称
        "category": service.category,  # 服务类别
        "agentdns_uri": service.agentdns_uri,  # AgentDNS URI
        "agentdns_path": service.agentdns_path,  # AgentDNS路径
        "description": service.description,  # 服务描述
        "version": service.version,  # 服务版本
        "is_active": service.is_active,  # 服务是否激活
        "is_public": service.is_public,  # 服务是否公开
        "protocol": service.protocol,  # 协议类型
        "http_method": service.http_method,  # HTTP方法
        "http_mode": service.http_mode,  # HTTP模式
        "input_description": service.input_description,  # 输入描述
        "output_description": service.output_description,  # 输出描述
        "authentication_required": service.authentication_required,  # 是否需要认证
        "pricing_model": service.pricing_model,  # 定价模型
        "price_per_unit": service.price_per_unit,  # 单位价格
        "currency": service.currency,  # 货币单位
        "tags": service.tags or [],  # 服务标签
        "capabilities": service.capabilities or {}, # 服务能力
        "organization_name": organization_name,  # 组织名称
        "created_at": service.created_at,  # 创建时间
        "updated_at": service.updated_at,  # 更新时间
        "trust_score": getattr(service, "trust_score", None),
        "success_rate": getattr(service, "success_rate", None),
        "rating_count": getattr(service, "rating_count", None),
        "avg_response_time_ms": getattr(service, "avg_response_time_ms", None),
        # 注意：排除敏感字段
        # - endpoint_url (端点URL)
        # - service_api_key (服务API密钥)
        # - organization_id (组织ID)
    }


def service_to_tool_format_safe(service: Service, organization_name: str = None) -> dict:
    """
    将服务转换为客户端安全的工具格式
    生成符合SDK规范的安全工具格式服务信息
    
    Args:
        service: 服务对象
        organization_name: 组织名称（可选）
    
    Returns:
        客户端安全的工具格式服务信息字典
    """
    # 成本描述映射
    cost_description_map = {
        "per_request": "按请求计费",  # 每次请求计费
        "per_token": "按令牌计费",  # 每个令牌计费
        "per_mb": "按MB传输计费",  # 每MB传输数据计费
        "monthly": "按月计费",  # 每月计费
        "yearly": "按年计费"  # 每年计费
    }
    
    pricing_model = service.pricing_model or "per_request"  # 使用默认定价模型
    
    return {
        "name": service.name or "",  # 服务名称
        "description": service.description or "",  # 服务描述
        "organization": organization_name or "Unknown",  # 组织名称
        "agentdns_url": service.agentdns_uri or "",  # AgentDNS URL
        "cost": {  # 成本信息
            "type": pricing_model,  # 成本类型
            "price": str(service.price_per_unit or 0.0),  # 价格
            "currency": service.currency or "CNY",  # 货币单位
            "description": cost_description_map.get(pricing_model, "按请求计费")  # 成本描述
        },
        "protocol": service.protocol or "HTTP",  # 协议类型
        "method": service.http_method or "POST",  # HTTP方法
        "http_mode": service.http_mode,  # HTTP模式
        "input_description": service.input_description or "{}",  # 输入描述
        "output_description": service.output_description or "{}",
        "trust_score": getattr(service, "trust_score", None),
        "success_rate": getattr(service, "success_rate", None),
        "rating_count": getattr(service, "rating_count", None),
        "avg_response_time_ms": getattr(service, "avg_response_time_ms", None),
    }
