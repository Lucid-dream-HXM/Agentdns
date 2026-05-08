from datetime import datetime, timedelta  # 日期时间处理模块，用于计算令牌过期时间
from typing import Optional, Union  # 类型提示模块，用于指定可选和联合类型
from jose import JWTError, jwt  # JOSE库，用于JWT令牌的编码和解码
from passlib.context import CryptContext  # 密码哈希库，用于安全地存储密码
import warnings  # 导入警告模块以处理bcrypt兼容性问题
warnings.filterwarnings('ignore', category=DeprecationWarning)  # 忽略bcrypt相关的弃用警告
from .config import settings  # 项目配置，包含安全相关配置

# 密码哈希配置 - 使用bcrypt算法对密码进行哈希处理，提高安全性
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    创建访问令牌
    生成JWT访问令牌，用于API认证
    
    Args:
        data: 令牌中要包含的数据（如用户信息）
        expires_delta: 令牌过期时间间隔，如果为None则使用默认过期时间
    
    Returns:
        编码后的JWT令牌字符串
    """
    # 复制要编码的数据
    to_encode = data.copy()
    # 计算令牌过期时间
    if expires_delta:
        # 如果提供了过期时间间隔，使用该间隔
        expire = datetime.utcnow() + expires_delta
    else:
        # 否则使用配置中的默认过期时间
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # 将过期时间添加到要编码的数据中
    to_encode.update({"exp": expire})
    # 使用配置的密钥和算法对数据进行JWT编码
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_token(token: str):
    """
    验证访问令牌
    解码并验证JWT令牌的有效性
    
    Args:
        token: 要验证的JWT令牌字符串
    
    Returns:
        令牌的载荷数据（如果验证成功），否则返回None
    """
    try:
        # 使用配置的密钥和算法解码JWT令牌
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        # 如果解码失败（如令牌无效或已过期），返回None
        return None


def get_password_hash(password: str) -> str:
    """
    获取密码哈希
    将明文密码转换为安全的哈希值进行存储
    修复bcrypt兼容性问题，限制密码长度
    
    Args:
        password: 明文密码
    
    Returns:
        密码的哈希值
    """
    # 限制密码长度为72字节以避免bcrypt错误
    if len(password.encode('utf-8')) > 72:
        password = password.encode('utf-8')[:72].decode('utf-8', errors='ignore')
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码
    比较明文密码与存储的哈希值是否匹配
    
    Args:
        plain_password: 明文密码
        hashed_password: 存储的密码哈希值
    
    Returns:
        如果密码匹配返回True，否则返回False
    """
    return pwd_context.verify(plain_password, hashed_password)