#
# AgentDNS应用主入口文件
# 此文件负责初始化FastAPI应用、配置中间件、注册路由等核心功能
# 该文件是整个API服务的入口点，负责整合所有API模块
#

from fastapi import FastAPI, HTTPException  # FastAPI框架核心类，用于创建Web应用
from fastapi.middleware.cors import CORSMiddleware  # CORS中间件，处理跨域资源共享
from contextlib import asynccontextmanager  # 异步上下文管理器，用于管理应用生命周期

# 导入项目配置和数据库相关组件
from .core.config import settings  # 项目配置类，包含所有环境变量和配置参数
from .database import engine, Base  # 数据库引擎和基础模型类

# 导入主要API模块
from .api import auth, discovery, agents  # 认证、服务发现、代理管理API模块
from .api.organizations import router as organizations_router  # 组织管理路由
from .api.services import router as services_router  # 服务管理路由
from .api.proxy import router as proxy_router  # 服务代理路由
from .api.billing import router as billing_router  # 计费管理路由
from .api.reviews import router as reviews_router  # 服务评价路由

# 导入客户端API路由
from .api.client import auth as client_auth  # 客户端认证路由
from .api.client import discovery as client_discovery  # 客户端服务发现路由
from .api.client import services as client_services  # 客户端服务调用路由
from .api.client import account as client_account  # 客户端账户管理路由

# 导入客户端仪表板API路由
from .api.client import dashboard as client_dashboard  # 客户端仪表板概览路由
from .api.client import api_keys as client_api_keys  # 客户端API密钥管理路由
from .api.client import billing as client_billing  # 客户端计费管理路由
from .api.client import logs as client_logs  # 客户端使用日志路由
from .api.client import profile as client_profile  # 客户端用户资料路由
from .api.client import user_services as client_user_services  # 客户端用户服务路由
from .api.client import notifications as client_notifications  # 客户端通知路由

# 导入公共API路由（无需身份验证）
from .api import public as public_api  # 公共API模块，提供无需身份验证的服务接口


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理器
    在应用启动时创建数据库表，在应用关闭时执行清理操作
    这个函数在应用启动时自动执行，用于初始化数据库表结构
    """
    # 启动时创建数据库表 - 自动创建所有未存在的数据库表
    Base.metadata.create_all(bind=engine)
    yield
    # 关闭时清理资源 - 在应用关闭时执行清理操作
    # 在这里可以添加清理资源的代码，如关闭数据库连接等


# 创建FastAPI应用实例
app = FastAPI(
    title=settings.PROJECT_NAME,  # 项目标题
    version=settings.VERSION,      # 项目版本
    description="AgentDNS - 为LLM代理设计的根域命名和服务发现系统",  # 项目描述
    lifespan=lifespan,             # 应用生命周期管理器
    redirect_slashes=False         # 禁用自动斜杠重定向
)

# 配置CORS（跨域资源共享）中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # 允许所有来源访问
    allow_credentials=True,   # 允许携带凭据
    allow_methods=["*"],      # 允许所有HTTP方法
    allow_headers=["*"],      # 允许所有请求头
)

# 注册认证相关的路由
app.include_router(
    auth.router,
    prefix=f"{settings.API_V1_STR}/auth",  # 路由前缀
    tags=["Auth"]                         # 标签用于API文档分组
)

# 注册组织管理相关的路由
app.include_router(
    organizations_router,
    prefix=f"{settings.API_V1_STR}/organizations",
    tags=["Organization Management"]
)

# 注册服务管理相关的路由
app.include_router(
    services_router,
    prefix=f"{settings.API_V1_STR}/services",
    tags=["Service Management"]
)

# 注册代理管理相关的路由
app.include_router(
    agents.router,
    prefix=f"{settings.API_V1_STR}/agents",
    tags=["Agent Management"],
    responses={404: {"description": "Not found"}}  # 自定义响应
)

# 注册服务发现相关的路由
app.include_router(
    discovery.router,
    prefix=f"{settings.API_V1_STR}/discovery",
    tags=["Service Discovery"]
)

# 注册服务代理相关的路由
app.include_router(
    proxy_router,
    prefix=f"{settings.API_V1_STR}/proxy",
    tags=["Service Proxy"]
)

# 注册计费管理相关的路由
app.include_router(
    billing_router,
    prefix=f"{settings.API_V1_STR}/billing",
    tags=["Billing Management"]
)

# 注册服务评价相关的路由
app.include_router(
    reviews_router,
    prefix=f"{settings.API_V1_STR}/reviews",
    tags=["Service Reviews"]
)

# === 客户端API路由 ===
# 客户端认证路由
app.include_router(
    client_auth.router,
    prefix=f"{settings.API_V1_STR}/client/auth",
    tags=["Client - Auth"]
)

# 客户端服务发现路由
app.include_router(
    client_discovery.router,
    prefix=f"{settings.API_V1_STR}/client/discovery",
    tags=["Client - Discovery"]
)

# 客户端服务调用路由
app.include_router(
    client_services.router,
    prefix=f"{settings.API_V1_STR}/client/services",
    tags=["Client - Service Invocation"]
)

# 客户端账户管理路由
app.include_router(
    client_account.router,
    prefix=f"{settings.API_V1_STR}/client/account",
    tags=["Client - Account Management"]
)

# === 客户端仪表板API路由 ===
# 客户端仪表板概览路由
app.include_router(
    client_dashboard.router,
    prefix=f"{settings.API_V1_STR}/client/dashboard",
    tags=["Client - Dashboard Overview"]
)

# 客户端API密钥管理路由
app.include_router(
    client_api_keys.router,
    prefix=f"{settings.API_V1_STR}/client/api-keys",
    tags=["Client - API Key Management"]
)

# 客户端计费管理路由
app.include_router(
    client_billing.router,
    prefix=f"{settings.API_V1_STR}/client/billing",
    tags=["Client - Billing Management"]
)

# 客户端使用日志路由
app.include_router(
    client_logs.router,
    prefix=f"{settings.API_V1_STR}/client/logs",
    tags=["Client - Usage Logs"]
)

# 客户端用户资料路由
app.include_router(
    client_profile.router,
    prefix=f"{settings.API_V1_STR}/client/profile",
    tags=["Client - User Profile"]
)

# 客户端用户服务路由
app.include_router(
    client_user_services.router,
    prefix=f"{settings.API_V1_STR}/client/user-services",
    tags=["Client - User Services"]
)

# 客户端通知路由
app.include_router(
    client_notifications.router,
    prefix=f"{settings.API_V1_STR}/client/notifications",
    tags=["Client - Notifications"]
)

# === 公共API路由（无需身份验证）===
app.include_router(
    public_api.router,
    prefix=f"{settings.API_V1_STR}/public",  # 公共API的URL前缀
    tags=["Public"]  # API文档中的标签名称
)


@app.get("/")
def root():
    """
    根路径路由 - 当访问API根路径时返回的基本信息
    返回欢迎信息和API版本，用于确认API服务正常运行
    """
    return {
        "message": "Welcome to the AgentDNS API",  # 欢迎信息
        "version": settings.VERSION,  # 当前API版本号
        "docs": "/docs"  # API文档路径 - 提供API文档的访问链接
    }


@app.get("/health")
async def health_check():
    """
    健康检查路由 - 用于检查服务是否正常运行
    通常被负载均衡器或监控系统调用，确认服务状态
    """
    return {"status": "healthy", "service": "AgentDNS API"}


if __name__ == "__main__":
    # 当作为主程序运行时，使用uvicorn启动服务器 - 用于本地开发运行
    import uvicorn
    uvicorn.run(
        "app.main:app",  # 模块路径和应用实例名 - 指定要运行的FastAPI应用
        host="0.0.0.0",  # 监听所有网络接口 - 使服务可以从外部访问
        port=8000,         # 监听端口 - API服务监听的端口号
        reload=settings.DEBUG  # 开发模式下启用热重载 - 代码更改时自动重启服务
    )