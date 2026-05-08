from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean  # SQLAlchemy ORM核心组件，用于定义数据库模型字段
from sqlalchemy.sql import func  # SQLAlchemy SQL函数，用于处理数据库时间戳等
from sqlalchemy.orm import relationship  # SQLAlchemy ORM关系映射，用于定义模型间关联
from ..database import Base  # 数据库基础模型类，所有模型都需要继承此类


class Organization(Base):
    """
    组织模型 - 存储系统中的组织信息
    
    该模型定义了系统中组织的基本属性，包括组织名称、域名、描述等
    与用户、服务等模型存在关联关系
    """
    __tablename__ = "organizations"  # 定义数据库表名
    
    # 基础信息字段
    id = Column(Integer, primary_key=True, index=True)  # 组织唯一标识符，主键，带索引
    name = Column(String(100), unique=True, index=True, nullable=False)  # 组织名称，例如"openai"，唯一约束，带索引，不允许为空
    domain = Column(String(255), unique=True, index=True)  # 组织域名，例如"openai.com"，唯一约束，带索引
    display_name = Column(String(100))  # 显示名称，例如"OpenAI"
    description = Column(Text)  # 组织描述
    website = Column(String(255))  # 组织网站URL
    logo_url = Column(String(500))  # 组织Logo URL
    
    # 状态字段
    is_verified = Column(Boolean, default=False)  # 组织是否已验证，默认为False
    
    # 外键字段
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 组织所有者ID，外键，不允许为空
    
    # 时间戳字段
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 创建时间，服务器自动生成当前时间
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())  # 更新时间，更新记录时自动更新
    
    # 模型关联关系
    owner = relationship("User", back_populates="organizations")  # 与用户模型的反向关联（一个用户可以拥有多个组织）
    services = relationship("Service", back_populates="organization")  # 与服务模型的反向关联（一个组织可以有多个服务） 