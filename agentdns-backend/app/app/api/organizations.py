"""
组织API - 用于管理用户的组织
提供组织的创建、查询、更新和删除功能
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models.user import User
from ..models.organization import Organization
from ..schemas.organization import (
    OrganizationCreate,
    OrganizationUpdate,
    Organization as OrganizationSchema
)
from .deps import get_current_active_user

router = APIRouter()


@router.post("/", response_model=OrganizationSchema)
def create_organization(
    org_data: OrganizationCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    创建组织
    
    创建一个新的组织，当前用户将成为组织的拥有者
    
    Args:
        org_data: 组织创建数据，包含名称、域名、显示名称等
        current_user: 当前活跃用户
        db: 数据库会话
    
    Returns:
        OrganizationSchema: 创建的组织信息
    
    Raises:
        HTTPException: 当组织名称或域名已存在时抛出
    """
    # 检查名称是否存在
    if db.query(Organization).filter(Organization.name == org_data.name).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="组织名称已存在"
        )
    
    # 检查域名是否存在
    if org_data.domain and db.query(Organization).filter(Organization.domain == org_data.domain).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="域名已被其他组织使用"
        )
    
    # 创建组织
    db_org = Organization(
        name=org_data.name,
        domain=org_data.domain,
        display_name=org_data.display_name,
        description=org_data.description,
        website=org_data.website,
        logo_url=org_data.logo_url,
        owner_id=current_user.id
    )
    
    db.add(db_org)
    db.commit()
    db.refresh(db_org)
    
    return db_org


@router.get("/", response_model=List[OrganizationSchema])
def list_organizations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """
    列出组织
    
    返回用户拥有的组织和公开验证的组织
    
    Args:
        current_user: 当前活跃用户
        db: 数据库会话
        skip: 跳过的记录数（用于分页）
        limit: 返回的最大记录数（用于分页）
    
    Returns:
        List[OrganizationSchema]: 组织列表
    """
    # 返回用户的组织和公开验证的组织
    user_orgs = db.query(Organization).filter(
        Organization.owner_id == current_user.id
    )
    
    public_orgs = db.query(Organization).filter(
        Organization.is_verified == True
    )
    
    # 合并结果
    all_orgs = user_orgs.union(public_orgs).offset(skip).limit(limit).all()
    
    return all_orgs


@router.get("/my", response_model=List[OrganizationSchema])
def get_my_organizations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取用户的组织
    
    返回当前用户拥有的所有组织
    
    Args:
        current_user: 当前活跃用户
        db: 数据库会话
    
    Returns:
        List[OrganizationSchema]: 用户拥有的组织列表
    """
    organizations = db.query(Organization).filter(
        Organization.owner_id == current_user.id
    ).all()
    
    return organizations


@router.get("/{organization_id}", response_model=OrganizationSchema)
def get_organization(
    organization_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取组织详情
    
    根据组织ID获取组织详细信息
    
    Args:
        organization_id: 组织ID
        current_user: 当前活跃用户
        db: 数据库会话
    
    Returns:
        OrganizationSchema: 组织详细信息
    
    Raises:
        HTTPException: 当组织未找到或无访问权限时抛出
    """
    organization = db.query(Organization).filter(
        Organization.id == organization_id
    ).first()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="组织未找到"
        )
    
    # 检查访问权限
    if not organization.is_verified and organization.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无访问权限"
        )
    
    return organization


@router.put("/{organization_id}", response_model=OrganizationSchema)
def update_organization(
    organization_id: int,
    org_data: OrganizationUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    更新组织
    
    更新组织信息，只有组织拥有者可以更新
    
    Args:
        organization_id: 组织ID
        org_data: 组织更新数据
        current_user: 当前活跃用户
        db: 数据库会话
    
    Returns:
        OrganizationSchema: 更新后的组织信息
    
    Raises:
        HTTPException: 当组织未找到、无权限或名称/域名已存在时抛出
    """
    organization = db.query(Organization).filter(
        Organization.id == organization_id,
        Organization.owner_id == current_user.id
    ).first()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="组织未找到或无权限"
        )
    
    # 检查名称是否被其他组织使用
    if org_data.name and org_data.name != organization.name:
        existing = db.query(Organization).filter(
            Organization.name == org_data.name,
            Organization.id != organization_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="组织名称已存在"
            )
    
    # 检查域名是否被其他组织使用
    if org_data.domain and org_data.domain != organization.domain:
        existing = db.query(Organization).filter(
            Organization.domain == org_data.domain,
            Organization.id != organization_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="域名已被其他组织使用"
            )
    
    # 应用更新
    update_data = org_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(organization, field, value)
    
    db.commit()
    db.refresh(organization)
    
    return organization


@router.delete("/{organization_id}")
def delete_organization(
    organization_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    删除组织
    
    删除组织及其关联的服务，只有组织拥有者可以删除
    
    Args:
        organization_id: 组织ID
        current_user: 当前活跃用户
        db: 数据库会话
    
    Returns:
        dict: 删除结果
    
    Raises:
        HTTPException: 当组织未找到或无权限时抛出
    """
    organization = db.query(Organization).filter(
        Organization.id == organization_id,
        Organization.owner_id == current_user.id
    ).first()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="组织未找到或无权限"
        )
    
    # 检查是否有关联的服务（包括非活跃的）
    from ..models.service import Service
    services = db.query(Service).filter(
        Service.organization_id == organization_id
    ).all()
    
    if services:
        # 删除关联的服务（包括非活跃的）
        for service in services:
            # 从Milvus删除向量
            try:
                from ..services.milvus_service import get_milvus_service
                milvus_service = get_milvus_service()
                milvus_service.delete_service_vector(service.id)
            except Exception as e:
                print(f"警告: 删除服务 {service.id} 的向量失败: {e}")
            
            # 删除服务记录
            db.delete(service)
    
    # 删除组织
    db.delete(organization)
    db.commit()
    
    return {"message": "组织已删除"}