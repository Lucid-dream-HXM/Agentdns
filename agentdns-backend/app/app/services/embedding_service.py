"""
嵌入服务 - 用于将文本转换为向量嵌入
提供服务和查询的向量化功能，支持相似性搜索
"""

import openai  # OpenAI API客户端库，用于调用嵌入服务
from typing import List, Dict, Any  # 类型提示，用于指定列表、字典和任意类型
import json  # JSON处理库，用于序列化和反序列化JSON数据
import logging  # 日志记录模块
import tiktoken  # OpenAI的令牌编码器，用于准确计算令牌数
from ..core.config import settings  # 项目配置，包含嵌入服务相关配置

# 获取当前模块的日志记录器
logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    嵌入服务，使用自定义的OpenAI兼容API
    
    用于将文本转换为向量嵌入，支持服务和查询的向量化
    提供服务嵌入、查询嵌入、批量嵌入等功能
    """
    
    def __init__(self):
        """
        初始化嵌入服务
        
        验证配置并初始化API客户端和编码器
        
        Raises:
            ValueError: 当未配置API密钥时抛出
        """
        if not settings.OPENAI_API_KEY:
            # 如果未配置API密钥，抛出错误
            raise ValueError("嵌入服务需要OPENAI_API_KEY")
        
        # 配置自定义OpenAI客户端
        self.client = openai.OpenAI(
            api_key=settings.OPENAI_API_KEY,  # API密钥
            base_url=settings.OPENAI_BASE_URL,  # API基础URL
            timeout=30.0  # 默认30秒超时
        )
        
        self.model = settings.OPENAI_EMBEDDING_MODEL  # 嵌入模型名称
        self.dimension = settings.MILVUS_DIMENSION  # 向量维度
        self.max_tokens = settings.OPENAI_MAX_TOKENS  # 最大token数
        
        # 初始化token编码器用于计算token数
        try:
            # 为自定义模型使用通用编码器
            self.encoding = tiktoken.get_encoding("cl100k_base")
        except Exception:
            # 退回到基于字符的估算
            self.encoding = None
            logger.warning("无法加载tiktoken编码器，使用基于字符的估算")
    
    def create_service_embedding(self, service_data: Dict[str, Any]) -> List[float]:
        """
        为服务创建嵌入
        
        将服务的各种属性组合成文本，然后生成向量嵌入
        
        Args:
            service_data: 包含服务信息的字典
        
        Returns:
            List[float]: 服务的向量嵌入列表
        """
        # 构建服务的文本表示
        text_parts = []
        
        # 服务名称（权重更高）
        if service_data.get('name'):
            text_parts.append(f"Service: {service_data['name']}")  # 服务: {服务名称}
        
        # 服务类别
        if service_data.get('category'):
            text_parts.append(f"Category: {service_data['category']}")  # 类别: {服务类别}
        
        # 基本描述
        if service_data.get('description'):
            text_parts.append(f"Description: {service_data['description']}")  # 描述: {服务描述}
        
        # 输入和输出描述
        if service_data.get('input_description'):
            text_parts.append(f"Input: {service_data['input_description']}")  # 输入: {输入描述}
        
        if service_data.get('output_description'):
            text_parts.append(f"Output: {service_data['output_description']}")  # 输出: {输出描述}
        
        # 标签
        if service_data.get('tags'):
            tags_str = ", ".join(service_data['tags'])
            text_parts.append(f"Tags: {tags_str}")  # 标签: {标签字符串}
        
        # 协议
        if service_data.get('protocol'):
            text_parts.append(f"Protocol: {service_data['protocol']}")  # 协议: {协议}
        
        # HTTP模式（使用HTTP协议时）
        if service_data.get('http_mode'):
            text_parts.append(f"HTTP Mode: {service_data['http_mode']}")  # HTTP模式: {HTTP模式}
        
        # 能力
        if service_data.get('capabilities'):
            capabilities_str = json.dumps(service_data['capabilities'], ensure_ascii=False)
            text_parts.append(f"Capabilities: {capabilities_str}")  # 能力: {能力字符串}
        
        # 组织信息
        if service_data.get('organization_name'):
            text_parts.append(f"Organization: {service_data['organization_name']}")  # 组织: {组织名称}
        
        # 连接文本部分
        full_text = " | ".join(text_parts)  # 使用" | "连接各部分文本
        
        # 截断以适应API限制
        truncated_text = self._truncate_text(full_text)
        
        # 通过自定义API创建嵌入
        embedding = self._get_embedding(truncated_text)
        
        return embedding
    
    def create_query_embedding(self, query: str) -> List[float]:
        """
        为搜索查询创建嵌入
        
        将用户查询转换为向量嵌入，用于相似性搜索
        
        Args:
            query: 搜索查询字符串
        
        Returns:
            List[float]: 查询的向量嵌入列表
        """
        # 预处理查询
        processed_query = self._preprocess_query(query)
        
        # 截断以适应API限制
        truncated_query = self._truncate_text(processed_query)
        
        # 通过自定义API创建嵌入
        embedding = self._get_embedding(truncated_query)
        
        return embedding
    
    def _get_embedding(self, text: str, retries: int = 3) -> List[float]:
        """
        调用火山方舟多模态嵌入API
        
        使用/embeddings/multimodal端点，仅输入文本
        
        Args:
            text: 要嵌入的文本
            retries: 重试次数
        
        Returns:
            List[float]: 文本的向量嵌入列表
        
        Raises:
            Exception: 当API调用失败时抛出
        """
        import time
        import requests
        
        for attempt in range(retries):
            try:
                url = f"{settings.OPENAI_BASE_URL}/embeddings/multimodal"
                headers = {
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                }
                data = {
                    "model": self.model,
                    "input": [
                        {
                            "type": "text",
                            "text": text
                        }
                    ]
                }
                
                response = requests.post(url, headers=headers, json=data, timeout=30.0)
                
                if response.status_code != 200:
                    raise Exception(f"HTTP {response.status_code}: {response.text}")
                
                result = response.json()
                
                # 解析响应: {"data": {"embedding": [...]}}
                data_obj = result.get("data", {})
                if isinstance(data_obj, list):
                    embedding = data_obj[0].get("embedding", [])
                else:
                    embedding = data_obj.get("embedding", [])
                
                if not embedding:
                    raise Exception("API返回空嵌入")
                
                # 验证向量维度
                if len(embedding) != self.dimension:
                    logger.warning(
                        f"期望维度 {self.dimension}，得到 {len(embedding)}"
                    )
                
                logger.debug(f"为文本生成嵌入: {text[:100]}...")
                return embedding
                
            except Exception as e:
                logger.error(f"火山方舟API错误 (尝试 {attempt + 1}): {e}")
                if attempt < retries - 1:
                    time.sleep(1)
                else:
                    logger.error(f"在 {retries} 次尝试后获取嵌入失败: {e}")
                    raise Exception("嵌入服务暂时不可用，请稍后再试")
        
        return []
    
    def _truncate_text(self, text: str) -> str:
        """
        截断文本以适应API令牌限制
        
        根据令牌数量限制截断文本，防止超出API限制
        
        Args:
            text: 要截断的文本
        
        Returns:
            str: 截断后的文本
        """
        if self.encoding:
            # 使用tiktoken计算token数
            tokens = self.encoding.encode(text)
            
            if len(tokens) <= self.max_tokens:
                return text
            
            # 截断token并解码回文本
            truncated_tokens = tokens[:self.max_tokens]
            truncated_text = self.encoding.decode(truncated_tokens)
            
            logger.info(f"文本从{len(tokens)}截断到{len(truncated_tokens)}个token")
            return truncated_text
        else:
            # 按字符长度估算（~1个token≈4个字符）
            estimated_tokens = len(text) // 4
            max_chars = self.max_tokens * 4
            
            if estimated_tokens <= self.max_tokens:
                return text
            
            truncated_text = text[:max_chars]
            logger.info(f"文本从~{estimated_tokens}截断到~{self.max_tokens}个token (估算)")
            return truncated_text
    
    def _preprocess_query(self, query: str) -> str:
        """
        预处理搜索查询
        
        扩展查询中的同义词以提高搜索准确性
        
        Args:
            query: 原始查询字符串
        
        Returns:
            str: 预处理后的查询字符串
        """
        # 添加常见同义词扩展
        synonyms_map = {
            "ai": "artificial intelligence machine learning",  # AI: 人工智能 机器学习
            "nlp": "natural language processing text analysis",  # NLP: 自然语言处理 文本分析
            "ml": "machine learning artificial intelligence",  # ML: 机器学习 人工智能
            "api": "application programming interface service",  # API: 应用程序编程接口 服务
            "chat": "conversation dialogue chatbot",  # 聊天: 对话 对话机器人
            "image": "picture photo visual computer vision",  # 图像: 图片 照片 视觉 计算机视觉
            "translate": "translation language conversion",  # 翻译: 翻译 语言转换
            "summarize": "summary abstract summarization",  # 总结: 摘要 概述 总结
            "analyze": "analysis analytics examination"  # 分析: 分析 分析学 检查
        }
        
        expanded_query = query.lower()
        for term, expansion in synonyms_map.items():
            if term in expanded_query:
                expanded_query += f" {expansion}"  # 将同义词扩展添加到查询中
        
        return expanded_query
    
    def batch_create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        批量创建嵌入向量
        
        一次性为多个文本创建嵌入，提高效率
        
        Args:
            texts: 要嵌入的文本列表
        
        Returns:
            List[List[float]]: 嵌入向量列表的列表
        """
        import requests
        
        embeddings = []
        truncated_texts = [self._truncate_text(text) for text in texts]
        
        try:
            url = f"{settings.OPENAI_BASE_URL}/embeddings/multimodal"
            headers = {
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                "Content-Type": "application/json",
            }
            data = {
                "model": self.model,
                "input": [
                    {"type": "text", "text": t} for t in truncated_texts
                ]
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=60.0)
            
            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
            
            result = response.json()
            data_obj = result.get("data", {})
            
            if isinstance(data_obj, list):
                for item in data_obj:
                    embeddings.append(item.get("embedding", [0.0] * self.dimension))
            else:
                # 单个响应回退
                embeddings.append(data_obj.get("embedding", [0.0] * self.dimension))
            
            logger.info(f"批量生成了 {len(embeddings)} 个嵌入")
            return embeddings
            
        except Exception as e:
            logger.error(f"批量嵌入错误: {e}")
            # 退回到单个处理
            for text in truncated_texts:
                try:
                    embedding = self._get_embedding(text)
                    embeddings.append(embedding)
                except Exception as single_error:
                    logger.error(f"获取文本嵌入失败: {single_error}")
                    embeddings.append([0.0] * self.dimension)
            
            return embeddings
    
    def get_token_count(self, text: str) -> int:
        """
        获取文本的令牌数
        
        计算文本中包含的令牌数量
        
        Args:
            text: 要计算令牌数的文本
        
        Returns:
            int: 文本的令牌数
        """
        if self.encoding:
            return len(self.encoding.encode(text))
        else:
            # 粗略估算：1个令牌≈4个字符
            return len(text) // 4
    
    def estimate_cost(self, text: str) -> float:
        """
        估算嵌入API调用成本（美元）
        
        注意：定价会变化；这使用通用估算
        
        Args:
            text: 要估算成本的文本
        
        Returns:
            float: 估算的成本（美元）
        """
        # 获取令牌数
        token_count = self.get_token_count(text)
        # 使用通用估算，实际成本请参考具体API提供商定价
        cost_per_1k_tokens = 0.0001  # 可根据实际API定价调整
        return (token_count / 1000) * cost_per_1k_tokens  # 按每千令牌成本计算总成本