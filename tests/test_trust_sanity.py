#!/usr/bin/env python3
import requests
import time

BASE = "http://127.0.0.1:8000/api/v1"
TOKEN = "agent_exp_quality_01"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
svc_id = 125

def get_trust(sid):
    r = requests.get(f"{BASE}/client/services/{sid}/trust-summary", headers=HEADERS, timeout=10)
    if r.status_code == 200:
        return r.json()
    return {"error": r.status_code, "text": r.text[:100]}

def post_review(sid, uid, rating, outcome="success"):
    p = {
        "service_id": sid, "usage_id": uid, "outcome": outcome, "rating": rating,
        "comment": f"sanity_{rating}", "task_fit": rating, "output_quality": rating,
        "protocol_adherence": 5, "would_reuse": True,
        "task_context": {"task_id": "trust_sanity", "step_id": 1}
    }
    r = requests.post(f"{BASE}/reviews/", json=p, headers=HEADERS, timeout=10)
    return r.status_code

print("=" * 60)
print("Trust Sanity Check - 测试1: 单服务连续评价")
print("=" * 60)

t0 = get_trust(svc_id)
print(f"[初始] {t0}")

print("\n--- 5次高评价 (rating=5) ---")
for i in range(5):
    print(f"  r{i+1}: {post_review(svc_id, 8000+i, 5)}")
t1 = get_trust(svc_id)
print(f"[高评价后] {t1}")

print("\n--- 5次低评价 (rating=1, outcome=failure) ---")
for i in range(5):
    print(f"  r{i+1}: {post_review(svc_id, 8100+i, 1, 'failure')}")
t2 = get_trust(svc_id)
print(f"[低评价后] {t2}")

if all(isinstance(x, dict) and 'trust_score' in x for x in [t0, t1, t2]):
    d1 = t1['trust_score'] - t0['trust_score']
    d2 = t2['trust_score'] - t1['trust_score']
    print(f"\n高评价delta: {d1:+.4f} | 低评价delta: {d2:+.4f}")
    if abs(d1) < 0.01 and abs(d2) < 0.01:
        print("⚠️  TRUST几乎不变 → 机制未真正生效")
    elif d1 > 0 and d2 < 0:
        print("✅  TRUST方向正确 → 机制活着")
    else:
        print("❓  方向异常，需检查")