"""
服务API - 用于管理服务的创建、查询、更新和删除
提供服务的完整生命周期管理功能
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging
from cryptography.fernet import Fernet
import base64
import os

from ..database import get_db
from ..models.user import User
from ..models.organization import Organization
from ..models.service import Service, ServiceMetadata
from ..models.review import ServiceTrustStats
from ..schemas.service import (
    ServiceCreate,
    ServiceUpdate,
    Service as ServiceSchema
)
from .deps import get_current_active_user
from ..services.embedding_service import EmbeddingService
from ..services.milvus_service import get_milvus_service
from ..core.config import settings
from ..core.permissions import attach_trust_summary

router = APIRouter()
logger = logging.getLogger(__name__)

# Encryption key (from settings)
ENCRYPTION_KEY = settings.ENCRYPTION_KEY
if not ENCRYPTION_KEY:
    ENCRYPTION_KEY = Fernet.generate_key()
    logger.warning("ENCRYPTION_KEY not set, using a temporary key (will reset on restart)")
elif isinstance(ENCRYPTION_KEY, str):
    # 如果是字符串，将其编码为bytes
    if len(ENCRYPTION_KEY) != 44:  # 标准Fernet密钥长度
        # 如果不是标准格式，则生成新密钥
        logger.warning("Invalid ENCRYPTION_KEY format, generating new key")
        ENCRYPTION_KEY = Fernet.generate_key()
    else:
        ENCRYPTION_KEY = ENCRYPTION_KEY.encode()
        
# 确保密钥是有效的Fernet密钥
try:
    cipher_suite = Fernet(ENCRYPTION_KEY)
except ValueError:
    logger.warning("Invalid ENCRYPTION_KEY, generating new key")
    ENCRYPTION_KEY = Fernet.generate_key()
    cipher_suite = Fernet(ENCRYPTION_KEY)


def encrypt_api_key(api_key: str) -> str:
    """
    加密API密钥
    
    使用Fernet对称加密算法加密API密钥
    
    Args:
        api_key: 原始API密钥
    
    Returns:
        str: 加密后的API密钥
    """
    if not api_key:
        return ""
    return base64.urlsafe_b64encode(cipher_suite.encrypt(api_key.encode())).decode()


def decrypt_api_key(encrypted_key: str) -> str:
    """
    解密API密钥
    
    使用Fernet对称加密算法解密API密钥
    
    Args:
        encrypted_key: 加密后的API密钥
    
    Returns:
        str: 解密后的API密钥
    """
    if not encrypted_key:
        return ""
    try:
        return cipher_suite.decrypt(base64.urlsafe_b64decode(encrypted_key.encode())).decode()
    except:
        return ""


def generate_agentdns_uri(org_name: str, category: str, service_name: str, agentdns_path: str = None) -> str:
    """
    生成AgentDNS URI
    
    根据组织名称、类别、服务名称或自定义路径生成AgentDNS URI
    
    Args:
        org_name: 组织名称
        category: 服务类别
        service_name: 服务名称
        agentdns_path: 自定义AgentDNS路径（可选）
    
    Returns:
        str: 生成的AgentDNS URI
    """
    # 如果提供了自定义路径，使用自定义路径
    # 否则使用默认/传统格式
    if agentdns_path:
        # 如果提供了自定义路径，使用自定义路径
        return f"agentdns://{agentdns_path}"
    else:
        # 默认/传统格式
        return f"agentdns://{org_name}/{category}/{service_name}"


def service_to_public_dict(service: Service, include_sensitive: bool = False) -> dict:
    """
    将服务模型转换为字典，可选包含敏感字段
    
    将Service模型转换为字典格式，根据需要决定是否包含敏感字段
    
    Args:
        service: 服务模型
        include_sensitive: 是否包含敏感字段（如API密钥）
    
    Returns:
        dict: 服务字典
    """
    # 转换服务模型为字典格式
    # 可选是否包含敏感字段（如API密钥）
    service_dict = {
        "id": service.id,
        "name": service.name,
        "category": service.category,
        "agentdns_uri": service.agentdns_uri,
        "description": service.description,
        "version": service.version,
        "is_active": service.is_active,
        "is_public": service.is_public,
        "protocol": service.protocol,  # 单个协议字段
        "authentication_required": service.authentication_required,
        "pricing_model": service.pricing_model,
        "price_per_unit": service.price_per_unit,
        "currency": service.currency,
        "tags": service.tags or [],
        "capabilities": service.capabilities or {},
        "organization_id": service.organization_id,
        "created_at": service.created_at,
        "updated_at": service.updated_at,
        
        # HTTP代理服务特定字段
        "agentdns_path": service.agentdns_path,
        "http_method": service.http_method,
        "http_mode": service.http_mode,  # HTTP模式
        "input_description": service.input_description,
        "output_description": service.output_description,
    }
    
    # 如果请求包含敏感信息
    if include_sensitive:
        service_dict["endpoint_url"] = service.endpoint_url
        # 解密API密钥
        if service.service_api_key:
            service_dict["service_api_key"] = decrypt_api_key(service.service_api_key)
        else:
            service_dict["service_api_key"] = None

    # 第一阶段新增：服务信任摘要字段
    service_dict["trust_score"] = getattr(service, "trust_score", None)
    service_dict["success_rate"] = getattr(service, "success_rate", None)
    service_dict["rating_count"] = getattr(service, "rating_count", None)
    service_dict["avg_response_time_ms"] = getattr(service, "avg_response_time_ms", None)

    return service_dict


@router.post("/", response_model=ServiceSchema)
def create_service(
    service_data: ServiceCreate,
    organization_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    创建新服务
    
    创建一个新的服务，包括验证组织所有权、生成AgentDNS URI、加密API密钥等步骤
    
    Args:
        service_data: 服务创建数据
        organization_id: 组织ID
        current_user: 当前活跃用户
        db: 数据库会话
    
    Returns:
        ServiceSchema: 创建的服务信息
    
    Raises:
        HTTPException: 当组织不存在、无权限或AgentDNS URI/路径已存在时抛出
    """
    # 验证组织所有权
    organization = db.query(Organization).filter(
        Organization.id == organization_id,
        Organization.owner_id == current_user.id
    ).first()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="组织不存在或无权限"
        )
    
    # 生成AgentDNS URI
    agentdns_uri = generate_agentdns_uri(
        organization.name, 
        service_data.category or "general", 
        service_data.name,
        service_data.agentdns_path
    )
    
    # 检查AgentDNS URI唯一性
    if db.query(Service).filter(Service.agentdns_uri == agentdns_uri).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="AgentDNS URI已存在，请使用不同的服务名称或路径"
        )
    
    # 检查自定义agentdns_path唯一性
    if service_data.agentdns_path:
        if db.query(Service).filter(Service.agentdns_path == service_data.agentdns_path).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
            detail="AgentDNS路径已存在，请使用不同的路径"
            )
    
    # 加密API密钥
    encrypted_api_key = encrypt_api_key(service_data.service_api_key) if service_data.service_api_key else None
    
    # 创建服务
    db_service = Service(
        name=service_data.name,
        category=service_data.category,
        agentdns_uri=agentdns_uri,
        description=service_data.description,
        version=service_data.version,
        is_public=service_data.is_public,
        endpoint_url=service_data.endpoint_url,
        protocol=service_data.protocol,  # 单个协议字段
        authentication_required=service_data.authentication_required,
        pricing_model=service_data.pricing_model,
        price_per_unit=service_data.price_per_unit,
        currency=service_data.currency,
        tags=service_data.tags or [],
        capabilities=service_data.capabilities or {},
        organization_id=organization.id,
        
        # HTTP代理服务特定字段
        agentdns_path=service_data.agentdns_path,
        http_method=service_data.http_method,
        http_mode=service_data.http_mode,  # HTTP模式
        input_description=service_data.input_description,
        output_description=service_data.output_description,
        service_api_key=encrypted_api_key
    )
    
    db.add(db_service)
    db.commit()
    db.refresh(db_service)
    
    # 创建服务元数据
    metadata = ServiceMetadata(
        service_id=db_service.id,
        search_keywords=service_data.tags or [],
        status="active"
    )
    db.add(metadata)
    db.commit()

    trust_stats = ServiceTrustStats(
        service_id=db_service.id,
        trust_score=0.0,
        objective_score=0.0,
        subjective_score=0.0,
        success_rate=0.0,
        avg_response_time_ms=0.0,
        rating_count=0,
        usage_count=0
    )
    db.add(trust_stats)
    db.commit()

    # 生成并存储向量到Milvus（仅当描述存在时）
    if db_service.description:
        try:
            embedding_service = EmbeddingService()
            milvus_service = get_milvus_service()
            
            # 准备嵌入数据
            vector_data = {
                'name': db_service.name,
                'category': db_service.category,
                'description': db_service.description,
                'tags': db_service.tags,
                'protocol': db_service.protocol,  # 单个协议字段
                'http_mode': db_service.http_mode,  # HTTP模式
                'capabilities': db_service.capabilities,
                'organization_name': organization.name
            }
            
            # 创建嵌入
            embedding = embedding_service.create_service_embedding(vector_data)
            
            # 存储到Milvus
            success = milvus_service.insert_service_vector(
                service_id=db_service.id,
                embedding=embedding,
                service_name=db_service.name,
                category=db_service.category or "",
                organization_id=organization.id
            )
            
            if success:
                logger.info(f"成功存储服务 {db_service.id} 的向量")
            else:
                logger.warning(f"存储服务 {db_service.id} 的向量失败")
                
        except Exception as e:
            logger.error(f"为服务 {db_service.id} 创建向量时出错: {e}")
            # 不抛出异常；服务创建成功，向量化不应阻塞
    
    # 返回公开服务信息
    return ServiceSchema.parse_obj(service_to_public_dict(db_service))


@router.get("/", response_model=List[ServiceSchema])
def list_services(
    organization_id: int = None,
    category: str = None,
    is_public: bool = True,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """
    列出服务
    
    列出活跃的服务，支持按组织、类别、是否公开筛选
    
    Args:
        organization_id: 组织ID（可选）
        category: 服务类别（可选）
        is_public: 是否公开（默认True）
        current_user: 当前活跃用户
        db: 数据库会话
        skip: 跳过的记录数（用于分页）
        limit: 返回的最大记录数（用于分页）
    
    Returns:
        List[ServiceSchema]: 服务列表
    """
    # 筛选活跃的服务
    # 可选按组织、类别、是否公开筛选
    # 当列出私有服务时，确保用户有权限
    # 转换为字典；如果用户是所有者，包含敏感字段
    query = db.query(Service).filter(Service.is_active == True)
    
    if organization_id:
        query = query.filter(Service.organization_id == organization_id)
    
    if category:
        query = query.filter(Service.category == category)
    
    if is_public is not None:
        query = query.filter(Service.is_public == is_public)
    
    # When listing private services, ensure user has permission
    if not is_public:
        user_org_ids = [org.id for org in db.query(Organization).filter(
            Organization.owner_id == current_user.id
        ).all()]
        query = query.filter(Service.organization_id.in_(user_org_ids))
    
    services = query.offset(skip).limit(limit).all()
    
    # Get org IDs owned by user
    user_org_ids = [org.id for org in db.query(Organization).filter(
        Organization.owner_id == current_user.id
    ).all()]
    
    # Convert to dict; include sensitive fields if owned by the user
    public_services = []
    for service in services:
        include_sensitive = service.organization_id in user_org_ids
        public_services.append(ServiceSchema.parse_obj(service_to_public_dict(service, include_sensitive=include_sensitive)))
    
    return public_services


@router.get("/{service_id}", response_model=ServiceSchema)
def get_service(
    service_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取服务详情
    
    根据服务ID获取服务详细信息
    
    Args:
        service_id: 服务ID
        current_user: 当前活跃用户
        db: 数据库会话
    
    Returns:
        ServiceSchema: 服务详细信息
    
    Raises:
        HTTPException: 当服务未找到或无访问权限时抛出
    """
    # 查找服务
    # 检查用户是否是所有者
    # 检查访问权限
    # 如果是所有者，包含敏感信息；否则返回公开信息
    service = db.query(Service).filter(Service.id == service_id).first()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="服务未找到"
        )
    
    # 检查当前用户是否是所有者
    organization = db.query(Organization).filter(
        Organization.id == service.organization_id
    ).first()
    is_owner = organization.owner_id == current_user.id

    # 检查访问权限
    if not service.is_public and not is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
                detail="无访问权限"
        )

    trust_stats = db.query(ServiceTrustStats).filter(
        ServiceTrustStats.service_id == service.id
    ).first()

    service = attach_trust_summary(service, trust_stats)

    # 如果是所有者，包含敏感信息；否则返回公开信息
    return ServiceSchema.parse_obj(service_to_public_dict(service, include_sensitive=is_owner))


@router.put("/{service_id}", response_model=ServiceSchema)
def update_service(
    service_id: int,
    service_data: ServiceUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    更新服务
    
    更新服务信息，包括检查权限、加密API密钥、更新Milvus向量等步骤
    
    Args:
        service_id: 服务ID
        service_data: 服务更新数据
        current_user: 当前活跃用户
        db: 数据库会话
    
    Returns:
        ServiceSchema: 更新后的服务信息
    
    Raises:
        HTTPException: 当服务未找到或无权限时抛出
    """
    # 查找服务
    # 检查权限
    # 应用更新
    # 加密API密钥（如果提供）
    # 更新Milvus中的向量（仅当描述存在时）
    # 查找服务
    service = db.query(Service).filter(Service.id == service_id).first()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="服务未找到"
        )
    
    # 检查权限
    organization = db.query(Organization).filter(
        Organization.id == service.organization_id
    ).first()
    
    if organization.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限修改此服务"
        )
    
    # 应用更新
    update_data = service_data.dict(exclude_unset=True)
    
    # 加密API密钥（如果提供）
    if 'service_api_key' in update_data:
        if update_data['service_api_key']:
            update_data['service_api_key'] = encrypt_api_key(update_data['service_api_key'])
        else:
            update_data['service_api_key'] = None
    
    for field, value in update_data.items():
        setattr(service, field, value)
    
    db.commit()
    db.refresh(service)
    
    # 更新Milvus中的向量（仅当描述存在时）
    if service.description:
        try:
            embedding_service = EmbeddingService()
            milvus_service = get_milvus_service()
            
            # 准备嵌入数据
            vector_data = {
                'name': service.name,
                'category': service.category,
                'description': service.description,
                'tags': service.tags,
                'protocol': service.protocol,  # 单个协议字段
                'http_mode': service.http_mode,  # HTTP模式
                'capabilities': service.capabilities,
                'organization_name': organization.name
            }
            
            # 创建新的嵌入
            embedding = embedding_service.create_service_embedding(vector_data)
            
            # 更新Milvus中的向量
            success = milvus_service.update_service_vector(
                service_id=service.id,
                embedding=embedding,
                service_name=service.name,
                category=service.category or "",
                organization_id=organization.id
            )
            
            if success:
                logger.info(f"成功更新服务 {service.id} 的向量")
            else:
                logger.warning(f"更新服务 {service.id} 的向量失败")
                
        except Exception as e:
            logger.error(f"更新服务 {service.id} 的向量时出错: {e}")
    
    # 返回公开服务信息
    return ServiceSchema.parse_obj(service_to_public_dict(service))


@router.delete("/{service_id}")
def delete_service(
    service_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    删除服务
    
    删除服务（软删除），包括检查权限、从Milvus删除向量等步骤
    
    Args:
        service_id: 服务ID
        current_user: 当前活跃用户
        db: 数据库会话
    
    Returns:
        dict: 删除结果
    
    Raises:
        HTTPException: 当服务未找到或无权限时抛出
    """
    # 查找服务
    # 检查权限
    # 从Milvus删除向量
    # 软删除服务
    # 查找服务
    service = db.query(Service).filter(Service.id == service_id).first()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="服务未找到"
        )
    
    # 检查权限
    organization = db.query(Organization).filter(
        Organization.id == service.organization_id
    ).first()
    
    if organization.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限删除此服务"
        )
    
    # 从Milvus删除向量
    try:
        milvus_service = get_milvus_service()
        success = milvus_service.delete_service_vector(service.id)
        
        if success:
            logger.info(f"成功删除服务 {service.id} 的向量")
        else:
            logger.warning(f"删除服务 {service.id} 的向量失败")
            
    except Exception as e:
        logger.error(f"删除服务 {service.id} 的向量时出错: {e}")
    
    # 软删除服务
    service.is_active = False
    db.commit()
    
    return {"message": "服务已删除"}