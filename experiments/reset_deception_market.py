#!/usr/bin/env python3
"""
B2 诱骗增强市场重置脚本：
1. 清空 DB 中现有服务（org_id=1）
2. 从 b2_deception_enhanced/service_catalog.json 重新导入服务
3. 重置 experiment 服务的 trust 历史（reviews + trust_stats）
"""
import json
import sys
import os

sys.path.insert(0, '/home/hxm/projects/AgentDNS/agentdns-backend')
os.chdir('/home/hxm/projects/AgentDNS/agentdns-backend')

from sqlalchemy import func
from app.database import SessionLocal
from app.models.service import Service
from app.models.review import ServiceReview, ServiceTrustStats
from app.models.usage import Usage
from app.models.organization import Organization


def load_catalog(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def delete_existing_services(db: SessionLocal, org_id: int) -> int:
    count = db.query(func.count(Service.id)).filter(Service.organization_id == org_id).scalar()
    db.query(Service).filter(Service.organization_id == org_id).delete(synchronize_session=False)
    db.commit()
    print(f"已删除 org_id={org_id} 的 {count} 个服务")
    return count


def reset_trust_history(db: SessionLocal) -> dict:
    deleted_reviews = db.query(func.count(ServiceReview.id)).scalar()
    db.query(ServiceReview).delete(synchronize_session=False)
    deleted_stats = db.query(func.count(ServiceTrustStats.service_id)).scalar()
    db.query(ServiceTrustStats).delete(synchronize_session=False)
    deleted_usage = db.query(func.count(Usage.id)).scalar()
    db.query(Usage).delete(synchronize_session=False)
    db.commit()
    print(f"已删除 {deleted_reviews} 条 reviews, {deleted_stats} 条 trust_stats, {deleted_usage} 条 usage")
    return {'reviews': deleted_reviews, 'trust_stats': deleted_stats, 'usage': deleted_usage}


def import_deception_catalog(db: SessionLocal, catalog: dict, org_id: int) -> int:
    count = 0
    for item in catalog['services']:
        service_key = item['service_key']
        name = item['service_name']
        category = item['category']
        description = item['description']
        price = item['price']
        tags = item.get('tags', [])
        profile_name = item['profile_name']

        existing = db.query(Service).filter(
            Service.name == name,
            Service.organization_id == org_id
        ).first()
        if existing:
            print(f"  跳过已存在: {name}")
            continue

        service = Service(
            name=name,
            category=category,
            description=description,
            is_active=True,
            is_public=True,
            endpoint_url="http://localhost:9001/mock",
            protocol="HTTP",
            authentication_required=False,
            agentdns_path=f"/mock/{service_key}",
            agentdns_uri=f"agentdns://experiment/market/{service_key}",
            http_method="POST",
            http_mode="sync",
            input_description=json.dumps({"task": "任务输入"}),
            output_description=json.dumps({"result": "任务输出"}),
            service_api_key="",
            pricing_model="per_call",
            price_per_unit=price,
            currency="USD",
            tags=tags,
            version="1.0.0",
            capabilities={
                "service_key": service_key,
                "profile_name": profile_name,
                "features": tags,
            },
            organization_id=org_id
        )
        db.add(service)
        count += 1
        print(f"  导入: {name} ({service_key}) price={price:.4f} profile={profile_name}")

    db.commit()
    return count


def main():
    CATALOG_PATH = '/home/hxm/projects/AgentDNS/experiments/outputs/b2_deception_enhanced/service_catalog.json'
    ORG_ID = 1

    catalog = load_catalog(CATALOG_PATH)
    print(f"加载诱骗增强市场: {catalog['service_count']} services, deception_enhanced={catalog.get('deception_enhanced')}")

    deceptive = [s for s in catalog['services'] if s.get('profile_name') == '诱骗失真型']
    low_latency = [s for s in catalog['services'] if s.get('profile_name') == '低时延响应型']
    print(f"诱骗失真型: {len(deceptive)}, 低时延响应型: {len(low_latency)}")

    db = SessionLocal()

    print("\n--- Step 1: 重置 trust 历史 ---")
    trust_reset = reset_trust_history(db)

    print("\n--- Step 2: 删除现有服务 ---")
    delete_existing_services(db, ORG_ID)

    print("\n--- Step 3: 导入诱骗增强市场 ---")
    imported = import_deception_catalog(db, catalog, ORG_ID)
    print(f"\n成功导入 {imported} 个服务")

    remaining = db.query(func.count(Service.id)).filter(Service.organization_id == ORG_ID).scalar()
    print(f"DB 中现有 org_id={ORG_ID} 服务数: {remaining}")

    db.close()
    print("\n完成.")


if __name__ == '__main__':
    main()
