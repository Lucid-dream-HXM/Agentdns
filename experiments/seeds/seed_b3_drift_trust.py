
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from sqlalchemy import inspect
from app.database import SessionLocal
from app.models.service import Service
from app.models.review import ServiceTrustStats

ROOT = Path("/home/hxm/projects/AgentDNS")
TRUST_PATH = ROOT / "experiments" / "outputs" / "b3_drift_inclass_market_v1" / "trust_seed.json"

def main():
    data = json.loads(TRUST_PATH.read_text(encoding="utf-8"))
    items = data["items"]
    db = SessionLocal()
    cols = {c.name for c in inspect(ServiceTrustStats).columns}
    inserted=0; updated=0; missing=0
    for item in items:
        svc = db.query(Service).filter(Service.agentdns_uri.like(f"%/{item['service_key']}")).first()
        if not svc:
            missing += 1
            continue
        row = db.query(ServiceTrustStats).filter(ServiceTrustStats.service_id == svc.id).first()
        if not row:
            row = ServiceTrustStats(service_id=svc.id); db.add(row); inserted += 1
        else:
            updated += 1
        if "trust_score" in cols: row.trust_score = float(item["trust_seed"])
        if "rating_count" in cols: row.rating_count = int(item["rating_count_seed"])
        if "subjective_score" in cols: row.subjective_score = float(item["trust_seed"])
        if "objective_score" in cols: row.objective_score = float(item["trust_seed"])
        if "usage_count" in cols: row.usage_count = 0
        if "updated_at" in cols: row.updated_at = datetime.utcnow()
    db.commit(); db.close()
    print(f"done: inserted={inserted}, updated={updated}, missing={missing}, total={len(items)}")

if __name__ == "__main__":
    main()
