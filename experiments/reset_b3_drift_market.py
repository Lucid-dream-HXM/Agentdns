
from __future__ import annotations
import json
from pathlib import Path
from sqlalchemy import text, inspect
from app.database import SessionLocal
from app.models.service import Service

ROOT = Path("/home/hxm/projects/AgentDNS")
CATALOG_PATH = ROOT / "experiments" / "outputs" / "b3_drift_inclass_market_v1" / "service_catalog.json"
ENDPOINT_URL = "http://localhost:9002/mock"

def main():
    db = SessionLocal()
    db.execute(text("DELETE FROM service_reviews WHERE service_id IN (SELECT id FROM services WHERE agentdns_uri LIKE '%experiment/market/%')"))
    db.execute(text("DELETE FROM service_trust_stats WHERE service_id IN (SELECT id FROM services WHERE agentdns_uri LIKE '%experiment/market/%')"))
    try:
        db.execute(text("DELETE FROM usage_records WHERE service_id IN (SELECT id FROM services WHERE agentdns_uri LIKE '%experiment/market/%')"))
    except Exception:
        pass
    db.execute(text("DELETE FROM services WHERE agentdns_uri LIKE '%experiment/market/%'"))
    db.commit()

    data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    services = data["services"]
    cols = {c.name for c in inspect(Service).columns}
    inserted = 0
    for item in services:
        svc = Service()
        values = {
            "name": item.get("name"),
            "description": item.get("description"),
            "category": item.get("category"),
            "service_key": item.get("service_key"),
            "agentdns_uri": item.get("agentdns_uri") or item.get("agentdns_url") or f"agentdns://experiment/market/{item.get('service_key')}",
            "agentdns_path": item.get("agentdns_path") or f"/mock/{item.get('service_key')}",
            "endpoint_url": ENDPOINT_URL,
            "protocol": item.get("protocol", "HTTP"),
            "supported_protocols": item.get("supported_protocols", ["HTTP"]),
            "authentication_required": item.get("authentication_required", False),
            "pricing_model": item.get("pricing_model", "per_call"),
            "price_per_unit": item.get("price_per_unit", item.get("price")),
            "currency": item.get("currency", "USD"),
            "tags": item.get("tags", []),
            "capabilities": item.get("capabilities", {}),
            "is_active": item.get("is_active", True),
            "is_public": item.get("is_public", True),
            "organization_id": item.get("organization_id", 1),
            "version": item.get("version", "1.0.0"),
            "http_method": item.get("http_method", "POST"),
            "input_description": item.get("input_description", '{"task":"任务输入"}'),
            "output_description": item.get("output_description", '{"result":"任务输出"}'),
        }
        for k, v in values.items():
            if k in cols:
                setattr(svc, k, v)
        db.add(svc); inserted += 1
    db.commit()
    print(f"成功导入 {inserted} 个服务")
    count = db.query(Service).filter(Service.organization_id == 1).count()
    print(f"DB 中现有 org_id=1 服务数: {count}")
    db.close()
    print("完成.")

if __name__ == "__main__":
    main()
