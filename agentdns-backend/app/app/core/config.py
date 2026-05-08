#
# AgentDNS项目的核心配置文件
# 该文件定义了整个应用的所有配置参数，包括数据库、缓存、向量数据库、JWT认证、API等
# 配置通过Pydantic Settings管理，支持从环境变量和.env文件加载
#

from pydantic_settings import BaseSettings  # Pydantic设置基类，用于类型验证和环境变量加载
from typing import Optional  # 类型提示，表示可选值
import os  # Python标准库，用于操作系统交互


class Settings(BaseSettings):
    # 数据库配置 - PostgreSQL数据库连接信息，用于存储用户、服务、组织等结构化数据
    DATABASE_URL: str = "postgresql://agentdns:your_password_here@localhost:5432/agentdns"
    
    # 缓存配置 - Redis缓存连接信息，用于临时存储会话、令牌等高频访问数据
    REDIS_URL: str = "redis://localhost:6379"
    
    # Milvus向量数据库配置 - 用于存储服务的向量嵌入，实现语义搜索功能
    MILVUS_HOST: str = "localhost"  # Milvus服务主机地址 - 向量数据库服务器IP或域名
    MILVUS_PORT: int = 19530  # Milvus服务端口 - 向量数据库服务端口
    MILVUS_COLLECTION_NAME: str = "agentdns_services"  # Milvus中存储服务向量的集合名称 - 存储服务向量数据的集合
    MILVUS_DIMENSION: int = 2048  # doubao-embedding-vision outputs 2048-dim vectors
    
    # JWT认证配置 - 用于生成和验证用户访问令牌，确保API安全访问
    SECRET_KEY: str = "your-secret-key-here"  # JWT密钥，用于签名和验证令牌 - 必须是强密钥
    ALGORITHM: str = "HS256"  # JWT加密算法 - HS256是最常用的JWT签名算法
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # 访问令牌过期时间（分钟） - 控制令牌有效期
    
    # API配置 - API版本和项目基本信息，用于API路由和文档
    API_V1_STR: str = "/api/v1"  # API版本前缀 - 所有API端点的公共前缀
    PROJECT_NAME: str = "AgentDNS"  # 项目名称 - 在API文档中显示的项目名称
    VERSION: str = "0.1.0"  # 项目版本 - API当前版本号
    
    # 外部服务配置 - 第三方服务API密钥，用于外部服务集成
    OPENAI_API_KEY: Optional[str] = None  # OpenAI API密钥，用于向量嵌入 - 可选配置项
    
    # 安全配置 - 加密密钥，用于保护敏感数据
    ENCRYPTION_KEY: Optional[str] = None  # 加密密钥，用于加密敏感数据 - 如API密钥等
    
    # OpenAI嵌入配置（自定义配置）- 用于服务向量嵌入，实现语义匹配
    OPENAI_BASE_URL: str = "https://ark.cn-beijing.volces.com/api/v3"  # OpenAI兼容API基础URL - 向量嵌入服务地址
    OPENAI_EMBEDDING_MODEL: str = "ep-20260403194159-ld5zp"  # 接入点 ID
    OPENAI_MAX_TOKENS: int = 4096  # 最大令牌数限制 - 单次请求最大处理的文本长度
    
    # 环境配置 - 运行环境设置，控制不同环境的行为
    ENVIRONMENT: str = "development"  # 运行环境（development/production）- 决定应用行为模式
    DEBUG: bool = True  # 是否开启调试模式 - 影响日志输出和错误处理
    
    class Config:
        env_file = ".env"  # 指定环境变量文件 - 从.env文件加载环境变量


# 创建配置实例，供整个应用使用
settings = Settings()  # 实例化配置类，解析环境变量并创建全局配置对象