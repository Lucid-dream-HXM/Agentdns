from sqlalchemy import create_engine  # SQLAlchemy数据库引擎，用于创建数据库连接
from sqlalchemy.ext.declarative import declarative_base  # SQLAlchemy声明式基类，用于定义模型
from sqlalchemy.orm import sessionmaker  # SQLAlchemy会话生成器，用于创建数据库会话
import redis  # Redis客户端库，用于缓存和会话存储
from .core.config import settings  # 项目配置，包含数据库连接信息

# 数据库连接引擎 - 根据DATABASE_URL自动选择数据库类型
engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {})
# 数据库会话生成器 - 用于创建数据库会话，autocommit=False表示手动提交，autoflush=False表示手动刷新
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# SQLAlchemy声明式基类 - 所有数据库模型的父类
Base = declarative_base()

# Redis连接客户端 - 用于缓存、会话存储等非结构化数据操作
try:
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
except:
    redis_client = None


def get_db():
    """
    获取数据库会话的依赖函数
    用于FastAPI依赖注入，为每个请求提供数据库会话
    """
    # 创建数据库会话实例
    db = SessionLocal()
    try:
        # 生成会话供使用
        yield db
    finally:
        # 确保会话关闭，释放连接
        db.close()


def get_redis():
    """
    获取Redis客户端的函数
    返回全局Redis客户端实例，用于缓存和会话操作
    """
    return redis_client 