from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON, Float  # SQLAlchemy ORM核心组件，用于定义数据库模型字段
from sqlalchemy.sql import func  # SQLAlchemy SQL函数，用于处理数据库时间戳等
from sqlalchemy.orm import relationship  # SQLAlchemy ORM关系映射，用于定义模型间关联
from ..database import Base  # 数据库基础模型类，所有模型都需要继承此类


class Service(Base):
    """
    服务模型 - 存储系统中的服务信息
    
    该模型定义了系统中服务的基本属性，包括服务名称、分类、端点、协议、定价等
    与组织、服务元数据、使用记录、异步任务等模型存在关联关系
    """
    __tablename__ = "services"  # 定义数据库表名
    
    # 基础信息字段
    id = Column(Integer, primary_key=True, index=True)  # 服务唯一标识符，主键，带索引
    name = Column(String(100), index=True, nullable=False)  # 服务名称，带索引，不允许为空
    category = Column(String(50), index=True)  # 服务分类，带索引
    agentdns_uri = Column(String(500), unique=True, index=True, nullable=False)  # AgentDNS URI，格式为agentdns://org/category/name，唯一约束，带索引，不允许为空
    description = Column(Text)  # 服务描述（合并了短描述和长描述）
    version = Column(String(20), default="1.0.0")  # 服务版本，默认为1.0.0
    is_active = Column(Boolean, default=True)  # 服务是否激活，默认为True
    is_public = Column(Boolean, default=True)  # 服务是否公开，默认为True
    
    # 端点配置字段
    endpoint_url = Column(String(500), nullable=False)  # 实际端点URL，不允许为空
    protocol = Column(String(20), default="MCP")  # 协议类型："MCP", "A2A", "ANP", "HTTP"，默认为MCP
    authentication_required = Column(Boolean, default=True)  # 是否需要身份验证，默认为True
    
    # HTTP代理特有字段
    agentdns_path = Column(String(500), index=True)  # 自定义AgentDNS路径，例如：org/search/websearch，带索引
    http_method = Column(String(10))  # HTTP方法：GET, POST等
    http_mode = Column(String(10))  # HTTP模式："sync"（同步）, "stream"（流式）, "async"（异步）
    input_description = Column(Text)  # 输入描述
    output_description = Column(Text)  # 输出描述
    service_api_key = Column(String(500))  # 提供商API密钥（加密存储）
    
    # 定价字段
    pricing_model = Column(String(50))  # 定价模型："per_request"（按请求）, "per_token"（按令牌）, "subscription"（订阅制）
    price_per_unit = Column(Float, default=0.0)  # 单位价格，默认为0.0
    currency = Column(String(3), default="USD")  # 货币类型，默认为USD
    
    # 元数据字段
    tags = Column(JSON)  # 标签，JSON格式存储
    capabilities = Column(JSON)  # 功能描述，JSON格式存储
    
    # 外键和时间戳字段
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)  # 所属组织ID，外键，不允许为空
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 创建时间，服务器自动生成当前时间
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())  # 更新时间，更新记录时自动更新
    
    # 模型关联关系
    organization = relationship("Organization", back_populates="services")  # 与组织模型的正向关联（一个组织可以有多个服务）
    service_metadata = relationship("ServiceMetadata", back_populates="service", uselist=False)  # 与服务元数据模型的一对一关联
    usage_records = relationship("Usage", back_populates="service")  # 与使用记录模型的反向关联（一个服务有多条使用记录）
    async_tasks = relationship("AsyncTask", back_populates="service")  # 与异步任务模型的反向关联（一个服务有多个异步任务）
    reviews = relationship("ServiceReview", back_populates="service")
    trust_stats = relationship("ServiceTrustStats", back_populates="service", uselist=False)


class ServiceMetadata(Base):
    """
    服务元数据模型 - 存储服务的详细元数据信息
    
    该模型定义了服务的详细元数据，包括OpenAPI规范、示例、健康检查等
    与服务模型存在一对一关联关系
    """
    __tablename__ = "service_metadata"  # 定义数据库表名
    
    # 基础字段
    id = Column(Integer, primary_key=True, index=True)  # 服务元数据唯一标识符，主键，带索引
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)  # 关联的服务ID，外键，不允许为空
    
    # API规范字段
    openapi_spec = Column(JSON)  # OpenAPI规范，JSON格式存储
    examples = Column(JSON)  # 使用示例，JSON格式存储
    rate_limits = Column(JSON)  # 速率限制，JSON格式存储
    
    # 运行时信息字段
    health_check_url = Column(String(500))  # 健康检查URL
    status = Column(String(20), default="active")  # 服务状态：active（活跃）, maintenance（维护中）, deprecated（已弃用），默认为active
    uptime_stats = Column(JSON)  # 可用性统计，JSON格式存储
    
    # 搜索优化字段
    search_keywords = Column(JSON)  # 搜索关键词，JSON格式存储
    embedding_vector = Column(JSON)  # 嵌入向量（用于语义搜索），JSON格式存储
    
    # 时间戳字段
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 创建时间，服务器自动生成当前时间
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())  # 更新时间，更新记录时自动更新
    
    # 模型关联关系
    service = relationship("Service", back_populates="service_metadata")  # 与服务模型的正向关联（一对一关系） 