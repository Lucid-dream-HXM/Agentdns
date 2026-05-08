"""
搜索引擎服务 - 基于向量的服务搜索
提供基于向量相似性的服务搜索功能，支持多种过滤条件
"""

import re
import json
from typing import List, Tuple, Optional, Dict
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
import logging

from ..models.service import Service, ServiceMetadata
from ..models.organization import Organization
from ..models.review import ServiceTrustStats
from .embedding_service import EmbeddingService
from .milvus_service import get_milvus_service

# 获取当前模块的日志记录器
logger = logging.getLogger(__name__)


def _attach_trust_to_service(service: Service, trust_stats: Optional[ServiceTrustStats]) -> Service:
    """
    给Service对象动态附加trust摘要字段
    """
    if trust_stats:
        service.trust_score = trust_stats.trust_score
        service.success_rate = trust_stats.success_rate
        service.rating_count = trust_stats.rating_count
        service.avg_response_time_ms = trust_stats.avg_response_time_ms
    else:
        service.trust_score = None
        service.success_rate = None
        service.rating_count = None
        service.avg_response_time_ms = None

    return service


def service_to_safe_dict(service: Service) -> dict:
    """
    将服务转换为安全字典
    
    返回服务的安全表示形式，不包含敏感信息如API密钥等
    
    Args:
        service: 服务模型
    
    Returns:
        dict: 服务的安全字典表示
    """
    return {
        "id": service.id,  # 服务ID
        "name": service.name,  # 服务名称
        "category": service.category,  # 服务类别
        "agentdns_uri": service.agentdns_uri,  # AgentDNS URI
        "description": service.description,  # 服务描述
        "version": service.version,  # 服务版本
        "is_active": service.is_active,  # 服务是否激活
        "is_public": service.is_public,  # 服务是否公开
        # 注意：排除endpoint_url和service_api_key（敏感字段）
        "protocol": service.protocol or "HTTP",
        "supported_protocols": [service.protocol] if getattr(service, "protocol", None) else [],  # 支持的协议列表
        "authentication_required": service.authentication_required,  # 是否需要认证
        "pricing_model": service.pricing_model,  # 定价模型
        "price_per_unit": service.price_per_unit,  # 单位价格
        "currency": service.currency,  # 货币单位
        "tags": service.tags or [],  # 服务标签
        "capabilities": service.capabilities or {},  # 服务能力
        "organization_id": service.organization_id,  # 组织ID
        "created_at": service.created_at,  # 创建时间
        "updated_at": service.updated_at,  # 更新时间
        
        # HTTP代理服务字段（完整返回，但不包含敏感信息）
        "agentdns_path": service.agentdns_path,  # AgentDNS路径
        "http_method": service.http_method,  # HTTP方法
        "input_description": service.input_description,  # 输入描述
        "output_description": service.output_description,  # 输出描述
        "trust_score": getattr(service, "trust_score", None),
        "success_rate": getattr(service, "success_rate", None),
        "rating_count": getattr(service, "rating_count", None),
        "avg_response_time_ms": getattr(service, "avg_response_time_ms", None),
    }


def service_to_tool_format(service: Service) -> dict:
    """
    将服务转换为SDK兼容的工具格式
    
    将服务对象转换为符合AgentDNS SDK规范的工具对象格式
    
    Args:
        service: 服务模型
    
    Returns:
        dict: 服务的工具格式表示
    """
    
    # 获取组织名称
    organization_name = "Unknown"
    if hasattr(service, 'organization') and service.organization:
        organization_name = service.organization.name
    
    # 构建成本对象
    cost_description_map = {
        "per_request": "按请求计费",  # 每次请求计费
        "per_token": "按token计费",  # 每个token计费
        "per_mb": "按MB传输计费",  # 每MB传输数据计费
        "monthly": "按月计费",  # 每月计费
        "yearly": "按年计费"  # 每年计费
    }
    
    cost = {
        "type": service.pricing_model or "per_request",  # 定价模型类型
        "price": str(service.price_per_unit or 0.0),  # 价格
        "currency": service.currency or "CNY",  # 货币单位
        "description": cost_description_map.get(service.pricing_model, "按请求计费")  # 成本描述
    }
    
    return {
        "name": service.name or "",  # 服务名称
        "description": service.description or "",  # 服务描述
        "organization": organization_name,  # 组织名称
        "agentdns_url": service.agentdns_uri or "", # AgentDNS URL
        "cost": cost,  # 成本信息
        "protocol": service.protocol or "MCP",  # 协议类型
        "method": service.http_method or "POST",  # HTTP方法
        "http_mode": service.http_mode,  # HTTP模式
        "input_description": service.input_description or "{}",  # 输入描述
        "output_description": service.output_description or "{}",
        "trust_score": getattr(service, "trust_score", None),
        "success_rate": getattr(service, "success_rate", None),
        "rating_count": getattr(service, "rating_count", None),
        "avg_response_time_ms": getattr(service, "avg_response_time_ms", None),
    }


class SearchEngine:
    """
    AgentDNS服务搜索引擎 - 基于向量的搜索
    
    提供基于向量相似性的服务搜索功能，支持多种过滤条件
    当向量搜索不可用时，回退到基于关键词的搜索
    """
    
    def __init__(self, db: Session):
        """
        初始化搜索引擎
        
        Args:
            db: 数据库会话
        """
        self.db = db  # 数据库会话
        try:
            self.embedding_service = EmbeddingService()  # 嵌入服务实例
        except ValueError as e:
            logger.warning(f"初始化嵌入服务失败: {e}")
            self.embedding_service = None
        
        try:
            self.milvus_service = get_milvus_service()  # Milvus向量数据库服务实例
            # 测试Milvus连接
            self.milvus_service.get_collection_stats()
            logger.info("Milvus服务初始化成功")
        except Exception as e:
            logger.warning(f"初始化Milvus服务失败: {e}")
            self.milvus_service = None

    def _get_trust_stats_map(self, service_ids: List[int]) -> Dict[int, ServiceTrustStats]:
        """
        批量获取服务信任摘要映射
        """
        if not service_ids:
            return {}

        trust_stats_list = self.db.query(ServiceTrustStats).filter(
            ServiceTrustStats.service_id.in_(service_ids)
        ).all()

        return {item.service_id: item for item in trust_stats_list}

    def _calc_cost_score(self, service: Service, max_price: Optional[float] = None) -> float:
        """
        计算价格分
        """
        price = service.price_per_unit or 0.0

        if price <= 0:
            return 100.0

        if max_price is not None and max_price > 0:
            ratio = min(price / max_price, 1.0)
            return round((1.0 - ratio) * 100.0, 2)

        if price <= 1:
            return 90.0
        if price <= 5:
            return 75.0
        if price <= 10:
            return 60.0
        return 40.0

    def _build_searchable_text(self, service: Service) -> str:
        """
        为关键词回退搜索构造可搜索文本

        将服务的多种元数据字段拼接成统一文本，
        使 fallback 搜索更贴近实验实际依赖的 metadata 语义。
        """
        text_parts = []

        if service.name:
            text_parts.append(service.name)
        if service.category:
            text_parts.append(service.category)
        if service.description:
            text_parts.append(service.description)
        if service.protocol:
            text_parts.append(service.protocol)
        if service.agentdns_path:
            text_parts.append(service.agentdns_path)
        if service.input_description:
            text_parts.append(service.input_description)
        if service.output_description:
            text_parts.append(service.output_description)

        if service.tags:
            text_parts.append(" ".join([str(x) for x in service.tags]))

        if service.capabilities:
            try:
                text_parts.append(json.dumps(service.capabilities, ensure_ascii=False))
            except Exception:
                text_parts.append(str(service.capabilities))

        if getattr(service, "service_metadata", None):
            metadata = service.service_metadata
            if metadata.search_keywords:
                try:
                    text_parts.append(json.dumps(metadata.search_keywords, ensure_ascii=False))
                except Exception:
                    text_parts.append(str(metadata.search_keywords))

            if metadata.examples:
                try:
                    text_parts.append(json.dumps(metadata.examples, ensure_ascii=False))
                except Exception:
                    text_parts.append(str(metadata.examples))

        return " ".join(text_parts).lower()

    def _calc_keyword_match_score(self, searchable_text: str, keywords: List[str]) -> float:
        """
        计算关键词匹配分

        简单规则：
        - 命中关键词越多，分数越高
        - 完全无命中则为 0
        """
        if not keywords:
            return 0.0

        hits = 0
        for kw in keywords:
            if kw and kw in searchable_text:
                hits += 1

        return (hits / len(keywords)) * 100.0

    def _rerank_services(
        self,
        services: List[Service],
        match_scores: Optional[Dict[int, float]] = None,
        sort_by: str = "balanced",
        max_price: Optional[float] = None
    ) -> List[Service]:
        """
        对候选服务进行召回后轻量重排
        """
        if not services:
            return services

        ranked = []

        for idx, service in enumerate(services):
            default_match_score = max(0.0, 100.0 - idx * 5.0)
            match_score = match_scores.get(service.id, default_match_score) if match_scores else default_match_score

            trust_score = getattr(service, "trust_score", None)
            if trust_score is None:
                trust_score = 0.0

            success_rate = getattr(service, "success_rate", None)
            performance_score = success_rate if success_rate is not None else 0.0

            cost_score = self._calc_cost_score(service, max_price=max_price)

            if sort_by == "trust":
                final_rank = (
                    0.60 * trust_score +
                    0.20 * match_score +
                    0.10 * performance_score +
                    0.10 * cost_score
                )
            elif sort_by == "relevance":
                final_rank = (
                    0.80 * match_score +
                    0.10 * trust_score +
                    0.05 * performance_score +
                    0.05 * cost_score
                )
            else:
                final_rank = (
                    0.55 * match_score +
                    0.25 * trust_score +
                    0.10 * performance_score +
                    0.10 * cost_score
                )

            ranked.append((final_rank, service))

        ranked.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in ranked]

    def search(
        self,
        query: str,
        category: Optional[str] = None,
        organization: Optional[str] = None,
        protocol: Optional[str] = None,
        max_price: Optional[float] = None,
        limit: int = 10,
        return_tool_format: bool = False,
        sort_by: str = "balanced",
        include_trust: bool = True,
        min_trust_score: Optional[float] = None
    ) -> Tuple[List[dict], int]:
        """
        执行服务搜索

        使用向量嵌入技术进行语义搜索，返回最匹配的服务
        如果向量搜索不可用，则使用基于关键词的搜索作为备用
        """
        logger.info(
            f"搜索: '{query}' 过滤器 - 类别: {category}, 组织: {organization}, 协议: {protocol}, "
            f"最高价格: {max_price}, 排序: {sort_by}, 附带trust: {include_trust}, 最低trust: {min_trust_score}"
        )
        
        # 构建基础查询
        base_query = self.db.query(Service).options(
            joinedload(Service.organization)  # 预加载组织信息
        ).filter(
            Service.is_active == True,  # 只搜索激活的服务
            Service.is_public == True  # 只搜索公开的服务
        )
        
        # 应用基础过滤条件
        if category:
            base_query = base_query.filter(Service.category == category)
        
        if organization:
            base_query = base_query.join(Service.organization).filter(
                Organization.name == organization
            )
        
        if protocol:
            base_query = base_query.filter(Service.protocol == protocol)
        
        if max_price is not None:
            base_query = base_query.filter(Service.price_per_unit <= max_price)
        
        # 尝试向量搜索
        if self.milvus_service and self.embedding_service:
            try:
                # 1) 检查Milvus中的向量
                stats = self.milvus_service.get_collection_stats()
                vector_count = stats.get("num_entities", 0)
                logger.info(f"Milvus集合包含 {vector_count} 个向量")
                
                if vector_count > 0:
                    # 2) 创建查询嵌入
                    query_embedding = self.embedding_service.create_query_embedding(query)
                    
                    # 3) 确定组织筛选条件
                    organization_id_filter = None
                    if organization:
                        org = self.db.query(Organization).filter(
                            Organization.name == organization
                        ).first()
                        if org:
                            organization_id_filter = org.id
                    
                    # 4) 在Milvus中进行向量搜索
                    vector_results = self.milvus_service.search_similar_services(
                        query_embedding=query_embedding,
                        top_k=limit * 3,
                        category_filter=category,
                        organization_filter=organization_id_filter
                    )
                    
                    logger.info(f"向量搜索返回 {len(vector_results)} 个结果")

                    if vector_results:
                        # 5) 从数据库获取完整服务信息
                        service_ids = [result["service_id"] for result in vector_results]
                        services_query = self.db.query(Service).options(
                            joinedload(Service.organization)
                        ).filter(
                            Service.id.in_(service_ids)
                        )

                        services_list = services_query.all()
                        trust_map = self._get_trust_stats_map(service_ids) if include_trust else {}

                        services_dict = {}
                        for service in services_list:
                            trust_stats = trust_map.get(service.id)
                            service = _attach_trust_to_service(service, trust_stats)
                            services_dict[service.id] = service

                        ordered_candidates = []
                        added_service_ids = set()
                        match_scores = {}

                        for idx, result in enumerate(vector_results):
                            service_id = result["service_id"]

                            if service_id in services_dict and service_id not in added_service_ids:
                                service = services_dict[service_id]

                                if min_trust_score is not None:
                                    trust_score = getattr(service, "trust_score", None)
                                    if trust_score is not None and trust_score < min_trust_score:
                                        continue

                                ordered_candidates.append(service)
                                added_service_ids.add(service_id)

                                similarity = result.get("similarity")
                                if similarity is None:
                                    similarity = max(0.0, 100.0 - idx * 5.0)
                                else:
                                    similarity = float(similarity) * 100.0

                                match_scores[service_id] = similarity

                        reranked_services = self._rerank_services(
                            ordered_candidates,
                            match_scores=match_scores,
                            sort_by=sort_by,
                            max_price=max_price
                        )[:limit]

                        if return_tool_format:
                            tool_services = [service_to_tool_format(service) for service in reranked_services]
                            return tool_services, len(reranked_services)
                        else:
                            safe_services = [service_to_safe_dict(service) for service in reranked_services]
                            return safe_services, len(reranked_services)
                    
            except Exception as e:
                logger.warning(f"向量搜索失败，回退到关键词搜索: {e}")
        else:
            logger.warning("向量搜索不可用，使用关键词搜索")
        
        # 向量搜索不可用或失败，使用增强版关键词搜索作为备用
        logger.info("执行增强版关键词搜索作为备用")

        keywords = re.findall(r'\w+', query.lower())

        # 先取一个较大的候选池，再在 Python 层做富文本匹配
        services = base_query.options(
            joinedload(Service.organization),
            joinedload(Service.service_metadata)
        ).limit(limit * 10).all()

        trust_map = self._get_trust_stats_map([service.id for service in services]) if include_trust else {}

        enriched_services = []
        match_scores = {}

        for service in services:
            trust_stats = trust_map.get(service.id)
            service = _attach_trust_to_service(service, trust_stats)

            if min_trust_score is not None:
                trust_score = getattr(service, "trust_score", None)
                if trust_score is not None and trust_score < min_trust_score:
                    continue

            searchable_text = self._build_searchable_text(service)
            keyword_score = self._calc_keyword_match_score(searchable_text, keywords)

            # 有关键词时，过滤掉完全无命中的候选
            if keywords and keyword_score <= 0:
                continue

            enriched_services.append(service)
            match_scores[service.id] = keyword_score if keyword_score > 0 else 50.0

        total = len(enriched_services)

        reranked_services = self._rerank_services(
            enriched_services,
            match_scores=match_scores,
            sort_by=sort_by,
            max_price=max_price
        )[:limit]

        if return_tool_format:
            tools = [service_to_tool_format(service) for service in reranked_services]
            return tools, total
        else:
            service_dicts = [service_to_safe_dict(service) for service in reranked_services]
            return service_dicts, total
    
    def get_vector_search_stats(self) -> dict:
        """
        获取向量搜索统计信息
        
        返回向量搜索系统的运行状态和统计信息
        
        Returns:
            dict: 包含向量搜索统计信息的字典
        """
        try:
            # 获取Milvus集合统计信息
            stats = self.milvus_service.get_collection_stats()
            return {
                "milvus_enabled": True,  # Milvus是否启用
                "total_vectors": stats.get("num_entities", 0),  # 向量总数
                "collection_name": stats.get("collection_name", "unknown"),  # 集合名称
                "vector_dimension": self.embedding_service.dimension,  # 向量维度
                "embedding_model": self.embedding_service.model  # 嵌入模型
            }
        except Exception as e:
            # 获取向量搜索统计信息出错
            logger.error(f"获取向量搜索统计信息错误: {e}")
            return {
                "milvus_enabled": False,  # Milvus未启用
                "error": str(e)  # 错误信息
            }