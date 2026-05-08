"""
客户端认证API - 用于客户前端
提供客户端用户注册、登录和获取用户档案等功能
"""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional

from ...database import get_db
from ...models.user import User
from ...core.security import (
    verify_password, 
    get_password_hash, 
    create_access_token
)
from ...core.config import settings
from ...core.permissions import UserRole
from ...api.deps import get_current_client_user

router = APIRouter()


class ClientRegisterRequest(BaseModel):
    """
    客户端注册请求
    
    包含客户端用户注册所需的基本信息
    """
    username: str  # 用户名
    email: EmailStr  # 邮箱地址
    full_name: Optional[str] = None  # 全名，可选
    password: str  # 密码


class ClientLoginResponse(BaseModel):
    """
    客户端登录响应
    
    包含访问令牌和用户信息
    """
    access_token: str  # 访问令牌
    token_type: str = "bearer"  # 令牌类型，默认为bearer
    user: dict  # 用户信息


class ClientUserProfile(BaseModel):
    """
    客户端用户档案
    
    包含客户端用户的详细信息
    """
    id: int  # 用户ID
    username: str  # 用户名
    email: str  # 邮箱地址
    full_name: Optional[str]  # 全名，可选
    balance: float  # 用户余额
    is_active: bool  # 是否活跃
    is_verified: bool  # 是否已验证
    created_at: str  # 创建时间


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """
    通过邮箱获取用户
    
    Args:
        db: 数据库会话
        email: 用户邮箱
    
    Returns:
        用户对象，如果不存在则返回None
    """
    return db.query(User).filter(User.email == email).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """
    通过用户名获取用户
    
    Args:
        db: 数据库会话
        username: 用户名
    
    Returns:
        用户对象，如果不存在则返回None
    """
    return db.query(User).filter(User.username == username).first()


def create_client_user(db: Session, user_data: ClientRegisterRequest) -> User:
    """
    创建客户端用户
    
    检查邮箱和用户名是否已存在，创建新的客户端用户
    
    Args:
        db: 数据库会话
        user_data: 客户端注册请求数据
    
    Returns:
        创建的用户对象
    
    Raises:
        HTTPException: 如果邮箱或用户名已存在
    """
    # 检查邮箱是否已存在
    if get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已注册"
        )
    
    # 检查用户名是否已存在
    if get_user_by_username(db, user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已被使用"
        )
    
    # 创建新用户
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        role="client",  # 客户端用户 - 使用字符串，不是枚举
        is_active=True,
        is_verified=False,  # 新用户默认未验证
        balance=0.0  # 初始余额为0
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def authenticate_client_user(db: Session, username: str, password: str) -> Optional[User]:
    """
    认证客户端用户登录
    
    验证用户名/邮箱和密码，检查用户是否活跃，以及用户角色是否为客户端或管理员
    
    Args:
        db: 数据库会话
        username: 用户名或邮箱
        password: 密码
    
    Returns:
        认证成功的用户对象，如果认证失败则返回None
    """
    user = get_user_by_username(db, username) or get_user_by_email(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    # 只允许客户端用户和管理员登录客户端
    if user.role not in ["client", "admin"]:
        return None
    return user


@router.post("/register", response_model=ClientUserProfile)
def register_client_user(
    user_data: ClientRegisterRequest,
    db: Session = Depends(get_db)
):
    """
    客户端用户注册
    
    创建新的客户端用户，返回用户档案信息
    
    Args:
        user_data: 客户端注册请求数据
        db: 数据库会话
    
    Returns:
        客户端用户档案
    
    Raises:
        HTTPException: 如果注册失败
    """
    try:
        user = create_client_user(db, user_data)
        return ClientUserProfile(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            balance=user.balance,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at.isoformat() if user.created_at else ""
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"注册失败: {str(e)}"
        )


@router.post("/login", response_model=ClientLoginResponse)
def login_client_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    客户端用户登录
    
    验证用户凭据，生成访问令牌，返回登录响应
    
    Args:
        form_data: OAuth2密码表单数据，包含用户名和密码
        db: 数据库会话
    
    Returns:
        客户端登录响应，包含访问令牌和用户信息
    
    Raises:
        HTTPException: 如果登录失败
    """
    user = authenticate_client_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码无效",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 创建访问令牌
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=access_token_expires
    )
    
    return ClientLoginResponse(
        access_token=access_token,
        token_type="bearer",
        user={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "balance": user.balance,
            "is_active": user.is_active,
            "is_verified": user.is_verified
        }
    )


@router.get("/me", response_model=ClientUserProfile)
def get_current_client_profile(
    current_user: User = Depends(get_current_client_user),
):
    """
    获取当前客户端用户档案
    
    返回当前登录的客户端用户的详细信息
    
    Args:
        current_user: 当前客户端用户
    
    Returns:
        客户端用户档案
    """
    return ClientUserProfile(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        balance=current_user.balance,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at.isoformat() if current_user.created_at else ""
    )