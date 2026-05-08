#!/usr/bin/env python3
"""
场景4：服务评价与信任分闭环测试脚本

测试目标：
1. 调用服务
2. 从响应头中拿到 usage_id
3. 提交评价
4. 查询 trust 摘要
5. 再次搜索，观察 trust 字段是否可见
"""

import requests
import json
import sys
from pathlib import Path

project_root = Path(__file__).parent / "agentdns-backend"
sys.path.insert(0, str(project_root))

BASE_URL = "http://localhost:8001/api/v1"

USERNAME = "reviewer"
PASSWORD = "password123"


def login():
    """
    登录并获取访问令牌
    """
    url = f"{BASE_URL}/auth/login"
    data = {
        "username": USERNAME,
        "password": PASSWORD
    }
    resp = requests.post(url, json=data)
    assert resp.status_code == 200, f"登录失败: {resp.text}"
    token = resp.json()["access_token"]
    return token


def call_service(token: str):
    """
    调用测试服务，并返回 usage_id / request_id
    """
    url = f"{BASE_URL}/client/services/call"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "agentdns_url": "agentdns://test-org-2/general/example-api",
        "input_data": {"text": "hello trust review"},
        "method": "POST"
    }

    resp = requests.post(url, headers=headers, json=data)

    usage_id = resp.headers.get("X-AgentDNS-Usage-ID")
    request_id = resp.headers.get("X-AgentDNS-Request-ID")

    print(f"[CALL] status={resp.status_code}")
    print(f"[CALL] usage_id={usage_id}, request_id={request_id}")
    print(f"[CALL] body={resp.text}")

    assert usage_id is not None, "调用响应头中未返回 usage_id"
    assert request_id is not None, "调用响应头中未返回 request_id"

    return int(usage_id)


def submit_review(token: str, usage_id: int):
    """
    针对本次调用提交评价
    """
    usage_url = f"{BASE_URL}/billing/usage"
    headers = {"Authorization": f"Bearer {token}"}
    usage_resp = requests.get(usage_url, headers=headers)
    assert usage_resp.status_code == 200, f"查询usage失败: {usage_resp.text}"

    usage_records = usage_resp.json()
    target_usage = None
    for item in usage_records:
        if item["id"] == usage_id:
            target_usage = item
            break

    assert target_usage is not None, f"未找到 usage_id={usage_id} 的使用记录"
    service_id = target_usage["service_id"]

    review_url = f"{BASE_URL}/reviews/"
    status_code = target_usage.get("status_code")
    error_message = target_usage.get("error_message")

    if status_code and 200 <= status_code < 300:
        final_state = "success"
    elif status_code and 400 <= status_code < 500:
        final_state = "partial"
    elif error_message:
        final_state = "fail"
    else:
        final_state = "success"

    if final_state == "success":
        review_data = {
            "usage_id": usage_id,
            "outcome": "success",
            "task_fit": 5,
            "output_quality": 4,
            "protocol_adherence": 5,
            "would_reuse": True,
            "cost_satisfaction": 4,
            "feedback_text": "成功路径闭环测试评价",
            "evidence": {
                "schema_valid": True,
                "downstream_success": True
            }
        }
    elif final_state == "partial":
        review_data = {
            "usage_id": usage_id,
            "outcome": "partial",
            "task_fit": 3,
            "output_quality": 3,
            "protocol_adherence": 4,
            "would_reuse": False,
            "cost_satisfaction": 3,
            "feedback_text": "部分完成路径闭环测试评价",
            "evidence": {
                "schema_valid": True,
                "downstream_success": False
            }
        }
    else:
        review_data = {
            "usage_id": usage_id,
            "outcome": "fail",
            "task_fit": 1,
            "output_quality": 1,
            "protocol_adherence": 2,
            "would_reuse": False,
            "cost_satisfaction": 2,
            "feedback_text": "失败路径闭环测试评价",
            "evidence": {
                "schema_valid": False,
                "downstream_success": False
            }
        }

    review_resp = requests.post(review_url, headers=headers, json=review_data)
    print(f"[REVIEW] status={review_resp.status_code}")
    print(f"[REVIEW] body={review_resp.text}")

    assert review_resp.status_code == 200, f"提交评价失败: {review_resp.text}"

    return service_id


def check_trust_summary(token: str, service_id: int):
    """
    查询服务信任摘要
    """
    url = f"{BASE_URL}/reviews/services/{service_id}/summary"
    headers = {"Authorization": f"Bearer {token}"}

    resp = requests.get(url, headers=headers)
    print(f"[SUMMARY] status={resp.status_code}")
    print(f"[SUMMARY] body={resp.text}")

    assert resp.status_code == 200, f"查询信任摘要失败: {resp.text}"

    data = resp.json()
    assert "trust_score" in data
    assert "success_rate" in data
    assert "rating_count" in data

    return data


def search_services(token: str):
    """
    再次搜索，观察返回结果是否带 trust 字段
    """
    url = f"{BASE_URL}/discovery/search"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "query": "text service",
        "limit": 10,
        "sort_by": "balanced",
        "include_trust": True
    }

    resp = requests.post(url, headers=headers, json=data)
    print(f"[SEARCH] status={resp.status_code}")
    print(f"[SEARCH] body={resp.text}")

    assert resp.status_code == 200, f"搜索失败: {resp.text}"

    result = resp.json()
    assert "tools" in result

    if result["tools"]:
        first_tool = result["tools"][0]
        assert "trust_score" in first_tool
        assert "success_rate" in first_tool
        assert "rating_count" in first_tool

    return result


def main():
    token = login()
    usage_id = call_service(token)
    service_id = submit_review(token, usage_id)
    summary = check_trust_summary(token, service_id)
    search_result = search_services(token)

    print("\n========== 测试完成 ==========")
    print(f"service_id={service_id}")
    print(f"trust_score={summary['trust_score']}")
    print(f"rating_count={summary['rating_count']}")
    print(f"search_results={len(search_result.get('tools', []))}")


if __name__ == "__main__":
    main()