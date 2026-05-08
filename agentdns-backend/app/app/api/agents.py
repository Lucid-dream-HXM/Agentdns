"""
代理API - 用于管理用户的代理实例
提供代理创建、查询、更新、删除和监控等功能
"""

from fastapi import APIRouter, Depends, HTTPException, status  # FastAPI核心组件，用于创建API路由、依赖注入和HTTP异常处理
from sqlalchemy.orm import Session  # SQLAlchemy ORM会话类型，用于数据库操作
from sqlalchemy import func, and_, extract  # SQLAlchemy查询函数，用于聚合查询和条件组合
from typing import List  # 类型提示，用于列表类型标注
import logging  # Python日志模块，用于记录系统日志
import secrets  # Python安全随机数生成模块，用于生成API密钥
from datetime import datetime, timedelta  # Python日期时间模块，用于时间计算

from ..database import get_db  # 数据库会话依赖函数，用于获取数据库会话
from ..models.user import User  # 用户模型，用于数据库操作
from ..models.agent import Agent, AgentUsage  # 代理模型和代理使用记录模型
from ..schemas.agent import (  # 代理相关的数据传输对象（DTO）
    AgentCreate,      # 代理创建请求数据结构
    AgentUpdate,      # 代理更新请求数据结构
    Agent as AgentSchema,  # 代理响应数据结构
    AgentStats,       # 代理统计信息数据结构
    AgentMonitoring,  # 代理监控信息数据结构
    AgentUsage as AgentUsageSchema  # 代理使用记录数据结构
)
from .deps import get_current_active_user  # 获取当前活跃用户的依赖函数

# 创建API路由器实例
router = APIRouter()
# 创建日志记录器
logger = logging.getLogger(__name__)


def generate_api_key() -> str:
    """
    生成API密钥
    
    使用安全的随机数生成器创建唯一的API密钥
    密钥格式为agent_前缀加上URL安全的base64编码随机字符串
    
    Returns:
        str: 生成的API密钥字符串
    """
    return f"agent_{secrets.token_urlsafe(32)}"


@router.post("", response_model=AgentSchema)
def create_agent(
    agent_data: AgentCreate,  # 代理创建请求数据
    current_user: User = Depends(get_current_active_user),  # 当前活跃用户依赖
    db: Session = Depends(get_db)  # 数据库会话依赖
):
    """
    创建新代理
    
    为当前用户创建一个新的代理实例，包括生成唯一的API密钥和其他配置参数
    
    Args:
        agent_data: 代理创建请求数据（包含代理名称、描述、成本限制等）
        current_user: 当前活跃用户对象
        db: 数据库会话对象
    
    Returns:
        AgentSchema: 创建成功的代理信息
    
    Raises:
        HTTPException: 当创建过程出现错误时抛出相应异常
    """
    # 生成API密钥
    api_key = generate_api_key()
    
    # 创建代理对象
    db_agent = Agent(
        name=agent_data.name,                           # 代理名称
        description=agent_data.description,             # 代理描述
        api_key=api_key,                                # 生成的API密钥
        cost_limit_daily=agent_data.cost_limit_daily,   # 日成本限制
        cost_limit_monthly=agent_data.cost_limit_monthly, # 月成本限制
        allowed_services=agent_data.allowed_services,   # 允许的服务列表
        rate_limit_per_minute=agent_data.rate_limit_per_minute, # 每分钟请求限制
        user_id=current_user.id                        # 所属用户ID
    )
    
    db.add(db_agent)      # 添加到数据库会话
    db.commit()           # 提交事务
    db.refresh(db_agent)  # 刷新对象以获取数据库生成的ID
    
    logger.info(f"用户 {current_user.id} 创建了代理 {db_agent.id}")  # 记录创建日志
    return db_agent


@router.get("", response_model=List[AgentSchema])
def list_agents(
    skip: int = 0,  # 跳过的记录数（用于分页）
    limit: int = 100,  # 返回的最大记录数（用于分页）
    current_user: User = Depends(get_current_active_user),  # 当前活跃用户依赖
    db: Session = Depends(get_db)  # 数据库会话依赖
):
    """
    列出用户的代理列表
    
    获取当前用户拥有的所有代理信息，支持分页功能
    
    Args:
        skip: 跳过的记录数量（分页偏移量）
        limit: 返回的最大记录数量（分页限制）
        current_user: 当前活跃用户对象
        db: 数据库会话对象
    
    Returns:
        List[AgentSchema]: 代理列表
    """
    # 查询当前用户的所有代理
    agents = db.query(Agent).filter(Agent.user_id == current_user.id).offset(skip).limit(limit).all()
    logger.info(f"用户 {current_user.id} 查看了代理列表，共 {len(agents)} 个代理")
    return agents


@router.get("/{agent_id}", response_model=AgentSchema)
def get_agent(
    agent_id: int,  # 代理ID
    current_user: User = Depends(get_current_active_user),  # 当前活跃用户依赖
    db: Session = Depends(get_db)  # 数据库会话依赖
):
    """
    获取代理详情
    
    根据代理ID获取代理的详细信息
    
    Args:
        agent_id: 代理ID
        current_user: 当前活跃用户对象
        db: 数据库会话对象
    
    Returns:
        AgentSchema: 代理详情
    
    Raises:
        HTTPException: 当代理不存在或用户无权访问时抛出
    """
    # 查询代理
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.user_id == current_user.id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="代理不存在"
        )
    logger.info(f"用户 {current_user.id} 查看了代理 {agent_id} 的详情")
    return agent


@router.put("/{agent_id}", response_model=AgentSchema)
def update_agent(
    agent_id: int,  # 代理ID
    agent_data: AgentUpdate,  # 代理更新请求数据
    current_user: User = Depends(get_current_active_user),  # 当前活跃用户依赖
    db: Session = Depends(get_db)  # 数据库会话依赖
):
    """
    更新代理信息
    
    根据代理ID更新代理的配置信息
    
    Args:
        agent_id: 代理ID
        agent_data: 代理更新请求数据
        current_user: 当前活跃用户对象
        db: 数据库会话对象
    
    Returns:
        AgentSchema: 更新后的代理信息
    
    Raises:
        HTTPException: 当代理不存在或用户无权访问时抛出
    """
    # 查询代理
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.user_id == current_user.id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="代理不存在"
        )
    
    # 更新代理信息
    update_data = agent_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(agent, key, value)
    
    db.commit()           # 提交事务
    db.refresh(agent)      # 刷新对象以获取更新后的数据
    
    logger.info(f"用户 {current_user.id} 更新了代理 {agent_id} 的信息")
    return agent


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(
    agent_id: int,  # 代理ID
    current_user: User = Depends(get_current_active_user),  # 当前活跃用户依赖
    db: Session = Depends(get_db)  # 数据库会话依赖
):
    """
    删除代理
    
    根据代理ID删除代理实例
    
    Args:
        agent_id: 代理ID
        current_user: 当前活跃用户对象
        db: 数据库会话对象
    
    Returns:
        None: 无返回值，状态码为204
    
    Raises:
        HTTPException: 当代理不存在或用户无权访问时抛出
    """
    # 查询代理
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.user_id == current_user.id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="代理不存在"
        )
    
    # 软删除：将is_active设置为False
    agent.is_active = False
    
    db.commit()  # 提交事务
    
    logger.info(f"用户 {current_user.id} 删除了代理 {agent_id}")
    return None


@router.post("/{agent_id}/reset-api-key")
def reset_api_key(
    agent_id: int,  # 代理ID
    current_user: User = Depends(get_current_active_user),  # 当前活跃用户依赖
    db: Session = Depends(get_db)  # 数据库会话依赖
):
    """
    重置代理API密钥
    
    为指定代理生成新的API密钥
    
    Args:
        agent_id: 代理ID
        current_user: 当前活跃用户对象
        db: 数据库会话对象
    
    Returns:
        dict: 包含新API密钥的字典
    
    Raises:
        HTTPException: 当代理不存在或用户无权访问时抛出
    """
    # 查询代理
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.user_id == current_user.id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="代理不存在"
        )
    
    # 生成新的API密钥
    new_api_key = generate_api_key()
    agent.api_key = new_api_key
    
    db.commit()  # 提交事务
    
    logger.info(f"用户 {current_user.id} 重置了代理 {agent_id} 的API密钥")
    return {"api_key": new_api_key}


@router.get("/{agent_id}/stats", response_model=AgentStats)
def get_agent_stats(
    agent_id: int,  # 代理ID
    current_user: User = Depends(get_current_active_user),  # 当前活跃用户依赖
    db: Session = Depends(get_db)  # 数据库会话依赖
):
    """
    获取代理统计信息
    
    获取指定代理的使用统计信息，包括总请求数、总成本、平均响应时间等
    
    Args:
        agent_id: 代理ID
        current_user: 当前活跃用户对象
        db: 数据库会话对象
    
    Returns:
        AgentStats: 代理统计信息
    
    Raises:
        HTTPException: 当代理不存在或用户无权访问时抛出
    """
    # 查询代理
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.user_id == current_user.id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="代理不存在"
        )
    
    # 计算统计信息
    total_requests = agent.total_requests
    total_cost = agent.total_cost
    
    # 计算今日使用情况
    today = datetime.utcnow().date()
    today_usage = db.query(func.sum(AgentUsage.cost)).filter(
        AgentUsage.agent_id == agent_id,
        func.date(AgentUsage.created_at) == today
    ).scalar() or 0
    
    # 计算本月使用情况
    current_month = datetime.utcnow().month
    current_year = datetime.utcnow().year
    monthly_usage = db.query(func.sum(AgentUsage.cost)).filter(
        AgentUsage.agent_id == agent_id,
        extract('month', AgentUsage.created_at) == current_month,
        extract('year', AgentUsage.created_at) == current_year
    ).scalar() or 0
    
    # 计算平均响应时间
    avg_response_time = db.query(func.avg(AgentUsage.response_time_ms)).filter(
        AgentUsage.agent_id == agent_id
    ).scalar() or 0
    
    # 构建响应
    stats = AgentStats(
        agent_id=agent_id,
        total_requests=total_requests,
        total_cost=float(total_cost),
        today_usage=float(today_usage),
        monthly_usage=float(monthly_usage),
        avg_response_time=float(avg_response_time),
        cost_limit_daily=agent.cost_limit_daily,
        cost_limit_monthly=agent.cost_limit_monthly
    )
    
    logger.info(f"用户 {current_user.id} 查看了代理 {agent_id} 的统计信息")
    return stats


@router.get("/{agent_id}/monitoring", response_model=AgentMonitoring)
def get_agent_monitoring(
    agent_id: int,  # 代理ID
    days: int = 7,  # 查询天数
    current_user: User = Depends(get_current_active_user),  # 当前活跃用户依赖
    db: Session = Depends(get_db)  # 数据库会话依赖
):
    """
    获取代理监控信息
    
    获取指定代理在过去几天的使用情况，包括请求量、成本和错误率
    
    Args:
        agent_id: 代理ID
        days: 查询天数，默认为7天
        current_user: 当前活跃用户对象
        db: 数据库会话对象
    
    Returns:
        AgentMonitoring: 代理监控信息
    
    Raises:
        HTTPException: 当代理不存在或用户无权访问时抛出
    """
    # 查询代理
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.user_id == current_user.id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="代理不存在"
        )
    
    # 计算时间范围
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # 查询使用记录
    usage_records = db.query(
        func.date(AgentUsage.created_at).label('date'),
        func.count(AgentUsage.id).label('request_count'),
        func.sum(AgentUsage.cost).label('total_cost'),
        func.count(and_(AgentUsage.status_code >= 400, AgentUsage.status_code < 600)).label('error_count')
    ).filter(
        AgentUsage.agent_id == agent_id,
        AgentUsage.created_at >= start_date,
        AgentUsage.created_at <= end_date
    ).group_by(func.date(AgentUsage.created_at)).order_by(func.date(AgentUsage.created_at)).all()
    
    # 构建响应
    daily_stats = []
    for record in usage_records:
        error_rate = (record.error_count / record.request_count) * 100 if record.request_count > 0 else 0
        daily_stats.append({
            "date": record.date.isoformat(),
            "request_count": record.request_count,
            "total_cost": float(record.total_cost or 0),
            "error_rate": round(error_rate, 2)
        })
    
    # 计算总体统计
    total_requests = sum(stat["request_count"] for stat in daily_stats)
    total_cost = sum(stat["total_cost"] for stat in daily_stats)
    total_errors = sum(stat["request_count"] * (stat["error_rate"] / 100) for stat in daily_stats)
    overall_error_rate = (total_errors / total_requests) * 100 if total_requests > 0 else 0
    
    monitoring = AgentMonitoring(
        agent_id=agent_id,
        days=days,
        total_requests=total_requests,
        total_cost=float(total_cost),
        overall_error_rate=round(overall_error_rate, 2),
        daily_stats=daily_stats
    )
    
    logger.info(f"用户 {current_user.id} 查看了代理 {agent_id} 的监控信息")
    return monitoring


@router.get("/{agent_id}/usage", response_model=List[AgentUsageSchema])
def get_agent_usage(
    agent_id: int,  # 代理ID
    skip: int = 0,  # 跳过的记录数（用于分页）
    limit: int = 100,  # 返回的最大记录数（用于分页）
    current_user: User = Depends(get_current_active_user),  # 当前活跃用户依赖
    db: Session = Depends(get_db)  # 数据库会话依赖
):
    """
    获取代理使用记录
    
    获取指定代理的使用记录，支持分页功能
    
    Args:
        agent_id: 代理ID
        skip: 跳过的记录数量（分页偏移量）
        limit: 返回的最大记录数量（分页限制）
        current_user: 当前活跃用户对象
        db: 数据库会话对象
    
    Returns:
        List[AgentUsageSchema]: 代理使用记录列表
    
    Raises:
        HTTPException: 当代理不存在或用户无权访问时抛出
    """
    # 查询代理
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.user_id == current_user.id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="代理不存在"
        )
    
    # 查询使用记录
    usage_records = db.query(AgentUsage).filter(
        AgentUsage.agent_id == agent_id
    ).order_by(AgentUsage.created_at.desc()).offset(skip).limit(limit).all()
    
    logger.info(f"用户 {current_user.id} 查看了代理 {agent_id} 的使用记录，共 {len(usage_records)} 条")
    return usage_records