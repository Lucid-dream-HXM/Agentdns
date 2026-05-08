from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Boolean, Text  # SQLAlchemy ORM核心组件，用于定义数据库模型字段
from sqlalchemy.sql import func  # SQLAlchemy SQL函数，用于处理数据库时间戳等
from sqlalchemy.orm import relationship  # SQLAlchemy ORM关系映射，用于定义模型间关联
from ..database import Base  # 数据库基础模型类，所有模型都需要继承此类


class Billing(Base):
    """
    账单模型 - 存储系统中的账单记录
    
    该模型定义了系统中账单的基本属性，包括账单类型、金额、状态等
    与用户模型存在关联关系
    """
    __tablename__ = "billing_records"  # 定义数据库表名
    
    # 基础字段
    id = Column(Integer, primary_key=True, index=True)  # 账单唯一标识符，主键，带索引
    
    # 关联字段
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 用户ID，外键，不允许为空
    
    # 账单信息字段
    bill_id = Column(String(64), unique=True, index=True)  # 账单ID，唯一约束，带索引
    bill_type = Column(String(20), nullable=False)  # 账单类型：charge（收费）、refund（退款）、topup（充值），不允许为空
    amount = Column(Float, nullable=False)  # 账单金额，不允许为空
    currency = Column(String(3), default="USD")  # 货币类型，默认为USD
    
    # 描述字段
    description = Column(Text)  # 账单描述
    service_name = Column(String(100))  # 相关服务名称
    usage_period_start = Column(DateTime(timezone=True))  # 使用周期开始时间
    usage_period_end = Column(DateTime(timezone=True))  # 使用周期结束时间
    
    # 状态字段
    status = Column(String(20), default="pending")  # 账单状态：pending（待处理）、completed（已完成）、failed（失败）、cancelled（已取消），默认为pending
    payment_method = Column(String(50))  # 支付方式：credit_card（信用卡）、paypal、crypto（加密货币）、balance（余额）
    transaction_id = Column(String(100))  # 外部交易ID
    
    # 元数据字段
    billing_metadata = Column(String(1000))  # 额外信息，JSON字符串格式
    
    # 时间戳字段
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 创建时间，服务器自动生成当前时间
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())  # 更新时间，更新记录时自动更新
    processed_at = Column(DateTime(timezone=True))  # 处理时间
    
    # 模型关联关系
    user = relationship("User")  # 与用户模型的关联（一个用户有多条账单记录） 