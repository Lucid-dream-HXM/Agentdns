"""
Milvus向量数据库服务 - 用于管理服务向量的存储、搜索和更新
提供向量数据库的连接、集合管理和向量操作功能
"""

from pymilvus import connections, Collection, CollectionSchema, DataType, FieldSchema, utility
from typing import List, Dict, Any, Tuple
import logging
from ..core.config import settings

logger = logging.getLogger(__name__)


class MilvusService:
    """
    Milvus向量数据库服务
    
    负责Milvus向量数据库的连接管理、集合操作和向量处理
    提供服务向量的插入、搜索、更新和删除功能
    """
    
    def __init__(self):
        """
        初始化Milvus服务
        
        配置集合名称、维度，初始化连接和集合
        """
        self.collection_name = settings.MILVUS_COLLECTION_NAME
        self.dimension = settings.MILVUS_DIMENSION
        self.collection = None
        self._init_connection()
        self._init_collection()
    
    def _init_connection(self):
        """
        初始化Milvus连接
        
        连接到Milvus服务器
        
        Raises:
            Exception: 当连接失败时抛出
        """
        try:
            connections.connect(
                alias="default",
                host=settings.MILVUS_HOST,
                port=settings.MILVUS_PORT
            )
            logger.info(f"已连接到Milvus: {settings.MILVUS_HOST}:{settings.MILVUS_PORT}")
        except Exception as e:
            logger.error(f"连接Milvus失败: {e}")
            raise
    
    def _init_collection(self):
        """
        初始化集合
        
        检查集合是否存在，不存在则创建新集合
        加载集合到内存
        
        Raises:
            Exception: 当初始化失败时抛出
        """
        try:
            # 检查集合是否存在
            if utility.has_collection(self.collection_name):
                self.collection = Collection(self.collection_name)
                logger.info(f"集合 {self.collection_name} 已存在")
            else:
                # 创建新集合
                self._create_collection()
            
            # 加载集合到内存
            self.collection.load()
            
        except Exception as e:
            logger.error(f"初始化集合失败: {e}")
            raise
    
    def _create_collection(self):
        """
        创建新集合
        
        定义字段、创建集合schema、创建集合和索引
        """
        # 定义字段
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="service_id", dtype=DataType.INT64),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.dimension),
            FieldSchema(name="service_name", dtype=DataType.VARCHAR, max_length=200),
            FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="organization_id", dtype=DataType.INT64),
        ]
        
        # 创建集合schema
        schema = CollectionSchema(
            fields=fields,
            description="AgentDNS服务向量集合"
        )
        
        # 创建集合
        self.collection = Collection(
            name=self.collection_name,
            schema=schema
        )
        
        # 创建索引
        index_params = {
            "metric_type": "COSINE",  # 余弦相似度
            "index_type": "IVF_FLAT",
            "params": {"nlist": 128}
        }
        
        self.collection.create_index(
            field_name="embedding",
            index_params=index_params
        )
        
        logger.info(f"已创建新集合 {self.collection_name}")
    
    def insert_service_vector(
        self,
        service_id: int,
        embedding: List[float],
        service_name: str,
        category: str,
        organization_id: int
    ) -> bool:
        """
        向Milvus插入服务向量
        
        向Milvus数据库插入服务的向量嵌入
        
        Args:
            service_id: 服务ID
            embedding: 服务的向量嵌入
            service_name: 服务名称
            category: 服务类别
            organization_id: 组织ID
        
        Returns:
            bool: 插入是否成功
        """
        try:
            # 准备数据
            entities = [
                [service_id],  # service_id
                [embedding],   # embedding
                [service_name], # service_name
                [category or ""], # category
                [organization_id] # organization_id
            ]
            
            # 插入数据
            insert_result = self.collection.insert(entities)
            
            # 刷新以确保数据被持久化
            self.collection.flush()
            
            logger.info(f"已插入服务 {service_id} 的向量")
            return True
            
        except Exception as e:
            logger.error(f"插入服务 {service_id} 的向量失败: {e}")
            return False
    
    def search_similar_services(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        category_filter: str = None,
        organization_filter: int = None
    ) -> List[Dict[str, Any]]:
        """
        搜索相似服务
        
        根据查询向量搜索相似的服务
        
        Args:
            query_embedding: 查询向量
            top_k: 返回结果数量
            category_filter: 类别过滤
            organization_filter: 组织过滤
        
        Returns:
            List[Dict[str, Any]]: 相似服务列表
        """
        try:
            # 构建搜索参数
            search_params = {
                "metric_type": "COSINE",
                "params": {"nprobe": 10}
            }
            
            # 构建过滤表达式
            expr_parts = []
            if category_filter:
                expr_parts.append(f'category == "{category_filter}"')
            if organization_filter:
                expr_parts.append(f'organization_id == {organization_filter}')
            
            expr = " && ".join(expr_parts) if expr_parts else None
            
            # 执行搜索
            search_results = self.collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                expr=expr,
                output_fields=["service_id", "service_name", "category", "organization_id"]
            )
            
            # 处理结果
            results = []
            for hits in search_results:
                for hit in hits:
                    results.append({
                        "service_id": hit.entity.get("service_id"),
                        "service_name": hit.entity.get("service_name"),
                        "category": hit.entity.get("category"),
                        "organization_id": hit.entity.get("organization_id"),
                        "similarity": float(hit.score)
                    })
            
            logger.info(f"找到 {len(results)} 个相似服务")
            return results
            
        except Exception as e:
            logger.error(f"搜索相似服务失败: {e}")
            return []
    
    def update_service_vector(
        self,
        service_id: int,
        embedding: List[float],
        service_name: str,
        category: str,
        organization_id: int
    ) -> bool:
        """
        更新服务向量
        
        更新服务的向量嵌入
        
        Args:
            service_id: 服务ID
            embedding: 新的向量嵌入
            service_name: 服务名称
            category: 服务类别
            organization_id: 组织ID
        
        Returns:
            bool: 更新是否成功
        """
        try:
            # 首先删除旧的向量（忽略结果，因为可能没有旧向量）
            try:
                self.delete_service_vector(service_id)
                logger.debug(f"已删除服务 {service_id} 的现有向量")
            except Exception as delete_error:
                logger.warning(f"删除服务 {service_id} 的现有向量错误: {delete_error}")
                # 继续；删除失败不应阻止更新
            
            # 插入新的向量
            return self.insert_service_vector(
                service_id, embedding, service_name, category, organization_id
            )
            
        except Exception as e:
            logger.error(f"更新服务 {service_id} 的向量失败: {e}")
            return False
    
    def delete_service_vector(self, service_id: int) -> bool:
        """
        删除服务向量
        
        删除服务的向量嵌入
        
        Args:
            service_id: 服务ID
        
        Returns:
            bool: 删除是否成功
        """
        try:
            # 删除指定service_id的向量
            expr = f"service_id == {service_id}"
            delete_result = self.collection.delete(expr)
            
            # 刷新以确保持久化
            self.collection.flush()
            
            logger.info(f"已删除服务 {service_id} 的向量")
            return True
            
        except Exception as e:
            logger.error(f"删除服务 {service_id} 的向量失败: {e}")
            return False
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        获取集合统计信息
        
        获取Milvus集合的统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            # 使用Milvus API获取统计信息
            self.collection.load()
            
            # 获取实体数量
            num_entities = self.collection.num_entities
            
            return {
                "num_entities": num_entities,
                "collection_name": self.collection_name
            }
        except Exception as e:
            logger.error(f"获取集合统计信息失败: {e}")
            return {"num_entities": 0, "collection_name": self.collection_name}


# 全局Milvus服务实例
milvus_service = None


def get_milvus_service() -> MilvusService:
    """
    获取Milvus服务实例
    
    单例模式，确保只有一个Milvus服务实例
    
    Returns:
        MilvusService: Milvus服务实例
    """
    global milvus_service
    if milvus_service is None:
        milvus_service = MilvusService()
    return milvus_service