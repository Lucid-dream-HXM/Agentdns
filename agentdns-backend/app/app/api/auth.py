from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
import secrets

from ..database import get_db
from ..core.security import (
    create_access_token, 
    get_password_hash, 
    verify_password
)
from ..core.config import settings
from ..models.user import User
from ..schemas.user import UserCreate, UserLogin, Token, User as UserSchema

router = APIRouter()


@router.post("/register", response_model=UserSchema)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    用户注册
    
    创建新用户，检查用户名和邮箱是否已存在，哈希密码后保存到数据库
    
    Args:
        user_data: 用户注册数据，包含用户名、邮箱、密码等信息
        db: 数据库会话
    
    Returns:
        创建的用户对象
    
    Raises:
        HTTPException: 如果用户名或邮箱已存在
    """
    # 检查用户名是否存在
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    # 检查邮箱是否存在
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已存在"
        )
    
    # 创建新用户
    hashed_password = get_password_hash(user_data.password)
    
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        is_active=user_data.is_active
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user


@router.post("/login", response_model=Token)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """
    用户登录
    
    验证用户凭据，检查用户是否活跃，生成JWT访问令牌
    
    Args:
        user_data: 用户登录数据，包含用户名和密码
        db: 数据库会话
    
    Returns:
        包含访问令牌、令牌类型、过期时间和用户信息的Token对象
    
    Raises:
        HTTPException: 如果用户名或密码无效，或用户账号已禁用
    """
    # 查找用户
    user = db.query(User).filter(User.username == user_data.username).first()
    
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码无效",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户账号已禁用"
        )
    
    # 创建访问令牌
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, 
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": user
    }


@router.post("/token", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    OAuth2兼容的登录端点
    
    用于支持OAuth2密码流的登录端点，接受表单数据格式的登录凭据
    
    Args:
        form_data: OAuth2密码表单数据，包含用户名和密码
        db: 数据库会话
    
    Returns:
        包含访问令牌、令牌类型、过期时间和用户信息的Token对象
    """
    user_data = UserLogin(username=form_data.username, password=form_data.password)
    return login(user_data, db)