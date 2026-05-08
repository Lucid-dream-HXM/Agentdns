from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime


class ServiceBase(BaseModel):
    """
    服务基础模式，包含服务的基本信息
    作为其他服务模式的基类，提供公共字段定义
    """
    name: str = Field(..., min_length=1, max_length=100, description="服务名称，必填字段，最大100字符")  # 服务名称，必填字段，最大100字符
    category: Optional[str] = Field(None, max_length=50, description="服务分类，如search、chat等，最大50字符")  # 服务分类，可选字段，最大50字符（分类示例： search （搜索）、 chat （对话）、 image （图像处理）、 data （数据处理）等）
    description: Optional[str] = Field(None, description="服务描述，可选字段")  # 服务描述，可选字段
    version: str = Field("1.0.0", description="服务版本，默认为1.0.0")  # 服务版本，默认为1.0.0
    is_public: bool = Field(True, description="服务是否公开，默认为True")  # 服务是否公开，默认为True


class ServiceCreate(ServiceBase):
    """
    服务创建模式，用于创建新服务
    继承ServiceBase，添加服务配置字段
    """
    endpoint_url: str = Field(..., max_length=500, description="实际端点URL，必填字段，最大500字符")  # 实际端点URL（服务提供商的真实API地址），必填字段，最大500字符
    protocol: str = Field("MCP", description="协议类型：MCP、A2A、ANP、HTTP，默认为MCP")  # 协议类型，默认为MCP
    authentication_required: bool = Field(True, description="是否需要身份验证，默认为True")  # 是否需要身份验证，默认为True
    pricing_model: str = Field("per_request", description="定价模型：per_request、per_token、subscription，默认为per_request")  # 定价模型，默认为per_request
    price_per_unit: float = Field(0.0, ge=0, description="单位价格，默认为0.0")  # 单位价格，默认为0.0，必须大于等于0
    currency: str = Field("CNY", max_length=3, description="货币类型，默认为CNY")  # 货币类型，默认为CNY
    tags: Optional[List[str]] = Field([], description="服务标签列表，默认为空列表")  # 服务标签（相比分类更细粒度的关键词）列表，默认为空列表
    capabilities: Optional[Dict[str, Any]] = Field({}, description="服务功能描述，JSON格式，默认为空字典")  # 服务功能描述，JSON格式，默认为空字典
    
    # HTTP代理特有字段（为了支持将第三方HTTP API服务接入，服务创建者在创建服务时赋值）
    agentdns_path: Optional[str] = Field(None, max_length=500, description="自定义AgentDNS路径，如org/search/websearch，最大500字符")  # 自定义AgentDNS路径，可选字段，最大500字符
    http_method: Optional[str] = Field(None, max_length=10, description="HTTP方法：GET、POST等，最大10字符")  # HTTP方法，可选字段，最大10字符
    http_mode: Optional[str] = Field(None, max_length=10, description="HTTP模式：sync、stream、async，最大10字符")  # HTTP模式，可选字段，最大10字符
    input_description: Optional[str] = Field(None, description="服务输入描述，可选字段")  # 服务输入描述，可选字段
    output_description: Optional[str] = Field(None, description="服务输出描述，可选字段")  # 服务输出描述，可选字段
    service_api_key: Optional[str] = Field(None, max_length=500, description="提供商API密钥，最大500字符")  # 提供商API密钥，可选字段，最大500字符


class ServiceUpdate(BaseModel):
    """
    服务更新模式，用于更新服务信息
    所有字段都是可选的，允许部分更新
    """
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="服务名称，可选更新")  # 服务名称，可选更新
    category: Optional[str] = Field(None, max_length=50, description="服务分类，可选更新")  # 服务分类，可选更新
    description: Optional[str] = Field(None, description="服务描述，可选更新")  # 服务描述，可选更新
    version: Optional[str] = Field(None, description="服务版本，可选更新")  # 服务版本，可选更新
    is_active: Optional[bool] = Field(None, description="服务是否激活，可选更新")  # 服务是否激活，可选更新
    is_public: Optional[bool] = Field(None, description="服务是否公开，可选更新")  # 服务是否公开，可选更新
    endpoint_url: Optional[str] = Field(None, max_length=500, description="实际端点URL，可选更新")  # 实际端点URL，可选更新
    protocol: Optional[str] = Field(None, description="协议类型，可选更新")  # 协议类型，可选更新
    authentication_required: Optional[bool] = Field(None, description="是否需要身份验证，可选更新")  # 是否需要身份验证，可选更新
    pricing_model: Optional[str] = Field(None, description="定价模型，可选更新")  # 定价模型，可选更新
    price_per_unit: Optional[float] = Field(None, ge=0, description="单位价格，可选更新")  # 单位价格，可选更新，必须大于等于0
    currency: Optional[str] = Field(None, max_length=3, description="货币类型，可选更新")  # 货币类型，可选更新
    tags: Optional[List[str]] = Field(None, description="服务标签列表，可选更新")  # 服务标签列表，可选更新
    capabilities: Optional[Dict[str, Any]] = Field(None, description="服务功能描述，可选更新")  # 服务功能描述，可选更新
    
    # HTTP代理特有字段
    agentdns_path: Optional[str] = Field(None, max_length=500, description="自定义AgentDNS路径，可选更新")  # 自定义AgentDNS路径，可选更新
    http_method: Optional[str] = Field(None, max_length=10, description="HTTP方法，可选更新")  # HTTP方法，可选更新
    http_mode: Optional[str] = Field(None, max_length=10, description="HTTP模式，可选更新")  # HTTP模式，可选更新
    input_description: Optional[str] = Field(None, description="服务输入描述，可选更新")  # 服务输入描述，可选更新
    output_description: Optional[str] = Field(None, description="服务输出描述，可选更新")  # 服务输出描述，可选更新
    service_api_key: Optional[str] = Field(None, max_length=500, description="提供商API密钥，可选更新")  # 提供商API密钥，可选更新


class Service(ServiceBase):
    """
    服务响应模式，用于API返回
    包含数据库中的所有字段
    """
    id: int  # 服务唯一标识符
    agentdns_uri: str  # AgentDNS URI，格式为agentdns://org/category/name
    is_active: bool  # 服务是否激活
    protocol: str  # 协议类型：MCP、A2A、ANP、HTTP
    authentication_required: bool  # 是否需要身份验证
    pricing_model: str  # 定价模型：per_request、per_token、subscription
    price_per_unit: float  # 单位价格
    currency: str  # 货币类型
    tags: List[str]  # 服务标签列表
    capabilities: Dict[str, Any]  # 服务功能描述
    organization_id: int  # 所属组织ID
    created_at: datetime  # 创建时间
    updated_at: Optional[datetime] = None  # 更新时间
    
    # HTTP代理字段
    agentdns_path: Optional[str] = None  # 自定义AgentDNS路径
    http_method: Optional[str] = None  # HTTP方法
    http_mode: Optional[str] = None  # HTTP模式：sync、stream、async
    input_description: Optional[str] = None  # 服务输入描述
    output_description: Optional[str] = None  # 服务输出描述

    trust_score: Optional[float] = None
    success_rate: Optional[float] = None
    rating_count: Optional[int] = None
    avg_response_time_ms: Optional[float] = None

    # 敏感字段（仅在允许时包含）
    endpoint_url: Optional[str] = None  # 实际端点URL
    service_api_key: Optional[str] = None  # 提供商API密钥
    
    class Config:
        from_attributes = True  # 允许从ORM对象创建Pydantic模型


class ServiceSearch(BaseModel):
    """
    服务搜索模式，用于服务搜索请求
    """
    query: str = Field(..., description="搜索查询字符串，必填字段")
    category: Optional[str] = Field(None, description="服务分类过滤，可选字段")
    organization: Optional[str] = Field(None, description="组织名称过滤，可选字段")
    protocol: Optional[str] = Field(None, description="协议类型过滤，可选字段")
    max_price: Optional[float] = Field(None, ge=0, description="最大价格过滤，可选字段")
    limit: int = Field(10, ge=1, le=100, description="返回结果数量限制，默认为10，范围1-100")

    sort_by: Optional[str] = "balanced"
    include_trust: Optional[bool] = True
    min_trust_score: Optional[float] = None


class ServiceDiscovery(BaseModel):
    """
    服务发现响应模式，用于返回搜索结果
    """
    services: List[Dict[str, Any]]  # 搜索引擎返回的服务列表
    total: int  # 总结果数
    query: str  # 搜索查询字符串


# SDK兼容的Tool对象结构
class ToolCost(BaseModel):
    """
    工具成本信息模式
    """
    type: str  # 成本类型：per_request、per_token、per_mb等
    price: str  # 价格字符串
    currency: str = Field("CNY", description="货币类型，默认为CNY")  # 货币类型，默认为CNY
    description: str = Field("Billed per request", description="成本描述，默认为Billed per request")  # 成本描述，默认为Billed per request


class Tool(BaseModel):
    """
    AgentDNS SDK兼容的工具对象
    """
    name: str  # 工具名称
    description: str  # 工具描述
    organization: str  # 组织名称（不是ID）
    agentdns_url: str  # AgentDNS URL，格式为agentdns://org/category/service
    cost: ToolCost  # 工具成本信息
    protocol: str = Field("MCP", description="协议类型，默认为MCP")  # 协议类型，默认为MCP
    method: str = Field("POST", description="HTTP方法，默认为POST")  # HTTP方法，默认为POST
    http_mode: Optional[str] = None  # HTTP模式：sync、stream、async
    input_description: str  # 输入描述
    output_description: str  # 输出描述

    trust_score: Optional[float] = None
    success_rate: Optional[float] = None
    rating_count: Optional[int] = None
    avg_response_time_ms: Optional[float] = None


class ToolsListResponse(BaseModel):
    """
    SDK兼容的工具列表响应模式
    """
    tools: List[Tool]  # 工具列表
    total: int  # 总工具数
    query: str  # 搜索查询字符串


# 内部完整服务信息（包含敏感字段）
class ServiceInternal(Service):
    """
    内部服务模式，包含敏感字段（不对外暴露）
    """
    endpoint_url: str  # 实际端点URL
    service_api_key_encrypted: Optional[str] = Field(None, alias="service_api_key")  # 加密的提供商API密钥
    
    class Config:
        from_attributes = True  # 允许从ORM对象创建Pydantic模型


# 保留HttpAgentServiceInfo供未来使用
class HttpAgentServiceInfo(BaseModel):
    """
    HTTP代理服务发现响应格式
    """
    name: str  # 服务名称
    description: Optional[str] = None  # 服务描述
    organization: str  # 组织名称
    agentdns: str  # AgentDNS路径
    method: str  # HTTP方法
    input_description: Optional[str] = None  # 输入描述
    output_description: Optional[str] = None  # 输出描述