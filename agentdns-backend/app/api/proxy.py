"""
代理API - 用于处理服务代理转发
提供统一代理入口，支持同步、流式和异步三种HTTP模式
"""

import json
import uuid
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any
from urllib.parse import urlparse, urlunparse

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
import httpx

from ..database import get_db
from ..models.user import User
from ..models.service import Service
from ..models.usage import Usage
from ..models.async_task import AsyncTask
from ..models.organization import Organization
from ..models.agent import Agent
from ..services.billing_service import BillingService
from .deps import get_current_principal

logger = logging.getLogger(__name__)
router = APIRouter()


def normalize_endpoint_url(endpoint_url: str) -> str:
    if not endpoint_url:
        return endpoint_url

    parsed = urlparse(endpoint_url)
    if parsed.hostname not in {"localhost", "127.0.0.1"}:
        return endpoint_url

    if not os.path.exists("/.dockerenv"):
        return endpoint_url

    netloc = "host.docker.internal"
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"

    return urlunparse(parsed._replace(netloc=netloc))


def find_service_by_path(db: Session, agentdns_path: str) -> Optional[Service]:
    """
    根据AgentDNS路径查找服务

    Args:
        db: 数据库会话
        agentdns_path: AgentDNS路径

    Returns:
        Service: 服务对象，如果未找到则返回None
    """
    agentdns_uri = f"agentdns://{agentdns_path}"

    service = db.query(Service).filter(
        Service.agentdns_uri == agentdns_uri,
        Service.is_active == True
    ).first()

    return service


def validate_service_access(service: Service, user: User, db: Session) -> None:
    """
    验证用户对服务的访问权限

    当前项目中：
    - 公开服务：所有已认证用户可访问
    - 私有服务：仅组织所有者可访问

    Args:
        service: 服务对象
        user: 当前用户
        db: 数据库会话

    Raises:
        HTTPException: 无权限时抛出
    """
    if service.is_public:
        return

    organization = db.query(Organization).filter(
        Organization.id == service.organization_id
    ).first()

    if organization and organization.owner_id == user.id:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="无权限访问此服务"
    )


def prepare_service_headers(service: Service, user: User, agent: Optional[Agent] = None) -> Dict[str, str]:
    """
    准备服务请求头

    Args:
        service: 服务对象
        user: 当前用户
        agent: 当前Agent对象，可空

    Returns:
        Dict[str, str]: 请求头字典
    """
    headers = {
        "Content-Type": "application/json",
        "X-User-ID": str(user.id),
        "X-User-Name": user.username,
    }

    if agent:
        headers["X-Agent-ID"] = str(agent.id)
        headers["X-Agent-Name"] = agent.name

    if hasattr(service, 'headers') and service.headers:
        try:
            service_headers = json.loads(service.headers)
            if isinstance(service_headers, dict):
                headers.update(service_headers)
        except json.JSONDecodeError:
            logger.warning(f"服务 {service.id} 的headers配置无效")

    return headers


def _build_tracking_headers(usage_record: Usage) -> Dict[str, str]:
    """
    构建调用追踪响应头

    Args:
        usage_record: Usage记录对象

    Returns:
        Dict[str, str]: 响应头字典
    """
    return {
        "X-AgentDNS-Usage-ID": str(usage_record.id),
        "X-AgentDNS-Request-ID": usage_record.request_id
    }


def _calc_execution_time_ms(start_time: datetime) -> int:
    if start_time.tzinfo is not None:
        now = datetime.now(start_time.tzinfo)
    else:
        now = datetime.utcnow()
    return int((now - start_time).total_seconds() * 1000)


def _parse_response_body(response: httpx.Response) -> Any:
    """
    解析上游服务响应内容

    优先按JSON解析，失败时回退为纯文本

    Args:
        response: httpx响应对象

    Returns:
        Any: 解析后的响应内容
    """
    try:
        return response.json()
    except Exception:
        return {"raw_response": response.text}


async def query_async_task_status(task_id: str, current_user: User, db: Session):
    """
    查询异步任务状态的内部辅助函数

    同时供：
    - 本文件中的 /tasks/{task_id} 路由
    - client/services.py 中的客户端任务状态接口
    """
    task = db.query(AsyncTask).filter(
        AsyncTask.id == task_id,
        AsyncTask.user_id == current_user.id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务未找到"
        )

    await update_task_status(task, db)
    db.refresh(task)

    return {
        "task_id": task.id,
        "usage_id": task.usage_id,
        "service_name": task.service.name if task.service else "Unknown",
        "state": task.state,
        "progress": task.progress,
        "error": task.error_message if task.state == "failed" else None
    }


@router.get("/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    principal = Depends(get_current_principal),
    db: Session = Depends(get_db)
):
    """
    获取异步任务状态
    """
    current_user = principal["user"]
    return await query_async_task_status(task_id, current_user, db)


@router.api_route(
    "/{agentdns_path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"]
)
async def proxy_request(
    agentdns_path: str,
    request: Request,
    principal = Depends(get_current_principal),
    db: Session = Depends(get_db)
):
    """
    统一代理入口 - 根据http_mode分发请求
    """
    current_user = principal["user"]
    current_agent = principal["agent"]

    logger.info(f"代理请求: {request.method} /{agentdns_path} - 用户: {current_user.id}")

    service = find_service_by_path(db, agentdns_path)
    if not service:
        logger.warning(f"服务未找到: {agentdns_path}")
        raise HTTPException(
            status_code=404,
            detail="AgentDNS服务未找到或已禁用"
        )

    logger.info(f"服务找到: {service.name} (ID: {service.id}) - http_mode: {service.http_mode}")

    validate_service_access(service, current_user, db)

    if not service.endpoint_url:
        logger.error(f"服务 {service.id} 缺少endpoint_url")
        raise HTTPException(
            status_code=500,
            detail="服务配置错误: 缺少endpoint_url"
        )

    http_mode = service.http_mode or "sync"

    try:
        if http_mode == "sync":
            return await handle_sync_request(service, request, current_user, db, current_agent)
        elif http_mode == "stream":
            return await handle_stream_request(service, request, current_user, db, current_agent)
        elif http_mode == "async":
            return await handle_async_request(service, request, current_user, db, current_agent)
        else:
            logger.warning(f"未知的http_mode: {http_mode}, 使用sync")
            return await handle_sync_request(service, request, current_user, db, current_agent)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理请求失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def handle_sync_request(
    service: Service,
    request: Request,
    user: User,
    db: Session,
    agent: Optional[Agent] = None
):
    """
    处理同步请求

    同步请求在真正进入服务执行后：
    - 成功时记录一条可评价Usage
    - 失败时也记录一条可评价Usage（但默认不收费）
    - 响应头返回 usage_id / request_id
    """
    logger.info(f"处理同步请求: {service.name}")

    billing_service = BillingService(db)

    if service.price_per_unit > 0 and user.balance < service.price_per_unit:
        raise HTTPException(status_code=402, detail="余额不足")

    body = await request.body()
    if body:
        try:
            input_data = json.loads(body)
        except json.JSONDecodeError:
            input_data = {}
    else:
        input_data = {}

    headers = prepare_service_headers(service, user, agent)
    target_method = service.http_method or request.method

    start_time = datetime.utcnow()

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.request(
                method=target_method,
                url=normalize_endpoint_url(service.endpoint_url),
                json=input_data,
                headers=headers,
                params=request.query_params
            )

        response.raise_for_status()
        result = _parse_response_body(response)
        execution_time_ms = _calc_execution_time_ms(start_time)

        usage_record = billing_service.record_usage(
            user=user,
            service=service,
            amount=service.price_per_unit if service.price_per_unit > 0 else 0.0,
            tokens_used=0,
            requests_count=1,
            data_transfer_mb=0.0,
            request_id=None,
            method=target_method,
            execution_time_ms=execution_time_ms,
            status_code=response.status_code,
            request_metadata=input_data,
            agent_id=agent.id if agent else None,
            http_mode="sync",
            final_state="success",
            error_message=None,
            is_meaningful=True,
            create_billing_record=(service.price_per_unit > 0)
        )

        tracking_headers = _build_tracking_headers(usage_record)
        return JSONResponse(content=result, headers=tracking_headers)

    except httpx.HTTPStatusError as e:
        execution_time_ms = _calc_execution_time_ms(start_time)
        error_detail = e.response.text if e.response is not None else str(e)
        status_code = e.response.status_code if e.response is not None else 502

        usage_record = billing_service.record_usage(
            user=user,
            service=service,
            amount=0.0,
            tokens_used=0,
            requests_count=1,
            data_transfer_mb=0.0,
            request_id=None,
            method=target_method,
            execution_time_ms=execution_time_ms,
            status_code=status_code,
            request_metadata=input_data,
            agent_id=agent.id if agent else None,
            http_mode="sync",
            final_state="fail",
            error_message=error_detail,
            is_meaningful=True,
            create_billing_record=False
        )

        tracking_headers = _build_tracking_headers(usage_record)
        raise HTTPException(
            status_code=status_code,
            detail=error_detail,
            headers=tracking_headers
        )

    except httpx.RequestError as e:
        execution_time_ms = _calc_execution_time_ms(start_time)

        usage_record = billing_service.record_usage(
            user=user,
            service=service,
            amount=0.0,
            tokens_used=0,
            requests_count=1,
            data_transfer_mb=0.0,
            request_id=None,
            method=target_method,
            execution_time_ms=execution_time_ms,
            status_code=502,
            request_metadata=input_data,
            agent_id=agent.id if agent else None,
            http_mode="sync",
            final_state="fail",
            error_message=str(e),
            is_meaningful=True,
            create_billing_record=False
        )

        tracking_headers = _build_tracking_headers(usage_record)
        raise HTTPException(
            status_code=502,
            detail=f"调用上游服务失败: {str(e)}",
            headers=tracking_headers
        )


async def handle_stream_request(
    service: Service,
    request: Request,
    user: User,
    db: Session,
    agent: Optional[Agent] = None
):
    """
    处理流式请求

    流式请求在开始转发前先创建Usage锚点，
    流结束后再补全最终状态与费用
    """
    logger.info(f"处理流式请求: {service.name}")

    body = await request.body()
    if body:
        try:
            input_data = json.loads(body)
        except json.JSONDecodeError:
            input_data = {}
    else:
        input_data = {}

    input_data["stream"] = True

    billing_service = BillingService(db)
    if service.price_per_unit > 0 and user.balance < service.price_per_unit:
        raise HTTPException(status_code=402, detail="余额不足")

    headers = prepare_service_headers(service, user, agent)
    target_method = service.http_method or request.method

    usage_record = billing_service.create_usage_anchor(
        user=user,
        service=service,
        method=target_method,
        request_metadata=input_data,
        agent_id=agent.id if agent else None,
        http_mode="stream",
        request_id=None,
        is_meaningful=True,
        initial_state="pending"
    )

    tracking_headers = _build_tracking_headers(usage_record)
    start_time = usage_record.started_at or datetime.utcnow()

    async def generate_stream():
        yielded_any = False

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                async with client.stream(
                    method=target_method,
                    url=normalize_endpoint_url(service.endpoint_url),
                    json=input_data,
                    headers=headers,
                    params=request.query_params
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if line.strip():
                            yielded_any = True
                            yield f"{line}\n"

                    billing_service.finalize_usage_record(
                        usage_record=usage_record,
                        final_state="success",
                        execution_time_ms=_calc_execution_time_ms(start_time),
                        status_code=response.status_code,
                        error_message=None,
                        request_metadata=input_data,
                        actual_cost=service.price_per_unit if service.price_per_unit > 0 else 0.0,
                        charge_user=(service.price_per_unit > 0)
                    )

        except httpx.HTTPStatusError as e:
            final_state = "partial" if yielded_any else "fail"

            billing_service.finalize_usage_record(
                usage_record=usage_record,
                final_state=final_state,
                execution_time_ms=_calc_execution_time_ms(start_time),
                status_code=e.response.status_code if e.response is not None else 502,
                error_message=e.response.text if e.response is not None else str(e),
                request_metadata=input_data,
                actual_cost=0.0,
                charge_user=False
            )

            error_payload = json.dumps(
                {"error": f"流式调用失败: {str(e)}"},
                ensure_ascii=False
            )
            yield f"{error_payload}\n"

        except Exception as e:
            final_state = "partial" if yielded_any else "fail"

            billing_service.finalize_usage_record(
                usage_record=usage_record,
                final_state=final_state,
                execution_time_ms=_calc_execution_time_ms(start_time),
                status_code=502,
                error_message=str(e),
                request_metadata=input_data,
                actual_cost=0.0,
                charge_user=False
            )

            error_payload = json.dumps(
                {"error": f"流式调用异常终止: {str(e)}"},
                ensure_ascii=False
            )
            yield f"{error_payload}\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers=tracking_headers
    )


async def handle_async_request(
    service: Service,
    request: Request,
    user: User,
    db: Session,
    agent: Optional[Agent] = None
):
    """
    处理异步请求
    """
    logger.info(f"处理异步请求: {service.name}")

    if request.method != "POST":
        raise HTTPException(400, "异步服务只支持POST方法创建任务")

    return await create_async_task(service, request, user, db, agent)


async def create_async_task(
    service: Service,
    request: Request,
    user: User,
    db: Session,
    agent: Optional[Agent] = None
):
    """
    创建异步任务

    异步任务在真正发起上游任务创建请求前先落一条Usage锚点，
    后续成功/失败时再更新该Usage记录
    """
    body = await request.body()
    if body:
        try:
            input_data = json.loads(body)
        except json.JSONDecodeError:
            input_data = {}
    else:
        input_data = {}

    task_id = str(uuid.uuid4())
    billing_service = BillingService(db)

    if service.price_per_unit > 0 and user.balance < service.price_per_unit:
        raise HTTPException(status_code=402, detail="余额不足")

    headers = prepare_service_headers(service, user, agent)
    target_method = service.http_method or "POST"

    usage_record = billing_service.create_usage_anchor(
        user=user,
        service=service,
        method=target_method,
        request_metadata=input_data,
        agent_id=agent.id if agent else None,
        http_mode="async",
        request_id=None,
        is_meaningful=True,
        initial_state="pending"
    )

    tracking_headers = _build_tracking_headers(usage_record)

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.request(
                method=target_method,
                url=normalize_endpoint_url(service.endpoint_url),
                json=input_data,
                headers=headers
            )

        response.raise_for_status()
        external_response = _parse_response_body(response)

        external_task_id = None
        if isinstance(external_response, dict):
            external_task_id = external_response.get("task_id") or external_response.get("id")

        if not external_task_id:
            billing_service.finalize_usage_record(
                usage_record=usage_record,
                final_state="fail",
                execution_time_ms=_calc_execution_time_ms(usage_record.started_at or datetime.utcnow()),
                status_code=response.status_code,
                error_message="上游异步服务未返回可追踪的任务ID",
                request_metadata=input_data,
                actual_cost=0.0,
                charge_user=False
            )
            raise HTTPException(
                status_code=500,
                detail="创建异步任务失败: 上游服务未返回任务ID",
                headers=tracking_headers
            )

        usage_record.status_code = response.status_code
        usage_record.request_metadata = {
            "input_data": input_data,
            "external_task_id": external_task_id
        }
        db.commit()
        db.refresh(usage_record)

        task = AsyncTask(
            id=task_id,
            service_id=service.id,
            user_id=user.id,
            agent_id=agent.id if agent else None,
            usage_id=usage_record.id,
            state="pending",
            input_data=input_data,
            external_task_id=external_task_id,
            estimated_cost=service.price_per_unit
        )
        db.add(task)
        db.commit()

        logger.info(f"异步任务创建成功: {task_id} -> {external_task_id}")

        return JSONResponse(
            content={"task_id": task_id},
            headers=tracking_headers
        )

    except HTTPException:
        raise

    except httpx.HTTPStatusError as e:
        billing_service.finalize_usage_record(
            usage_record=usage_record,
            final_state="fail",
            execution_time_ms=_calc_execution_time_ms(usage_record.started_at or datetime.utcnow()),
            status_code=e.response.status_code if e.response is not None else 502,
            error_message=e.response.text if e.response is not None else str(e),
            request_metadata=input_data,
            actual_cost=0.0,
            charge_user=False
        )

        raise HTTPException(
            status_code=e.response.status_code if e.response is not None else 502,
            detail=f"创建异步任务失败: {e.response.text if e.response is not None else str(e)}",
            headers=tracking_headers
        )

    except httpx.RequestError as e:
        billing_service.finalize_usage_record(
            usage_record=usage_record,
            final_state="fail",
            execution_time_ms=_calc_execution_time_ms(usage_record.started_at or datetime.utcnow()),
            status_code=502,
            error_message=str(e),
            request_metadata=input_data,
            actual_cost=0.0,
            charge_user=False
        )

        raise HTTPException(
            status_code=502,
            detail=f"创建异步任务失败: {str(e)}",
            headers=tracking_headers
        )


async def update_task_status(task: AsyncTask, db: Session):
    """
    更新异步任务状态 - 透传适配器的原始响应

    在第一阶段中：
    - 成功时完成Usage并执行扣费
    - 失败时完成Usage但不收费
    - 运行中仅更新任务状态
    """
    service = task.service
    usage_record = task.usage

    query_url = f"{normalize_endpoint_url(service.endpoint_url).rstrip('/')}/{task.external_task_id}"
    headers = prepare_service_headers(service, task.user, task.agent)
    billing_service = BillingService(db)

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(query_url, headers=headers)
            response.raise_for_status()
            status_data = response.json()

        task.result_data = status_data
        adapter_state = status_data.get("state", "unknown").lower()

        if adapter_state in ["succeeded", "completed", "success", "finished"]:
            task.state = "succeeded"
            task.completed_at = datetime.utcnow()
            task.progress = 1.0

            if usage_record:
                execution_time_ms = None
                if usage_record.started_at:
                    execution_time_ms = _calc_execution_time_ms(usage_record.started_at)

                billing_service.finalize_usage_record(
                    usage_record=usage_record,
                    final_state="success",
                    execution_time_ms=execution_time_ms,
                    status_code=200,
                    error_message=None,
                    request_metadata=status_data,
                    actual_cost=task.estimated_cost if task.estimated_cost > 0 else 0.0,
                    charge_user=(not task.is_billed and task.estimated_cost > 0)
                )

            if not task.is_billed and task.estimated_cost > 0:
                task.actual_cost = task.estimated_cost
                task.is_billed = True

        elif adapter_state in ["failed", "error", "cancelled"]:
            task.state = "failed"
            task.error_message = status_data.get("error") or "任务执行失败"
            task.completed_at = datetime.utcnow()

            if usage_record:
                execution_time_ms = None
                if usage_record.started_at:
                    execution_time_ms = _calc_execution_time_ms(usage_record.started_at)

                billing_service.finalize_usage_record(
                    usage_record=usage_record,
                    final_state="fail",
                    execution_time_ms=execution_time_ms,
                    status_code=500,
                    error_message=task.error_message,
                    request_metadata=status_data,
                    actual_cost=0.0,
                    charge_user=False
                )

        elif adapter_state in ["running", "processing", "in_progress"]:
            task.state = "running"
            task.progress = status_data.get("progress", task.progress)
            if not task.started_at:
                task.started_at = datetime.utcnow()

        elif adapter_state == "pending":
            task.state = "pending"

        db.commit()
        logger.info(f"任务状态更新: {task.id} -> {task.state} (适配器状态: {adapter_state})")

    except Exception as e:
        logger.warning(f"更新任务状态失败: {task.id}, 错误: {e}")
