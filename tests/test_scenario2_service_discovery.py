#!/usr/bin/env python3
"""
场景2：服务注册与发现测试脚本
"""

import requests
import json

BASE_URL = "http://localhost:8001/api/v1"

def test_user_login():
    """测试用户登录"""
    print("=== 测试用户登录 ===")
    url = f"{BASE_URL}/auth/login"
    data = {
        "username": "testuser",
        "password": "password123"
    }
    response = requests.post(url, json=data)
    print(f"登录响应状态码: {response.status_code}")
    assert response.status_code == 200, f"登录失败: {response.text}"
    return response.json()

def test_create_service(access_token, organization_id):
    """测试注册新服务"""
    print("\n=== 测试注册新服务 ===")
    url = f"{BASE_URL}/services/"
    headers = {"Authorization": f"Bearer {access_token}"}
    data = {
        "name": "test-service-scenario2",
        "category": "ai",
        "description": "A test AI service for scenario 2",
        "version": "1.0.0",
        "is_public": True,
        "endpoint_url": "https://api.example.com/test-service",
        "protocol": "http",
        "authentication_required": False,
        "pricing_model": "per_request",
        "price_per_unit": 0.05,
        "currency": "USD",
        "tags": ["ai", "test", "scenario2"],
        "agentdns_path": "test-org/ai/test-service",
        "http_method": "POST",
        "http_mode": "sync"
    }
    params = {"organization_id": organization_id}
    response = requests.post(url, json=data, headers=headers, params=params)
    print(f"注册服务响应状态码: {response.status_code}")
    print(f"注册服务响应内容: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 200, f"注册服务失败: {response.text}"
    return response.json()

def test_service_discovery(access_token):
    """测试服务发现"""
    print("\n=== 测试服务发现 ===")
    url = f"{BASE_URL}/discovery/search"
    headers = {"Authorization": f"Bearer {access_token}"}
    data = {
        "query": "AI test service",
        "top_k": 5,
        "filters": {"category": "ai"}
    }
    response = requests.post(url, json=data, headers=headers)
    print(f"服务发现响应状态码: {response.status_code}")
    print(f"服务发现响应内容: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 200, f"服务发现失败: {response.text}"
    return response.json()

def test_get_service_detail(access_token, service_id):
    """测试获取服务详情"""
    print("\n=== 测试获取服务详情 ===")
    url = f"{BASE_URL}/services/{service_id}"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    print(f"获取服务详情响应状态码: {response.status_code}")
    print(f"获取服务详情响应内容: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 200, f"获取服务详情失败: {response.text}"
    return response.json()

def main():
    """主测试函数"""
    print("开始场景2测试：服务注册与发现")
    print("=" * 60)
    
    try:
        # 1. 登录获取令牌
        login_response = test_user_login()
        access_token = login_response["access_token"]
        
        # 2. 获取用户组织
        url = f"{BASE_URL}/organizations/my"
        headers = {"Authorization": f"Bearer {access_token}"}
        org_response = requests.get(url, headers=headers)
        organizations = org_response.json()
        organization_id = organizations[0]["id"]
        print(f"使用组织ID: {organization_id}")
        
        # 3. 注册新服务
        service = test_create_service(access_token, organization_id)
        service_id = service["id"]
        
        # 4. 测试服务发现
        discovery_result = test_service_discovery(access_token)
        
        # 5. 获取服务详情
        service_detail = test_get_service_detail(access_token, service_id)
        
        print("\n" + "=" * 60)
        print("场景2测试完成，所有测试通过！")
        print(f"注册服务: {service['name']}")
        print(f"服务ID: {service_id}")
        print(f"发现服务数量: {discovery_result['total']}")
        
    except Exception as e:
        print(f"\n测试失败: {str(e)}")
        raise

if __name__ == "__main__":
    main()
