"""
客户端账户API - 用于客户前端
提供账户余额管理、充值、使用历史查询等功能
"""

import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field
from typing import Optional, List

from ...database import get_db
from ...models.user import User
from ...models.billing import Billing
from ...models.usage import Usage
from ...models.service import Service
from ...api.deps import get_current_client_user

logger = logging.getLogger(__name__)

router = APIRouter()


class TopupRequest(BaseModel):
    """
    充值请求
    
    包含充值金额和支付方式
    """
    amount: float = Field(..., gt=0, description="充值金额，必须大于0")
    payment_method: str = Field(..., description="支付方式")


class UsageRecord(BaseModel):
    """
    使用记录
    
    包含服务使用的详细信息
    """
    id: int
    service_name: str
    agentdns_uri: str
    cost: float
    currency: str
    tokens_used: int
    request_method: str
    created_at: str


class BillingRecord(BaseModel):
    """
    账单记录
    
    包含账单的详细信息
    """
    id: int
    bill_type: str
    amount: float
    currency: str
    description: str
    status: str
    created_at: str


class UsageStats(BaseModel):
    """
    使用统计信息
    
    包含用户使用服务的统计数据
    """
    total_requests: int
    total_cost: float
    total_tokens: int
    period_days: int
    top_services: List[dict]


@router.get("/balance")
async def get_balance(
    current_user: User = Depends(get_current_client_user),
):
    """
    获取账户余额
    
    返回当前用户的账户余额
    
    Args:
        current_user: 当前客户端用户
    
    Returns:
        包含余额的字典
    """
    logger.info(f"客户端用户 {current_user.id} 查询余额")
    
    try:
        return {
            "balance": current_user.balance,
            "currency": "CNY"
        }
    except Exception as e:
        logger.error(f"获取余额失败: {e}")
        raise HTTPException(500, f"获取余额失败: {str(e)}")


@router.post("/topup")
async def topup_balance(
    topup_request: TopupRequest,
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """
    充值账户
    
    为用户账户充值，创建充值记录
    
    Args:
        topup_request: 充值请求数据
        current_user: 当前客户端用户
        db: 数据库会话
    
    Returns:
        充值结果
    
    Raises:
        HTTPException: 如果充值失败
    """
    logger.info(f"客户端用户 {current_user.id} 充值: {topup_request.amount}")
    
    try:
        # 创建充值记录
        billing_record = Billing(
            user_id=current_user.id,
            bill_type="topup",
            amount=topup_request.amount,
            currency="CNY",
            description=f"账户充值 {topup_request.amount} CNY",
            status="completed",
            payment_method=topup_request.payment_method
        )
        
        # 更新用户余额
        current_user.balance += topup_request.amount
        
        # 保存到数据库
        db.add(billing_record)
        db.commit()
        db.refresh(current_user)
        
        logger.info(f"充值成功，用户 {current_user.id} 余额: {current_user.balance}")
        
        return {
            "success": True,
            "message": "充值成功",
            "amount": topup_request.amount,
            "new_balance": current_user.balance,
            "transaction_id": billing_record.id
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"充值失败: {e}")
        raise HTTPException(500, f"充值失败: {str(e)}")


@router.get("/usage", response_model=List[UsageRecord])
async def get_usage_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service_name: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """
    获取使用历史
    
    查询用户的服务使用记录，支持按服务名称和时间范围过滤
    
    Args:
        limit: 返回记录数量限制
        offset: 分页偏移量
        service_name: 服务名称过滤
        start_date: 开始日期
        end_date: 结束日期
        current_user: 当前客户端用户
        db: 数据库会话
    
    Returns:
        使用记录列表
    
    Raises:
        HTTPException: 如果查询失败
    """
    logger.info(f"客户端用户 {current_user.id} 查询使用历史")
    
    try:
        # 构建查询
        query = db.query(Usage).filter(Usage.user_id == current_user.id)
        
        # 按服务名称过滤
        if service_name:
            query = query.join(Usage.service).filter(
                func.lower(Service.name).contains(service_name.lower())
            )
        
        # 按时间范围过滤
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.filter(Usage.created_at >= start_dt)
        
        if end_date:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.filter(Usage.created_at <= end_dt)
        
        # 排序和分页
        usage_records = query.order_by(Usage.created_at.desc()).offset(offset).limit(limit).all()
        
        # 转换为响应
        results = []
        for record in usage_records:
            results.append(UsageRecord(
                id=record.id,
                service_name=record.service.name if record.service else "Unknown",
                agentdns_uri=record.service.agentdns_uri if record.service else "",
                cost=record.cost_amount or 0.0,
                currency=record.cost_currency or "CNY",
                tokens_used=record.tokens_used or 0,
                request_method=record.method or "POST",
                created_at=record.created_at.isoformat() if record.created_at else ""
            ))
        
        logger.info(f"返回 {len(results)} 条使用记录")
        return results
        
    except Exception as e:
        logger.error(f"获取使用历史失败: {e}")
        raise HTTPException(500, f"获取使用历史失败: {str(e)}")


@router.get("/billing", response_model=List[BillingRecord])
async def get_billing_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    bill_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """
    获取账单历史
    
    查询用户的账单记录，支持按账单类型过滤
    
    Args:
        limit: 返回记录数量限制
        offset: 分页偏移量
        bill_type: 账单类型过滤
        current_user: 当前客户端用户
        db: 数据库会话
    
    Returns:
        账单记录列表
    
    Raises:
        HTTPException: 如果查询失败
    """
    logger.info(f"客户端用户 {current_user.id} 查询账单历史")
    
    try:
        # 构建查询
        query = db.query(Billing).filter(Billing.user_id == current_user.id)
        
        # 按账单类型过滤
        if bill_type:
            query = query.filter(Billing.bill_type == bill_type)
        
        # 排序和分页
        billing_records = query.order_by(Billing.created_at.desc()).offset(offset).limit(limit).all()
        
        # 转换为响应
        results = []
        for record in billing_records:
            results.append(BillingRecord(
                id=record.id,
                bill_type=record.bill_type,
                amount=record.amount,
                currency=record.currency or "CNY",
                description=record.description or "",
                status=record.status,
                created_at=record.created_at.isoformat() if record.created_at else ""
            ))
        
        logger.info(f"返回 {len(results)} 条账单记录")
        return results
        
    except Exception as e:
        logger.error(f"获取账单历史失败: {e}")
        raise HTTPException(500, f"获取账单历史失败: {str(e)}")


@router.get("/stats", response_model=UsageStats)
async def get_usage_stats(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """
    获取使用统计信息
    
    查询用户在指定天数内的服务使用统计数据
    
    Args:
        days: 查询天数
        current_user: 当前客户端用户
        db: 数据库会话
    
    Returns:
        使用统计信息
    
    Raises:
        HTTPException: 如果查询失败
    """
    logger.info(f"客户端用户 {current_user.id} 查询使用统计")
    
    try:
        # 时间范围
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # 查询时间范围内的记录
        usage_query = db.query(Usage).filter(
            Usage.user_id == current_user.id,
            Usage.created_at >= start_date,
            Usage.created_at <= end_date
        )
        
        # 统计总数
        total_requests = usage_query.count()
        total_cost = usage_query.with_entities(func.sum(Usage.cost_amount)).scalar() or 0.0
        total_tokens = usage_query.with_entities(func.sum(Usage.tokens_used)).scalar() or 0
        
        # 热门服务
        top_services_query = db.query(
            Usage.service_id,
            func.count(Usage.id).label('usage_count'),
            func.sum(Usage.cost_amount).label('total_cost')
        ).filter(
            Usage.user_id == current_user.id,
            Usage.created_at >= start_date,
            Usage.created_at <= end_date
        ).group_by(Usage.service_id).order_by(func.count(Usage.id).desc()).limit(5)
        
        top_services = []
        for service_id, usage_count, service_cost in top_services_query:
            if service_id:
                service = db.query(Service).filter(Service.id == service_id).first()
                if service:
                    top_services.append({
                        "service_name": service.name,
                        "agentdns_uri": service.agentdns_uri,
                        "usage_count": usage_count,
                        "total_cost": float(service_cost or 0.0)
                    })
        
        return UsageStats(
            total_requests=total_requests,
            total_cost=float(total_cost),
            total_tokens=int(total_tokens),
            period_days=days,
            top_services=top_services
        )
        
    except Exception as e:
        logger.error(f"获取使用统计失败: {e}")
        raise HTTPException(500, f"获取使用统计失败: {str(e)}")


@router.get("/api-keys")
async def get_api_keys(
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """
    获取用户的API密钥（用于SDK使用）
    
    查询用户的代理（API密钥）列表，返回掩码处理后的API密钥
    
    Args:
        current_user: 当前客户端用户
        db: 数据库会话
    
    Returns:
        API密钥列表
    
    Raises:
        HTTPException: 如果查询失败
    """
    logger.info(f"客户端用户 {current_user.id} 查询API密钥")
    
    try:
        # 查询用户的代理（API密钥）
        from ...models.agent import Agent
        agents = db.query(Agent).filter(
            Agent.user_id == current_user.id,
            Agent.is_active == True
        ).all()
        
        # 返回API密钥（掩码处理）
        api_keys = []
        for agent in agents:
            # 只显示API密钥的前8位和后4位
            masked_key = f"{agent.api_key[:8]}...{agent.api_key[-4:]}" if len(agent.api_key) > 12 else agent.api_key
            
            api_keys.append({
                "id": agent.id,
                "name": agent.name,
                "api_key_masked": masked_key,
                "is_active": agent.is_active,
                "cost_limit_daily": agent.cost_limit_daily,
                "cost_limit_monthly": agent.cost_limit_monthly,
                "cost_used_daily": agent.cost_used_daily,
                "cost_used_monthly": agent.cost_used_monthly,
                "total_requests": agent.total_requests,
                "total_cost": agent.total_cost,
                "last_used_at": agent.last_used_at.isoformat() if agent.last_used_at else None,
                "created_at": agent.created_at.isoformat() if agent.created_at else ""
            })
        
        logger.info(f"返回 {len(api_keys)} 个API密钥")
        return api_keys
        
    except Exception as e:
        logger.error(f"获取API密钥失败: {e}")
        raise HTTPException(500, f"获取API密钥失败: {str(e)}")


@router.post("/api-keys")
async def create_api_key(
    key_name: str,
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """
    创建新的API密钥
    
    为用户创建新的API密钥（代理），用于SDK使用
    
    Args:
        key_name: API密钥名称
        current_user: 当前客户端用户
        db: 数据库会话
    
    Returns:
        创建结果，包含新的API密钥
    
    Raises:
        HTTPException: 如果创建失败
    """
    logger.info(f"客户端用户 {current_user.id} 创建API密钥: {key_name}")
    
    try:
        from ...models.agent import Agent
        import secrets
        
        # 生成新的API密钥
        api_key = f"agent_{secrets.token_urlsafe(32)}"
        
        # 创建代理记录
        agent = Agent(
            name=key_name,
            description=f"客户端API密钥 - {key_name}",
            api_key=api_key,
            user_id=current_user.id,
            is_active=True,
            cost_limit_daily=100.0,  # 默认每日限额
            cost_limit_monthly=1000.0  # 默认每月限额
        )
        
        db.add(agent)
        db.commit()
        db.refresh(agent)
        
        logger.info(f"API密钥已创建: {agent.id}")
        
        return {
            "success": True,
            "message": "API密钥创建成功",
            "agent_id": agent.id,
            "name": agent.name,
            "api_key": api_key,  # 仅在创建时返回
            "created_at": agent.created_at.isoformat() if agent.created_at else ""
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"创建API密钥失败: {e}")
        raise HTTPException(500, f"创建API密钥失败: {str(e)}")
