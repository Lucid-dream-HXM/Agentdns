"""
计费API - 用于管理用户的计费和账单
提供余额查询、充值、账单历史、使用历史等功能
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, timedelta

from ..database import get_db
from ..models.user import User
from ..models.billing import Billing
from ..models.usage import Usage
from ..schemas.billing import Billing as BillingSchema, BillingCreate
from ..schemas.usage import Usage as UsageSchema
from .deps import get_current_active_user
from ..services.billing_service import BillingService

router = APIRouter()


@router.get("/balance")
def get_balance(
    current_user: User = Depends(get_current_active_user)
):
    """
    获取用户余额
    
    返回当前用户的账户余额
    
    Args:
        current_user: 当前活跃用户
    
    Returns:
        dict: 包含余额和货币类型的字典
    """
    return {
        "balance": current_user.balance,
        "currency": "USD"
    }


@router.post("/topup")
def topup_balance(
    billing_data: BillingCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    充值账户余额
    
    为用户账户充值，创建充值记录
    
    Args:
        billing_data: 充值数据，包含金额、支付方式等
        current_user: 当前活跃用户
        db: 数据库会话
    
    Returns:
        dict: 充值结果，包含消息、账单记录和新余额
    
    Raises:
        HTTPException: 当bill_type不是'topup'或金额小于等于0时抛出
    """
    if billing_data.bill_type != "topup":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="bill_type必须为'topup'"
        )
    
    if billing_data.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="金额必须大于0"
        )
    
    billing_service = BillingService(db)
    
    try:
        # 模拟支付处理
        # 在生产环境中，这里会调用支付网关
        billing_record = billing_service.topup_user(
            user=current_user,
            amount=billing_data.amount,
            payment_method=billing_data.payment_method,
            transaction_id=f"txn_{datetime.utcnow().timestamp()}"
        )
        
        return {
            "message": "充值成功",
            "billing_record": billing_record,
            "new_balance": current_user.balance
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"充值失败: {str(e)}"
        )


@router.get("/history", response_model=List[BillingSchema])
def get_billing_history(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 50,
    bill_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """
    获取账单历史
    
    查询用户的账单记录，支持按账单类型和时间范围过滤
    
    Args:
        current_user: 当前活跃用户
        db: 数据库会话
        skip: 跳过的记录数（用于分页）
        limit: 返回的最大记录数（用于分页）
        bill_type: 账单类型过滤
        start_date: 开始日期
        end_date: 结束日期
    
    Returns:
        List[BillingSchema]: 账单记录列表
    """
    query = db.query(Billing).filter(Billing.user_id == current_user.id)
    
    if bill_type:
        query = query.filter(Billing.bill_type == bill_type)
    
    if start_date:
        query = query.filter(Billing.created_at >= start_date)
    
    if end_date:
        query = query.filter(Billing.created_at <= end_date)
    
    bills = query.order_by(Billing.created_at.desc()).offset(skip).limit(limit).all()
    
    return bills


@router.get("/usage", response_model=List[UsageSchema])
def get_usage_history(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 50,
    service_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """
    获取使用历史
    
    查询用户的服务使用记录，支持按服务ID和时间范围过滤
    
    Args:
        current_user: 当前活跃用户
        db: 数据库会话
        skip: 跳过的记录数（用于分页）
        limit: 返回的最大记录数（用于分页）
        service_id: 服务ID过滤
        start_date: 开始日期
        end_date: 结束日期
    
    Returns:
        List[UsageSchema]: 使用记录列表
    """
    query = db.query(Usage).filter(Usage.user_id == current_user.id)
    
    if service_id:
        query = query.filter(Usage.service_id == service_id)
    
    if start_date:
        query = query.filter(Usage.started_at >= start_date)
    
    if end_date:
        query = query.filter(Usage.started_at <= end_date)
    
    usage_records = query.order_by(Usage.started_at.desc()).offset(skip).limit(limit).all()
    
    # 确保正确转换为Pydantic模型
    return [UsageSchema.model_validate(record) for record in usage_records]


@router.get("/stats")
def get_billing_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365)
):
    """
    获取账单统计信息
    
    查询用户在指定天数内的账单统计信息，包括总支出、总充值、总请求数等
    
    Args:
        current_user: 当前活跃用户
        db: 数据库会话
        days: 查询天数，默认30天，范围1-365天
    
    Returns:
        dict: 账单统计信息
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # 总支出
    total_spent = db.query(
        func.sum(Billing.amount)
    ).filter(
        Billing.user_id == current_user.id,
        Billing.bill_type == "charge",
        Billing.created_at >= start_date
    ).scalar() or 0
    
    # 总充值
    total_topup = db.query(
        func.sum(Billing.amount)
    ).filter(
        Billing.user_id == current_user.id,
        Billing.bill_type == "topup",
        Billing.created_at >= start_date
    ).scalar() or 0
    
    # 总请求数
    total_requests = db.query(
        func.count(Usage.id)
    ).filter(
        Usage.user_id == current_user.id,
        Usage.started_at >= start_date
    ).scalar() or 0
    
    # 按服务分组的支出
    service_spending = db.query(
        Usage.service_id,
        func.sum(Usage.cost_amount).label("total_cost"),
        func.count(Usage.id).label("request_count")
    ).filter(
        Usage.user_id == current_user.id,
        Usage.started_at >= start_date
    ).group_by(Usage.service_id).all()
    
    return {
        "period_days": days,
        "current_balance": current_user.balance,
        "total_spent": float(total_spent),
        "total_topup": float(total_topup),
        "total_requests": total_requests,
        "service_spending": [
            {
                "service_id": item.service_id,
                "total_cost": float(item.total_cost),
                "request_count": item.request_count
            }
            for item in service_spending
        ]
    }


@router.post("/refund/{bill_id}")
def request_refund(
    bill_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    请求退款
    
    为指定的账单请求退款
    
    Args:
        bill_id: 账单ID
        current_user: 当前活跃用户
        db: 数据库会话
    
    Returns:
        dict: 退款结果，包含消息、退款记录和新余额
    
    Raises:
        HTTPException: 当账单未找到、不可退款或已经退款时抛出
    """
    # 查找原始账单
    original_bill = db.query(Billing).filter(
        Billing.bill_id == bill_id,
        Billing.user_id == current_user.id,
        Billing.bill_type == "charge"
    ).first()
    
    if not original_bill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="账单未找到或不可退款"
        )
    
    # 检查是否已经退款
    existing_refund = db.query(Billing).filter(
        Billing.user_id == current_user.id,
        Billing.bill_type == "refund",
        Billing.billing_metadata.contains(f"original_bill_id:{bill_id}")
    ).first()
    
    if existing_refund:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="此账单已经退款"
        )
    
    billing_service = BillingService(db)
    
    try:
        refund_record = billing_service.refund_user(
            user=current_user,
            amount=original_bill.amount,
            description=f"退款: {original_bill.description}",
            original_bill_id=bill_id
        )
        
        return {
            "message": "退款成功",
            "refund_record": refund_record,
            "new_balance": current_user.balance
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"退款失败: {str(e)}"
        )