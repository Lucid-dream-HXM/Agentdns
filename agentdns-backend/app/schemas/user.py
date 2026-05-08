from pydantic import BaseModel, EmailStr, Field  # Pydantic基础模型、邮箱验证类型和字段验证
from typing import Optional  # 类型提示，表示可选值
from datetime import datetime  # 日期时间类型

"""
Schemas（数据验证模式）的核心作用：
- 数据验证规则 ：验证输入数据是否符合要求（类型、长度、格式等）
- 数据序列化 ：将Python对象转换为JSON格式返回给客户端
- 数据转换 ：将请求数据转换为Python对象
- 数据过滤 ：决定哪些字段暴露给API，哪些隐藏
- 数据格式化 ：控制数据的输出格式
- 文档生成 ：自动生成API文档（Swagger/OpenAPI）
    
"""

"""
### 不同用途的场景
- UserBase : 作为基类，包含公共字段，避免重复代码
- UserCreate : 用于用户注册，需要密码字段
- UserUpdate : 用于更新用户信息，所有字段都是可选的
- User : API响应使用，不包含敏感信息
- UserLogin : 用于用户登录，包含用户名和密码
- Token : 用于返回认证令牌
"""

class UserBase(BaseModel):
    """
    用户基础模式，包含用户的基本信息
    作为其他用户模式的基类，提供公共字段定义
    """
    # Pydantic 字段定义语法：字段名: 类型 = 默认值 ，Field(...) ：额外的验证规则
    username: str = Field(..., min_length=3, max_length=50, description="用户名，长度3-50字符")  # 用户名，必填字段，最小3字符，最大50字符
    email: EmailStr = Field(..., description="邮箱地址，必须是有效的邮箱格式")  # 邮箱地址，必填字段，自动验证邮箱格式
    full_name: Optional[str] = Field(None, max_length=100, description="用户全名，可选字段，最大100字符")  # 用户全名，可选字段，最大100字符
    is_active: bool = True  # 账户是否激活，默认为True


class UserCreate(UserBase):
    """
    用户创建模式，用于用户注册
    继承UserBase，添加密码字段
    """
    password: str = Field(..., min_length=6, description="密码，必填字段，最小6字符")  # 密码，必填字段，最小6字符


class UserUpdate(BaseModel):
    """
    用户更新模式，用于更新用户信息
    所有字段都是可选的，允许部分更新
    """
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="用户名，可选更新")  # 用户名，可选更新
    email: Optional[EmailStr] = Field(None, description="邮箱地址，可选更新")  # 邮箱地址，可选更新
    full_name: Optional[str] = Field(None, max_length=100, description="用户全名，可选更新")  # 用户全名，可选更新
    is_active: Optional[bool] = Field(None, description="账户是否激活，可选更新")  # 账户激活状态，可选更新


class UserLogin(BaseModel):
    """
    用户登录模式，用于用户登录
    包含用户名和密码字段
    """
    username: str  # 用户名，用于登录
    password: str  # 密码，用于登录验证


class User(UserBase):
    """
    用户响应模式，用于API返回
    不包含敏感信息（如密码），用于向客户端返回用户数据
    """
    id: int  # 用户唯一标识符
    is_verified: bool  # 账户是否已验证
    balance: float  # 账户余额
    api_key: Optional[str] = None  # API密钥
    created_at: datetime  # 创建时间
    updated_at: Optional[datetime] = None  # 更新时间
    
    class Config:
        from_attributes = True  # 允许从ORM对象创建Pydantic模型


class Token(BaseModel):
    """
    令牌模式，用于返回认证令牌
    包含访问令牌和令牌类型
    """
    access_token: str  # 访问令牌，用于后续API请求的身份验证
    token_type: str = "bearer"  # 令牌类型，默认为"bearer"
    expires_in: int  # 令牌过期时间（秒）
    user: User  # 用户信息 