from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class BillingBase(BaseModel):
    """
    账单基础模式，包含账单的基本信息
    作为其他账单模式的基类，提供公共字段定义
    """
    bill_type: str = Field(..., description="账单类型：charge（扣费）、refund（退款）、topup（充值）")  # 账单类型：charge（扣费）、refund（退款）、topup（充值）
    amount: float = Field(..., ge=0, description="账单金额，必须大于等于0")  # 账单金额，必须大于等于0
    currency: str = Field("USD", description="货币类型，默认为USD")  # 货币类型，默认为USD
    description: Optional[str] = Field(None, description="账单描述，可选字段")  # 账单描述，可选字段


class BillingCreate(BillingBase):
    """
    账单创建模式，用于创建新账单
    继承BillingBase，添加服务名称和支付方式字段
    """
    service_name: Optional[str] = Field(None, description="服务名称，可选字段")  # 服务名称，可选字段
    payment_method: str = Field("balance", description="支付方式，默认为balance（余额支付）")  # 支付方式，默认为balance（余额支付）


class Billing(BillingBase):
    """
    账单响应模式，用于API返回
    包含数据库中的所有字段
    """
    id: int  # 账单唯一标识符
    user_id: int  # 用户ID
    bill_id: str  # 账单ID
    service_name: Optional[str] = None  # 服务名称
    usage_period_start: Optional[datetime] = None  # 使用周期开始时间
    usage_period_end: Optional[datetime] = None  # 使用周期结束时间
    status: str  # 账单状态
    payment_method: str  # 支付方式
    transaction_id: Optional[str] = None  # 交易ID
    billing_metadata: Optional[str] = Field(None, description="元数据")  # 元数据
    created_at: datetime  # 创建时间
    updated_at: Optional[datetime] = None  # 更新时间
    processed_at: Optional[datetime] = None  # 处理时间
    
    class Config:
        from_attributes = True  # 允许从ORM对象创建Pydantic模型 