
from __future__ import annotations
from app.database import SessionLocal
from app.models.service import Service
from app.services.embedding_service import EmbeddingService
from app.services.milvus_service import get_milvus_service

def build_text(svc: Service) -> str:
    caps = svc.capabilities or {}
    profile = caps.get("profile_name") or ""
    features = caps.get("features") or []
    tags = svc.tags or []
    parts = [svc.name or "", svc.description or "", f"category={svc.category or ''}", f"profile={profile}", " ".join(tags), " ".join(features)]
    return " | ".join([p for p in parts if p])

def main():
    db = SessionLocal()
    embedding_service = EmbeddingService()
    milvus_service = get_milvus_service()
    coll = milvus_service.collection
    probe = embedding_service.create_query_embedding("b3 drift market vector probe")
    embed_dim = len(probe)
    schema_dim = None
    for field in coll.schema.fields:
        if field.name == 'embedding':
            schema_dim = int(field.params.get('dim')); break
    if embed_dim != schema_dim:
        raise SystemExit(f"dim mismatch: embed_dim={embed_dim}, milvus_dim={schema_dim}")
    services = db.query(Service).filter(Service.agentdns_uri.like('%experiment/market/%')).all()
    rows=[]; ids=[]
    for svc in services:
        text = build_text(svc)
        vec = embedding_service.create_query_embedding(text)
        rows.append({"service_id": int(svc.id), "service_name": svc.name, "category": svc.category, "organization_id": int(svc.organization_id) if svc.organization_id else 1, "embedding": vec})
        ids.append(int(svc.id))
    if ids:
        try: coll.delete(f"service_id in {ids}")
        except Exception: pass
    coll.insert(rows); coll.flush()
    print(f"done: inserted_vectors={len(rows)}")
    db.close()

if __name__ == "__main__":
    main()
