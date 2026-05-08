from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class AgentBase(BaseModel):
    """
    代理基础模式，包含代理的基本信息
    作为其他代理模式的基类，提供公共字段定义
    """
    name: str = Field(..., min_length=1, max_length=100, description="代理名称，必填字段，最大100字符")  # 代理名称，必填字段，最大100字符
    description: Optional[str] = Field(None, description="代理描述，可选字段")  # 代理描述，可选字段


class AgentCreate(AgentBase):
    """
    代理创建模式，用于创建新代理
    继承AgentBase，添加成本限制和服务限制字段
    """
    cost_limit_daily: float = Field(0.0, ge=0, description="每日成本限制，默认为0.0，表示无限制")  # 每日成本限制，默认为0.0（无限制）
    cost_limit_monthly: float = Field(0.0, ge=0, description="每月成本限制，默认为0.0，表示无限制")  # 每月成本限制，默认为0.0（无限制）
    allowed_services: Optional[List[str]] = Field(None, description="允许访问的服务列表，可选字段")  # 允许访问的服务列表，可选字段
    rate_limit_per_minute: int = Field(60, ge=1, le=10000, description="每分钟请求限制，默认为60，范围1-10000")  # 每分钟请求限制，默认为60


class AgentUpdate(BaseModel):
    """
    代理更新模式，用于更新代理信息
    所有字段都是可选的，允许部分更新
    """
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="代理名称，可选更新")  # 代理名称，可选更新
    description: Optional[str] = Field(None, description="代理描述，可选更新")  # 代理描述，可选更新
    cost_limit_daily: Optional[float] = Field(None, ge=0, description="每日成本限制，0.0表示无限制")  # 每日成本限制，0.0表示无限制
    cost_limit_monthly: Optional[float] = Field(None, ge=0, description="每月成本限制，0.0表示无限制")  # 每月成本限制，0.0表示无限制
    allowed_services: Optional[List[str]] = Field(None, description="允许访问的服务列表，可选更新")  # 允许访问的服务列表，可选更新
    rate_limit_per_minute: Optional[int] = Field(None, ge=1, le=10000, description="每分钟请求限制，可选更新")  # 每分钟请求限制，可选更新
    is_active: Optional[bool] = Field(None, description="是否激活，可选更新")  # 是否激活，可选更新


class Agent(AgentBase):
    """
    代理响应模式，用于API返回
    包含数据库中的所有字段
    """
    id: int  # 代理唯一标识符
    api_key: str  # API密钥
    cost_limit_daily: float  # 每日成本限制，0.0表示无限制
    cost_limit_monthly: float  # 每月成本限制，0.0表示无限制
    cost_used_daily: float  # 每日已使用成本
    cost_used_monthly: float  # 每月已使用成本
    is_active: bool  # 是否激活
    is_suspended: bool  # 是否被暂停
    allowed_services: Optional[List[str]] = None  # 允许访问的服务列表
    rate_limit_per_minute: int  # 每分钟请求限制
    total_requests: int  # 总请求数
    total_cost: float  # 总成本
    last_used_at: Optional[datetime] = None  # 最后使用时间
    user_id: int  # 所属用户ID
    created_at: datetime  # 创建时间
    updated_at: Optional[datetime] = None  # 更新时间

    class Config:
        from_attributes = True  # 允许从ORM对象创建Pydantic模型


class AgentUsageBase(BaseModel):
    """
    代理使用记录基础模式
    用于记录代理的API调用信息
    """
    service_name: Optional[str] = None  # 服务名称
    request_method: Optional[str] = None  # 请求方法
    request_path: Optional[str] = None  # 请求路径
    cost: float = Field(0.0, description="本次调用成本，默认为0.0")  # 本次调用成本，默认为0.0
    tokens_used: int = Field(0, description="使用的token数，默认为0")  # 使用的token数，默认为0
    response_time_ms: Optional[int] = None  # 响应时间（毫秒）
    status_code: Optional[int] = None  # 状态码
    error_message: Optional[str] = None  # 错误信息


class AgentUsageCreate(AgentUsageBase):
    """
    代理使用记录创建模式
    用于创建新的使用记录
    """
    agent_id: int  # 代理ID


class AgentUsage(AgentUsageBase):
    """
    代理使用记录响应模式
    用于返回使用记录信息
    """
    id: int  # 使用记录唯一标识符
    agent_id: int  # 代理ID
    requested_at: datetime  # 请求时间

    class Config:
        from_attributes = True  # 允许从ORM对象创建Pydantic模型


class AgentStats(BaseModel):
    """
    代理统计信息模式
    用于返回代理的统计数据
    """
    total_requests: int  # 总请求数
    total_cost: float  # 总成本
    daily_requests: int  # 每日请求数
    daily_cost: float  # 每日成本
    monthly_requests: int  # 每月请求数
    monthly_cost: float  # 每月成本
    success_rate: float  # 成功率
    avg_response_time: float  # 平均响应时间
    last_24h_requests: List[dict]  # 过去24小时请求分布
    cost_trend: List[dict]  # 成本趋势


class AgentMonitoring(BaseModel):
    """
    代理监控信息模式
    用于返回代理的完整监控数据
    """
    agent: Agent  # 代理信息
    stats: AgentStats  # 统计信息
    recent_usage: List[AgentUsage]  # 最近使用记录
    alerts: List[dict]  # 告警信息 