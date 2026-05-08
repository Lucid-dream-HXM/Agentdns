from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, JSON, Text, Boolean  # SQLAlchemy ORM核心组件，用于定义数据库模型字段
from sqlalchemy.sql import func  # SQLAlchemy SQL函数，用于处理数据库时间戳等
from sqlalchemy.orm import relationship  # SQLAlchemy ORM关系映射，用于定义模型间关联
from ..database import Base  # 数据库基础模型类，所有模型都需要继承此类

FINAL_STATE_SUCCESS = "success"
FINAL_STATE_PARTIAL = "partial"
FINAL_STATE_FAIL = "fail"
FINAL_STATE_PENDING = "pending"


class Usage(Base):
    """
    使用记录模型 - 存储系统中的服务使用记录
    
    该模型定义了系统中服务使用记录的基本属性，包括请求信息、使用统计、计费信息等
    与用户、服务模型存在关联关系
    """
    __tablename__ = "usage_records"  # 定义数据库表名
    
    # 基础字段
    id = Column(Integer, primary_key=True, index=True)  # 使用记录唯一标识符，主键，带索引
    
    # 关联字段
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 用户ID，外键，不允许为空
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)  # 服务ID，外键，不允许为空
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)  # 发起本次调用的Agent ID，可空

    # 请求信息字段
    request_id = Column(String(64), unique=True, index=True)  # 唯一请求ID，唯一约束，带索引
    method = Column(String(10))  # HTTP方法
    endpoint = Column(String(500))  # 调用的端点URL
    protocol = Column(String(20))  # 使用的协议（MCP、A2A、ANP）
    
    # 使用统计字段
    tokens_used = Column(Integer, default=0)  # 使用的令牌数，默认为0
    requests_count = Column(Integer, default=1)  # 请求次数，默认为1
    data_transfer_mb = Column(Float, default=0.0)  # 数据传输量（MB），默认为0.0
    execution_time_ms = Column(Integer)  # 执行时间（毫秒）
    
    # 计费信息字段
    cost_amount = Column(Float, default=0.0)  # 成本金额，默认为0.0
    cost_currency = Column(String(3), default="USD")  # 货币类型，默认为USD
    billing_status = Column(String(20), default="pending")  # 计费状态：pending（待计费）、charged（已计费）、failed（失败），默认为pending
    
    # 状态字段
    status_code = Column(Integer)  # HTTP状态码 - 网关/HTTP层调用结果，反映网络层面的成功或错误
    error_message = Column(Text)  # 错误信息
    request_metadata = Column(JSON)  # 额外元数据，JSON格式
    http_mode = Column(String(10))  # 调用模式：sync / stream / async
    is_meaningful = Column(Boolean, default=True)  # 是否真正进入服务执行阶段，可用于控制是否允许评价
    final_state = Column(String(20), default="success")  # 服务执行结果抽象 - success（完全成功）/ partial（部分成功）/ fail（失败）/ pending（待处理）

    # 时间戳字段
    started_at = Column(DateTime(timezone=True), server_default=func.now())  # 请求开始时间，服务器自动生成当前时间
    completed_at = Column(DateTime(timezone=True))  # 请求完成时间
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 创建时间，服务器自动生成当前时间
    
    # 模型关联关系
    user = relationship("User", back_populates="usage_records")  # 与用户模型的反向关联（一个用户有多条使用记录）
    service = relationship("Service", back_populates="usage_records")  # 与服务模型的反向关联（一个服务有多条使用记录）
    agent = relationship("Agent", back_populates="service_usages")
    async_tasks = relationship("AsyncTask", back_populates="usage")
    review = relationship("ServiceReview", back_populates="usage", uselist=False) 