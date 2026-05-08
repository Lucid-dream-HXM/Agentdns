"""
API依赖函数 - 用于定义API的依赖注入函数
提供用户认证、权限检查等功能
"""

from typing import Dict, Any
from fastapi import Depends, HTTPException, status  # FastAPI核心组件，用于依赖注入和HTTP异常处理
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials  # HTTP Bearer认证相关类
from sqlalchemy.orm import Session  # SQLAlchemy数据库会话类型
from ..database import get_db  # 数据库会话依赖函数
from ..core.security import verify_token  # 令牌验证函数
from ..models.user import User  # 用户模型
from ..models.agent import Agent  # 代理模型

# HTTP Bearer安全方案 - 用于从请求头获取认证令牌
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),  # 从请求头获取认证凭证
    db: Session = Depends(get_db)  # 获取数据库会话
) -> User:
    """
    获取当前用户（支持JWT令牌和代理API密钥）
    
    这是核心认证函数，处理两种认证方式：JWT令牌和代理API密钥
    
    Args:
        credentials: HTTP认证凭证，包含令牌
        db: 数据库会话
    
    Returns:
        User: 当前认证用户对象
    
    Raises:
        HTTPException: 当认证失败时抛出
    """
    # 从凭证中提取令牌
    token = credentials.credentials
    
    # 检查是否为代理API密钥（以agent_开头）
    if token.startswith("agent_"):
        # 从数据库查询代理对象
        agent = db.query(Agent).filter(Agent.api_key == token).first()
        if agent is None:
            # 代理API密钥无效
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的代理API密钥",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not agent.is_active:
            # 代理已被禁用
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="代理已被禁用"
            )
        
        if agent.is_suspended:
            # 代理因超出费用限制被暂停
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="代理因费用超限被暂停"
            )
        
        # 获取与代理关联的用户
        user = db.query(User).filter(User.id == agent.user_id).first()
        if user is None or not user.is_active:
            # 关联用户不存在或已被禁用
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="代理关联的用户不存在或已被禁用",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user
    
    # 否则作为JWT令牌处理
    payload = verify_token(token)  # 验证JWT令牌
    if payload is None:
        # 令牌无效
        raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的访问令牌",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    # 从令牌载荷中获取用户标识符
    user_identifier = payload.get("sub")
    if user_identifier is None:
        # 令牌格式无效
        raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的令牌格式",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    # 支持按用户ID或用户名查找
    if isinstance(user_identifier, str) and not user_identifier.isdigit():
        # 如果是字符串且非数字，作为用户名处理
        user = db.query(User).filter(User.username == user_identifier).first()
    else:
        # 否则作为用户ID处理
        user = db.query(User).filter(User.id == int(user_identifier)).first()
    if user is None:
        # 用户不存在
        raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    if not user.is_active:
        # 用户账户已被禁用
        raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户账户已被禁用"
            )
    
    return user


def get_current_principal(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    获取当前调用主体

    与get_current_user不同，该函数会同时返回：
    - user：当前认证用户
    - agent：当前Agent对象（如果是agent_开头的API key），否则为None

    Returns:
        Dict[str, Any]: {"user": user, "agent": agent_or_none}
    """
    token = credentials.credentials

    if token.startswith("agent_"):
        agent = db.query(Agent).filter(Agent.api_key == token).first()
        if agent is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的代理API密钥",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not agent.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="代理已被禁用"
            )

        if agent.is_suspended:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="代理因费用超限被暂停"
            )

        user = db.query(User).filter(User.id == agent.user_id).first()
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="代理关联的用户不存在或已被禁用",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return {
            "user": user,
            "agent": agent
        }

    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的访问令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_identifier = payload.get("sub")
    if user_identifier is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌格式",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if isinstance(user_identifier, str) and not user_identifier.isdigit():
        user = db.query(User).filter(User.username == user_identifier).first()
    else:
        user = db.query(User).filter(User.id == int(user_identifier)).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户账户已被禁用"
        )

    return {
        "user": user,
        "agent": None
    }


def get_current_active_user(
    current_user: User = Depends(get_current_user),  # 通过依赖注入获取当前用户
) -> User:
    """
    获取当前活跃用户
    
    验证用户是否活跃并返回用户对象
    
    Args:
        current_user: 当前认证用户
    
    Returns:
        User: 当前活跃用户对象
    """
    return current_user 


def get_current_agent(
    credentials: HTTPAuthorizationCredentials = Depends(security),  # 从请求头获取认证凭证
    db: Session = Depends(get_db)  # 获取数据库会话
) -> Agent:
    """
    获取当前代理（仅代理API密钥）
    
    专门用于验证代理API密钥的函数
    
    Args:
        credentials: HTTP认证凭证，包含令牌
        db: 数据库会话
    
    Returns:
        Agent: 当前认证代理对象
    
    Raises:
        HTTPException: 当认证失败时抛出
    """
    # 从凭证中提取令牌
    token = credentials.credentials
    
    # 检查是否为代理API密钥（必须以agent_开头）
    if not token.startswith("agent_"):
        # 此端点仅支持代理API密钥
        raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="此端点仅支持代理API密钥",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    # 从数据库查询代理对象
    agent = db.query(Agent).filter(Agent.api_key == token).first()
    if agent is None:
        # 代理API密钥无效
        raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的代理API密钥",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    if not agent.is_active:
        # 代理已被禁用
        raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="代理已被禁用"
            )
    
    if agent.is_suspended:
        # 代理因超出费用限制被暂停
        raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="代理因费用超限被暂停"
            )
    
    return agent


def get_current_admin_user(
    current_user: User = Depends(get_current_user),  # 通过依赖注入获取当前用户
) -> User:
    """
    获取当前管理员用户
    
    验证当前用户是否具有管理员权限
    
    Args:
        current_user: 当前认证用户
    
    Returns:
        User: 当前管理员用户对象
    
    Raises:
        HTTPException: 当用户没有管理员权限时抛出
    """
    from ..core.permissions import PermissionChecker  # 导入权限检查器
    # 检查用户是否具有管理员访问权限
    PermissionChecker.check_admin_access(current_user)
    return current_user


def get_current_client_user(
    current_user: User = Depends(get_current_user),  # 通过依赖注入获取当前用户
) -> User:
    """
    获取当前客户端用户
    
    验证当前用户是否具有客户端访问权限
    
    Args:
        current_user: 当前认证用户
    
    Returns:
        User: 当前客户端用户对象
    
    Raises:
        HTTPException: 当用户没有客户端权限时抛出
    """
    from ..core.permissions import PermissionChecker  # 导入权限检查器
    # 检查用户是否具有客户端访问权限
    PermissionChecker.check_client_access(current_user)
    return current_user