#!/usr/bin/env python3
"""
将 service_seed_payload.json 导入到数据库
"""
import json
import sys
import os

sys.path.insert(0, '/home/hxm/projects/AgentDNS/agentdns-backend')
os.chdir('/home/hxm/projects/AgentDNS/agentdns-backend')

from app.database import SessionLocal
from app.models.service import Service
from app.models.organization import Organization


def load_seed_payload(path: str) -> list:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def import_services(seed_payload: list, org_id: int) -> int:
    db = SessionLocal()
    count = 0

    for item in seed_payload:
        service_key = item['service_key']
        name = item['name']
        category = item['category']
        description = item['description']
        price = item['price']
        tags = item['tags']
        profile_name = item['profile_name']
        mock_behavior = item['mock_behavior']

        agentdns_uri = f"agentdns://experiment/market/{service_key}"

        existing = db.query(Service).filter(
            Service.name == name,
            Service.organization_id == org_id
        ).first()
        if existing:
            print(f"跳过已存在: {name}")
            continue

        service = Service(
            name=name,
            category=category,
            agentdns_uri=agentdns_uri,
            description=description,
            version="1.0.0",
            is_active=True,
            is_public=True,
            endpoint_url="http://localhost:9002/mock",
            protocol="HTTP",
            authentication_required=False,
            agentdns_path=f"/mock/{service_key}",
            http_method="POST",
            http_mode="sync",
            input_description=json.dumps({"task": "任务输入"}),
            output_description=json.dumps({"result": "任务输出"}),
            service_api_key="",
            pricing_model="per_call",
            price_per_unit=price,
            currency="USD",
            tags=tags,
            capabilities={
                "service_key": service_key,
                "profile_name": profile_name,
                "features": tags,
                "mock_behavior": mock_behavior
            },
            organization_id=org_id
        )
        db.add(service)

        count += 1
        print(f"导入: {name} ({service_key})")

    db.commit()
    db.close()
    return count


def main():
    if len(sys.argv) < 2:
        print("用法: python import_market_services.py <seed_payload.json>")
        return
    seed_path = sys.argv[1]

    seed_payload = load_seed_payload(seed_path)
    print(f"加载了 {len(seed_payload)} 个服务")

    db = SessionLocal()
    org = db.query(Organization).filter(Organization.name.like('%experiment%')).first()
    if not org:
        org = db.query(Organization).first()
    if not org:
        print("错误: 没有找到组织")
        db.close()
        return
    org_id = org.id
    print(f"使用组织: {org.name} (id={org_id})")
    db.close()

    count = import_services(seed_payload, org_id)
    print(f"\n成功导入 {count} 个服务")


if __name__ == '__main__':
    main()