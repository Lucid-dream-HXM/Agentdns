from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

"""
### 不同用途的场景
- OrganizationBase : 作为基类，包含公共字段，避免重复代码
- OrganizationCreate : 用于创建组织，包含所有必填字段
- OrganizationUpdate : 用于更新组织信息，所有字段都是可选的
- Organization : API响应使用，包含数据库中的所有字段
"""

class OrganizationBase(BaseModel):
    """
    组织基础模式，包含组织的基本信息
    作为其他组织模式的基类，提供公共字段定义
    """
    name: str = Field(..., min_length=1, max_length=100, description="组织名称，唯一标识，最大100字符")  # 组织名称，必填字段，最大100字符
    domain: Optional[str] = Field(None, max_length=255, description="组织域名，如openai.com，最大255字符")  # 组织域名，可选字段，最大255字符
    display_name: Optional[str] = Field(None, max_length=100, description="组织显示名称，如OpenAI，最大100字符")  # 组织显示名称，可选字段，最大100字符
    description: Optional[str] = Field(None, description="组织描述，可选字段")  # 组织描述，可选字段
    website: Optional[str] = Field(None, max_length=255, description="组织网站URL，最大255字符")  # 组织网站URL，可选字段，最大255字符
    logo_url: Optional[str] = Field(None, max_length=500, description="组织Logo URL，最大500字符")  # 组织Logo URL，可选字段，最大500字符


class OrganizationCreate(OrganizationBase):
    """
    组织创建模式，用于创建组织
    继承OrganizationBase，不需要添加额外字段
    """
    pass


class OrganizationUpdate(BaseModel):
    """
    组织更新模式，用于更新组织信息
    所有字段都是可选的，允许部分更新
    """
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="组织名称，可选更新")  # 组织名称，可选更新
    domain: Optional[str] = Field(None, max_length=255, description="组织域名，可选更新")  # 组织域名，可选更新
    display_name: Optional[str] = Field(None, max_length=100, description="组织显示名称，可选更新")  # 组织显示名称，可选更新
    description: Optional[str] = Field(None, description="组织描述，可选更新")  # 组织描述，可选更新
    website: Optional[str] = Field(None, max_length=255, description="组织网站URL，可选更新")  # 组织网站URL，可选更新
    logo_url: Optional[str] = Field(None, max_length=500, description="组织Logo URL，可选更新")  # 组织Logo URL，可选更新


class Organization(OrganizationBase):
    """
    组织响应模式，用于API返回
    用于向客户端返回组织数据
    """
    id: int  # 组织唯一标识符
    is_verified: bool  # 组织是否已验证
    owner_id: int  # 组织所有者ID
    created_at: datetime  # 创建时间
    updated_at: Optional[datetime] = None  # 更新时间
    
    class Config:
        from_attributes = True  # 允许从ORM对象创建Pydantic模型 