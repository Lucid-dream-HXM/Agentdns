#!/usr/bin/env python3
"""
场景1：用户注册登录与组织管理测试脚本
"""

import requests
import json
import time

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
    print(f"登录响应内容: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 200, f"登录失败: {response.text}"
    return response.json()

def test_create_organization(access_token):
    """测试创建组织"""
    print("\n=== 测试创建组织 ===")
    url = f"{BASE_URL}/organizations/"
    headers = {"Authorization": f"Bearer {access_token}"}
    timestamp = int(time.time())
    data = {
        "name": f"test-org-scenario1-{timestamp}",
        "domain": f"test-scenario1-{timestamp}.org",
        "display_name": f"Test Organization Scenario 1",
        "description": "A test organization for scenario 1",
        "website": "https://test-scenario1.org"
    }
    response = requests.post(url, json=data, headers=headers)
    print(f"创建组织响应状态码: {response.status_code}")
    print(f"创建组织响应内容: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 200, f"创建组织失败: {response.text}"
    return response.json()

def test_get_user_organizations(access_token):
    """测试获取用户组织列表"""
    print("\n=== 测试获取用户组织列表 ===")
    url = f"{BASE_URL}/organizations/my"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    print(f"获取组织列表响应状态码: {response.status_code}")
    print(f"获取组织列表响应内容: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 200, f"获取组织列表失败: {response.text}"
    return response.json()

def main():
    """主测试函数"""
    print("开始场景1测试：用户注册登录与组织管理")
    print("=" * 60)
    
    try:
        # 1. 登录获取令牌
        login_response = test_user_login()
        access_token = login_response["access_token"]
        
        # 2. 创建新组织
        organization = test_create_organization(access_token)
        
        # 3. 获取用户组织列表
        organizations = test_get_user_organizations(access_token)
        
        print("\n" + "=" * 60)
        print("场景1测试完成，所有测试通过！")
        print(f"登录用户: {login_response['user']['username']}")
        print(f"创建组织: {organization['name']}")
        print(f"用户组织数量: {len(organizations)}")
        
    except Exception as e:
        print(f"\n测试失败: {str(e)}")
        raise

if __name__ == "__main__":
    main()
