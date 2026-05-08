from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from decimal import Decimal
import uuid
from datetime import datetime

from ..models.service import Service
from ..models.user import User
from ..models.billing import Billing
from ..models.usage import Usage


class BillingService:
    """
    计费服务 - 处理服务使用计费、用户充值、退款等功能
    
    支持多种计费模型：按请求、按令牌、按数据传输量、订阅制
    负责计算服务使用成本、记录使用情况、管理用户余额
    """
    
    def __init__(self, db: Session):
        """
        初始化计费服务
        
        Args:
            db: 数据库会话
        """
        self.db = db

    def _generate_request_id(self) -> str:
        """
        生成短请求ID

        Returns:
            str: 16位短请求ID
        """
        return str(uuid.uuid4())[:16]

    def calculate_cost(
        self,
        service: Service,
        tokens_used: int = 0,
        requests_count: int = 1,
        data_transfer_mb: float = 0.0
    ) -> float:
        """
        计算服务使用成本
        
        根据服务的定价模型计算使用成本，支持多种计费模型
        
        Args:
            service: 服务对象
            tokens_used: 使用的令牌数，默认为0
            requests_count: 请求次数，默认为1
            data_transfer_mb: 数据传输量（MB），默认为0.0
        
        Returns:
            计算后的成本金额
        """
        if service.pricing_model == "per_request":
            return float(service.price_per_unit * requests_count)
        
        elif service.pricing_model == "per_token":
            return float(service.price_per_unit * tokens_used / 1000)  # 价格按每1k令牌计算
        
        elif service.pricing_model == "per_mb":
            return float(service.price_per_unit * data_transfer_mb)
        
        elif service.pricing_model == "subscription":
            # 订阅制：暂时返回0；应该检查订阅状态
            return 0.0
        
        else:
            return float(service.price_per_unit)
    
    def charge_user(
        self,
        user: User,
        amount: float,
        description: str,
        service_name: Optional[str] = None
    ) -> Billing:
        """
        向用户收费
        
        检查用户余额是否足够，扣除用户余额，创建收费账单记录
        
        Args:
            user: 用户对象
            amount: 收费金额
            description: 收费描述
            service_name: 服务名称，可选
        
        Returns:
            创建的账单记录
        
        Raises:
            ValueError: 如果用户余额不足
        """
        if user.balance < amount:
            raise ValueError("用户余额不足")
        
        # 扣除余额
        user.balance -= amount
        
        # 创建账单记录
        billing_record = Billing(
            user_id=user.id,
            bill_id=str(uuid.uuid4())[:16],
            bill_type="charge",
            amount=amount,
            description=description,
            service_name=service_name,
            status="completed",
            payment_method="balance"
        )
        
        self.db.add(billing_record)
        self.db.commit()
        self.db.refresh(billing_record)
        
        return billing_record
    
    def refund_user(
        self,
        user: User,
        amount: float,
        description: str,
        original_bill_id: Optional[str] = None
    ) -> Billing:
        """
        向用户退款
        
        增加用户余额，创建退款账单记录
        
        Args:
            user: 用户对象
            amount: 退款金额
            description: 退款描述
            original_bill_id: 原始账单ID，可选
        
        Returns:
            创建的退款记录
        """
        # 增加余额
        user.balance += amount
        
        # 创建退款记录
        billing_record = Billing(
            user_id=user.id,
            bill_id=str(uuid.uuid4())[:16],
            bill_type="refund",
            amount=amount,
            description=description,
            status="completed",
            payment_method="balance",
            billing_metadata=f"original_bill_id:{original_bill_id}" if original_bill_id else None
        )
        
        self.db.add(billing_record)
        self.db.commit()
        self.db.refresh(billing_record)
        
        return billing_record
    
    def topup_user(
        self,
        user: User,
        amount: float,
        payment_method: str = "credit_card",
        transaction_id: Optional[str] = None
    ) -> Billing:
        """
        为用户充值
        
        增加用户余额，创建充值账单记录
        
        Args:
            user: 用户对象
            amount: 充值金额
            payment_method: 支付方式，默认为"credit_card"
            transaction_id: 交易ID，可选
        
        Returns:
            创建的充值记录
        """
        # 增加余额
        user.balance += amount
        
        # 创建充值记录
        billing_record = Billing(
            user_id=user.id,
            bill_id=str(uuid.uuid4())[:16],
            bill_type="topup",
            amount=amount,
            description=f"账户充值 {amount} USD",
            status="completed",
            payment_method=payment_method,
            transaction_id=transaction_id
        )
        
        self.db.add(billing_record)
        self.db.commit()
        self.db.refresh(billing_record)
        
        return billing_record 
    
    def record_usage(
        self,
        user: User,
        service: Service,
        amount: float,
        tokens_used: int = 0,
        requests_count: int = 1,
        data_transfer_mb: float = 0.0,
        request_id: Optional[str] = None,
        method: str = "POST",
        execution_time_ms: Optional[int] = None,
        status_code: int = 200,
        request_metadata: Optional[dict] = None,
        agent_id: Optional[int] = None,
        http_mode: Optional[str] = None,
        final_state: str = "success",
        error_message: Optional[str] = None,
        is_meaningful: bool = True,
        create_billing_record: bool = True
    ) -> Usage:
        """
        记录一次服务使用情况

        该方法用于记录一次真实服务调用。
        第一阶段中，它既可以用于：
        1. 正常成功调用后的记录与计费
        2. 已真实进入服务执行阶段，但本次不收费的失败记录

        Args:
            user: 当前用户
            service: 被调用服务
            amount: 本次调用金额
            tokens_used: 使用的token数量
            requests_count: 请求次数
            data_transfer_mb: 数据传输量（MB）
            request_id: 请求ID，可选，不传则自动生成
            method: HTTP方法
            execution_time_ms: 执行耗时（毫秒）
            status_code: HTTP状态码
            request_metadata: 请求元数据
            agent_id: 发起调用的Agent ID，可空
            http_mode: 调用模式 sync / stream / async
            final_state: 最终状态 success / partial / fail / pending
            error_message: 错误信息
            is_meaningful: 是否真正进入服务执行阶段
            create_billing_record: 是否创建扣费账单记录

        Returns:
            Usage: 创建好的使用记录对象
        """
        if not request_id:
            request_id = self._generate_request_id()

        now = datetime.utcnow()

        billing_status = "pending"

        if create_billing_record and amount > 0:
            if user.balance < amount:
                raise ValueError("用户余额不足")

            user.balance -= amount

            billing_record = Billing(
                user_id=user.id,
                bill_id=self._generate_request_id(),
                bill_type="charge",
                amount=amount,
                currency=service.currency or "USD",
                description=f"服务调用计费: {service.name}",
                service_name=service.name,
                usage_period_start=now,
                usage_period_end=now,
                status="completed",
                payment_method="balance",
                transaction_id=f"usage_{request_id}",
                billing_metadata=f"service_id:{service.id};request_id:{request_id}",
                processed_at=now
            )
            self.db.add(billing_record)
            billing_status = "charged"

        usage_record = Usage(
            user_id=user.id,
            service_id=service.id,
            agent_id=agent_id,
            request_id=request_id,
            method=method,
            endpoint=service.endpoint_url,
            protocol=service.protocol,
            http_mode=http_mode,
            tokens_used=tokens_used,
            requests_count=requests_count,
            data_transfer_mb=data_transfer_mb,
            execution_time_ms=execution_time_ms,
            cost_amount=amount if create_billing_record else 0.0,
            cost_currency=service.currency or "USD",
            billing_status=billing_status,
            status_code=status_code,
            error_message=error_message,
            request_metadata=request_metadata or {},
            started_at=now,
            completed_at=now if final_state in ["success", "partial", "fail"] else None,
            is_meaningful=is_meaningful,
            final_state=final_state
        )

        self.db.add(usage_record)
        self.db.commit()
        self.db.refresh(usage_record)

        return usage_record

    def finalize_usage_record(
        self,
        usage_record: Usage,
        final_state: str,
        execution_time_ms: Optional[int] = None,
        status_code: Optional[int] = None,
        error_message: Optional[str] = None,
        request_metadata: Optional[Dict[str, Any]] = None,
        actual_cost: Optional[float] = None,
        charge_user: bool = False
    ) -> Usage:
        """
        完成一条Usage锚点记录

        该方法用于在服务执行结束后，补全Usage记录的最终状态、耗时、错误信息和费用。
        如果charge_user=True且actual_cost>0，则会同步生成一条扣费账单记录。

        Args:
            usage_record: 要更新的Usage记录
            final_state: 最终状态 success / partial / fail / pending
            execution_time_ms: 执行耗时
            status_code: 状态码
            error_message: 错误信息
            request_metadata: 元数据，可选
            actual_cost: 实际费用，可选
            charge_user: 是否在本次完成时执行扣费

        Returns:
            Usage: 更新后的Usage记录
        """
        now = datetime.utcnow()

        usage_record.final_state = final_state
        usage_record.execution_time_ms = execution_time_ms
        usage_record.status_code = status_code
        usage_record.error_message = error_message

        if request_metadata is not None:
            usage_record.request_metadata = request_metadata

        if final_state in ["success", "partial", "fail"]:
            usage_record.completed_at = now

        if charge_user and actual_cost is not None and actual_cost > 0:
            user = self.db.query(User).filter(User.id == usage_record.user_id).first()
            service = self.db.query(Service).filter(Service.id == usage_record.service_id).first()

            if not user or not service:
                raise ValueError("完成Usage记录时，关联用户或服务不存在")

            if user.balance < actual_cost:
                raise ValueError("用户余额不足")

            user.balance -= actual_cost

            usage_record.cost_amount = actual_cost
            usage_record.cost_currency = service.currency or "USD"
            usage_record.billing_status = "charged"

            billing_record = Billing(
                user_id=user.id,
                bill_id=self._generate_request_id(),
                bill_type="charge",
                amount=actual_cost,
                currency=service.currency or "USD",
                description=f"服务调用计费: {service.name}",
                service_name=service.name,
                usage_period_start=usage_record.started_at,
                usage_period_end=now,
                status="completed",
                payment_method="balance",
                transaction_id=f"usage_{usage_record.request_id}",
                billing_metadata=f"service_id:{service.id};request_id:{usage_record.request_id}",
                processed_at=now
            )
            self.db.add(billing_record)
        else:
            if actual_cost is not None:
                usage_record.cost_amount = actual_cost

        self.db.commit()
        self.db.refresh(usage_record)

        return usage_record

    def create_usage_anchor(
        self,
        user: User,
        service: Service,
        method: str = "POST",
        request_metadata: Optional[Dict[str, Any]] = None,
        agent_id: Optional[int] = None,
        http_mode: Optional[str] = None,
        request_id: Optional[str] = None,
        is_meaningful: bool = True,
        initial_state: str = "pending"
    ) -> Usage:
        """
        创建一条Usage锚点记录

        该方法用于在服务真正开始执行时，先落一条可追踪的Usage记录，
        后续再根据执行结果补全最终状态、耗时和费用等信息

        Args:
            user: 当前用户
            service: 被调用服务
            method: HTTP方法
            request_metadata: 请求元数据
            agent_id: 发起调用的Agent ID，可空
            http_mode: 调用模式 sync / stream / async
            request_id: 请求ID，可选，不传则自动生成
            is_meaningful: 是否真正进入服务执行阶段
            initial_state: 初始状态，默认pending

        Returns:
            Usage: 创建好的Usage锚点记录
        """
        if not request_id:
            request_id = self._generate_request_id()

        usage_record = Usage(
            user_id=user.id,
            service_id=service.id,
            agent_id=agent_id,
            request_id=request_id,
            method=method,
            endpoint=service.endpoint_url,
            protocol=service.protocol,
            http_mode=http_mode,
            tokens_used=0,
            requests_count=1,
            data_transfer_mb=0.0,
            execution_time_ms=None,
            cost_amount=0.0,
            cost_currency=service.currency or "USD",
            billing_status="pending",
            status_code=None,
            error_message=None,
            request_metadata=request_metadata or {},
            started_at=datetime.utcnow(),
            completed_at=None,
            is_meaningful=is_meaningful,
            final_state=initial_state
        )

        self.db.add(usage_record)
        self.db.commit()
        self.db.refresh(usage_record)

        return usage_record