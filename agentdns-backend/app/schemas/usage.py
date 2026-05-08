from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

# Usage定义了API返回给客户端的数据结构
class UsageBase(BaseModel):
    """
    使用记录基础模式，包含使用记录的基本信息
    作为其他使用记录模式的基类，提供公共字段定义
    """
    service_id: int = Field(..., description="服务ID，必填字段")  # 服务ID，必填字段
    method: str = Field("POST", description="HTTP方法，默认为POST")  # HTTP方法，默认为POST
    endpoint: str = Field(..., description="调用的端点，必填字段")  # 调用的端点，必填字段
    protocol: str = Field("MCP", description="使用的协议，默认为MCP")  # 使用的协议（MCP、A2A、ANP），默认为MCP


class UsageCreate(UsageBase):
    """
    使用记录创建模式，用于创建新的使用记录
    继承UsageBase，添加使用统计和元数据字段
    """
    tokens_used: int = Field(0, ge=0, description="使用的token数，默认为0")  # 使用的token数，默认为0，必须大于等于0
    requests_count: int = Field(1, ge=1, description="请求数量，默认为1")  # 请求数量，默认为1，必须大于等于1
    data_transfer_mb: float = Field(0.0, ge=0, description="数据传输量（MB），默认为0.0")  # 数据传输量（MB），默认为0.0，必须大于等于0
    execution_time_ms: Optional[int] = Field(None, description="执行时间（毫秒），可选字段")  # 执行时间（毫秒），可选字段
    request_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="请求元数据，JSON格式，默认为空字典")  # 请求元数据，JSON格式，默认为空字典


class Usage(UsageBase):
    """
    使用记录响应模式，用于API返回
    包含数据库中的所有字段
    """
    id: int  # 使用记录唯一标识符
    user_id: int  # 用户ID
    request_id: str  # 唯一请求ID
    tokens_used: int  # 使用的token数
    requests_count: int  # 请求数量
    data_transfer_mb: float  # 数据传输量（MB）
    execution_time_ms: Optional[int] = None  # 执行时间（毫秒）
    cost_amount: float  # 成本金额
    cost_currency: str  # 货币类型
    billing_status: str  # 计费状态：pending（待处理）、charged（已计费）、failed（失败）
    status_code: Optional[int] = None  # HTTP状态码
    error_message: Optional[str] = None  # 错误信息
    request_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="请求元数据，JSON格式")  # 请求元数据，JSON格式
    started_at: datetime  # 开始时间
    completed_at: Optional[datetime] = None  # 完成时间
    created_at: datetime  # 创建时间
    
    class Config:
        from_attributes = True  # 允许从ORM对象创建Pydantic模型
        exclude = {'metadata', 'registry'}  # 排除SQLAlchemy内部属性
    """
    SQLAlchemy内部属性
    - metadata ：包含所有表的元数据定义
    - registry ：包含ORM映射注册信息
    排除的原因可能是防御性编程，防止某些边缘情况
    """ 