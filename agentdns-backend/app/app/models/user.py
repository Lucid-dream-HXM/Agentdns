from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float  # SQLAlchemy ORM核心组件，用于定义数据库模型字段
from sqlalchemy.sql import func  # SQLAlchemy SQL函数，用于处理数据库时间戳等
from sqlalchemy.orm import relationship  # SQLAlchemy ORM关系映射，用于定义模型间关联
from ..database import Base  # 数据库基础模型类，所有模型都需要继承此类


class User(Base):
    """
    用户模型 - 存储系统中的用户信息
    
    该模型定义了系统中用户的基本属性，包括登录信息、账户状态、余额等
    与其他模型（组织、代理、账单记录等）存在关联关系
    """
    __tablename__ = "users"  # 定义数据库表名
    
    # 基础信息字段
    id = Column(Integer, primary_key=True, index=True)  # 用户唯一标识符，主键，带索引
    username = Column(String(50), unique=True, index=True, nullable=False)  # 用户名，唯一约束，带索引，不允许为空
    email = Column(String(100), unique=True, index=True, nullable=False)  # 邮箱地址，唯一约束，带索引，不允许为空
    full_name = Column(String(100))  # 用户全名，可选字段
    hashed_password = Column(String(255), nullable=False)  # 哈希后的密码，不允许为空
    
    # 角色权限字段
    role = Column(String(20), default="client", nullable=False)  # 用户角色：admin（管理员）、client（普通客户）、org_owner（组织所有者），默认为client
    
    # 账户状态字段
    is_active = Column(Boolean, default=True)  # 账户是否激活，默认为True
    is_verified = Column(Boolean, default=False)  # 账户是否已验证，默认为False
    
    # 账户余额字段
    balance = Column(Float, default=0.0)  # 账户余额，默认为0.0
    
    # 时间戳字段
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 创建时间，服务器自动生成当前时间
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())  # 更新时间，更新记录时自动更新
    last_login_at = Column(DateTime(timezone=True))  # 最后登录时间
    
    # 模型关联关系
    organizations = relationship("Organization", back_populates="owner")  # 与组织模型的反向关联（一个用户可以拥有多个组织）
    agents = relationship("Agent", back_populates="user")  # 与代理模型的反向关联（一个用户可以拥有多个代理）
    billing_records = relationship("Billing", back_populates="user")  # 与账单模型的反向关联（一个用户有多条账单记录）
    usage_records = relationship("Usage", back_populates="user")  # 与使用记录模型的反向关联（一个用户有多条使用记录）
    async_tasks = relationship("AsyncTask", back_populates="user")  # 与异步任务模型的反向关联（一个用户有多个异步任务）