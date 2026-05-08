from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON, Float  # SQLAlchemy ORM核心组件，用于定义数据库模型字段
from sqlalchemy.sql import func  # SQLAlchemy SQL函数，用于处理数据库时间戳等
from sqlalchemy.orm import relationship  # SQLAlchemy ORM关系映射，用于定义模型间关联
from ..database import Base  # 数据库基础模型类，所有模型都需要继承此类


class Agent(Base):
    """
    代理模型 - 存储系统中的代理信息
    
    该模型定义了系统中代理的基本属性，包括代理名称、API密钥、成本控制、状态管理等
    与用户、代理使用记录模型存在关联关系
    """
    __tablename__ = "agents"  # 定义数据库表名
    
    # 基础字段
    id = Column(Integer, primary_key=True, index=True)  # 代理唯一标识符，主键，带索引
    name = Column(String(100), nullable=False)  # 代理名称，不允许为空
    description = Column(Text)  # 代理描述
    api_key = Column(String(500), unique=True, nullable=False)  # AgentDNS API密钥，唯一约束，不允许为空
    
    # 成本控制字段
    cost_limit_daily = Column(Float, default=0.0)  # 每日成本限制，默认为0.0（无限制）
    cost_limit_monthly = Column(Float, default=0.0)  # 每月成本限制，默认为0.0（无限制）
    cost_used_daily = Column(Float, default=0.0)  # 今日已使用成本，默认为0.0
    cost_used_monthly = Column(Float, default=0.0)  # 本月已使用成本，默认为0.0
    
    # 状态管理字段
    is_active = Column(Boolean, default=True)  # 是否启用，默认为True
    is_suspended = Column(Boolean, default=False)  # 是否因超出限制而暂停，默认为False
    
    # 配置字段
    allowed_services = Column(JSON)  # 允许访问的服务列表（空表示所有服务），JSON格式
    rate_limit_per_minute = Column(Integer, default=60)  # 每分钟请求限制，默认为60
    
    # 统计字段
    total_requests = Column(Integer, default=0)  # 总请求数，默认为0
    total_cost = Column(Float, default=0.0)  # 总成本，默认为0.0
    last_used_at = Column(DateTime(timezone=True))  # 最后使用时间
    
    # 外键和时间戳字段
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 所属用户ID，外键，不允许为空
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 创建时间，服务器自动生成当前时间
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())  # 更新时间，更新记录时自动更新
    
    # 模型关联关系
    user = relationship("User", back_populates="agents")  # 与用户模型的反向关联（一个用户可以拥有多个代理）
    usage_records = relationship("AgentUsage", back_populates="agent")  # 与代理使用记录模型的反向关联（一个代理有多条使用记录）
    service_usages = relationship("Usage", back_populates="agent")
    async_tasks = relationship("AsyncTask", back_populates="agent")
    reviews = relationship("ServiceReview", back_populates="reviewer_agent")


class AgentUsage(Base):
    """
    代理使用记录模型 - 存储系统中代理的使用记录
    
    该模型定义了代理使用记录的基本属性，包括请求信息、成本和性能、状态等
    与代理模型存在关联关系
    """
    __tablename__ = "agent_usage"  # 定义数据库表名
    
    # 基础字段
    id = Column(Integer, primary_key=True, index=True)  # 使用记录唯一标识符，主键，带索引
    
    # 关联字段
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)  # 代理ID，外键，不允许为空
    
    # 请求信息字段
    service_name = Column(String(200))  # 使用的服务名称
    request_method = Column(String(10))  # HTTP方法
    request_path = Column(String(500))  # 请求路径
    
    # 成本和性能字段
    cost = Column(Float, default=0.0)  # 本次请求的成本，默认为0.0
    tokens_used = Column(Integer, default=0)  # 使用的令牌数，默认为0
    response_time_ms = Column(Integer)  # 响应时间（毫秒）
    
    # 状态字段
    status_code = Column(Integer)  # HTTP状态码
    error_message = Column(Text)  # 错误信息
    
    # 时间戳字段
    requested_at = Column(DateTime(timezone=True), server_default=func.now())  # 请求时间，服务器自动生成当前时间
    
    # 模型关联关系
    agent = relationship("Agent", back_populates="usage_records")  # 与代理模型的反向关联（一个代理有多条使用记录） 