#!/usr/bin/env python3
"""
测试嵌入API连接
验证火山方舟Doubao-embedding-vision API是否正常工作
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.embedding_service import EmbeddingService
from app.core.config import settings

def test_embedding_api():
    """测试嵌入API连接"""
    print("=== 测试嵌入API连接 ===")
    
    try:
        # 创建嵌入服务实例
        embedding_service = EmbeddingService()
        print("[SUCCESS] 嵌入服务初始化成功!")
        
        # 测试文本
        test_text = "This is a test text for embedding"
        
        # 生成嵌入
        embedding = embedding_service._get_embedding(test_text)
        print("[SUCCESS] API 连接成功!")
        
        # 检查向量维度
        vector_dim = len(embedding)
        print(f"[SUCCESS] 向量维度: {vector_dim}")
        
        # 验证维度是否匹配配置
        expected_dim = settings.MILVUS_DIMENSION
        if vector_dim == expected_dim:
            print(f"[SUCCESS] 维度匹配: YES (期望: {expected_dim}, 实际: {vector_dim})")
        else:
            print(f"[ERROR] 维度不匹配: NO (期望: {expected_dim}, 实际: {vector_dim})")
        
        # 测试批量嵌入
        test_texts = ["Test 1", "Test 2", "Test 3"]
        embeddings = embedding_service.batch_create_embeddings(test_texts)
        print(f"[SUCCESS] 批量嵌入测试成功，生成了 {len(embeddings)} 个嵌入")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] 测试失败: {e}")
        return False

if __name__ == "__main__":
    success = test_embedding_api()
    if success:
        print("\n=== 所有测试通过! ===")
        sys.exit(0)
    else:
        print("\n=== 测试失败! ===")
        sys.exit(1)
