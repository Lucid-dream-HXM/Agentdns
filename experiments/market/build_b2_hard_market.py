from __future__ import annotations

import copy
import json
import random
from pathlib import Path
from typing import Any, Dict, List, Tuple

from experiments.market.b2_hard_market_spec import (
    B2_HARD_MARKET_NAME,
    CATEGORY_LAYOUT,
    PROFILE_RULES,
    CATEGORY_SUBINTENTS,
    DESCRIPTION_TEMPLATES,
    CATEGORY_TAGS,
)

RNG = random.Random(20260420)

ROOT = Path("/home/hxm/projects/AgentDNS")
OUTPUT_DIR = ROOT / "experiments" / "outputs" / B2_HARD_MARKET_NAME
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 优先用已有的诱骗增强市场做 schema 模板；没有就退回 full_service_catalog
CATALOG_CANDIDATES = [
    ROOT / "experiments" / "outputs" / "b2_deception_enhanced" / "service_catalog.json",
    ROOT / "experiments" / "outputs" / "sample" / "full_service_catalog.json",
]

def load_base_catalog() -> Dict[str, Any]:
    for p in CATALOG_CANDIDATES:
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"[load] using base catalog: {p}")
            return data
    raise FileNotFoundError("No base catalog found. Please ensure an existing service_catalog.json is available.")

def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))

def randf(lo: float, hi: float, digits: int = 4) -> float:
    return round(RNG.uniform(lo, hi), digits)

def randi(lo: int, hi: int) -> int:
    return RNG.randint(lo, hi)

def extract_profile(svc: Dict[str, Any]) -> str:
    if svc.get("profile_name"):
        return str(svc["profile_name"])
    caps = svc.get("capabilities") or {}
    if caps.get("profile_name"):
        return str(caps["profile_name"])
    desc = str(svc.get("description") or "")
    for kw in PROFILE_RULES.keys():
        if kw in desc:
            return kw
    return ""

def build_index(base_services: List[Dict[str, Any]]) -> Dict[Tuple[str, str], List[Dict[str, Any]]]:
    idx: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for svc in base_services:
        cat = str(svc.get("category") or "")
        prof = extract_profile(svc)
        idx.setdefault((cat, prof), []).append(svc)
        idx.setdefault((cat, "__any__"), []).append(svc)
    return idx

def choose_template(index: Dict[Tuple[str, str], List[Dict[str, Any]]], category: str, profile: str) -> Dict[str, Any]:
    candidates = index.get((category, profile)) or index.get((category, "__any__"))
    if not candidates:
        raise ValueError(f"No template service found for category={category}, profile={profile}")
    return copy.deepcopy(RNG.choice(candidates))

def make_service_key(category: str, seq: int) -> str:
    return f"svc_{category}_{seq:03d}"

def make_service_name(category: str, profile: str, seq: int) -> str:
    category_cn = {
        "translation": "翻译",
        "text_summary": "摘要",
        "structured_extraction": "抽取",
        "routing_classification": "路由",
    }.get(category, category)

    profile_cn = {
        "平衡实用型": "平衡服务",
        "领域专精型": "专精服务",
        "低价基础型": "经济服务",
        "低时延响应型": "快速服务",
        "诱骗失真型": "增强服务",
        "漂移波动型": "波动服务",
        "故障脆弱型": "脆弱服务",
    }.get(profile, "服务")

    return f"{category_cn}{profile_cn}{seq}"

def make_description(category: str, profile: str, seq: int, subintent: str) -> str:
    templates = DESCRIPTION_TEMPLATES.get((category, profile))
    if not templates:
        base = f"{category}类服务{seq}，画像为{profile}，面向{subintent}场景。"
        return base

    t = RNG.choice(templates).format(idx=seq)

    # 在 description 尾部追加子意图提示，增强向量区分度
    suffix = {
        "translation": f"重点适配{subintent}场景。",
        "text_summary": f"重点适配{subintent}场景。",
        "structured_extraction": f"重点适配{subintent}场景。",
        "routing_classification": f"重点适配{subintent}场景。",
    }.get(category, f"重点适配{subintent}场景。")

    return f"{t}{suffix}"

def make_tags(category: str, profile: str, subintent: str) -> List[str]:
    base_tags = CATEGORY_TAGS.get(category, [])[:]
    tags = [f"{category}类", profile, subintent]
    tags.extend(base_tags[:3])

    # 诱骗服务需要“看起来更像能做这个任务”
    if profile == "诱骗失真型":
        if category == "translation":
            tags.extend(["术语一致", "技术文档翻译"])
        elif category == "text_summary":
            tags.extend(["结论压缩", "高密度摘要"])
        elif category == "structured_extraction":
            tags.extend(["字段完整", "实体抽取"])
        elif category == "routing_classification":
            tags.extend(["智能判别", "快速分流"])

    # 去重保序
    seen = set()
    out = []
    for t in tags:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out[:8]

def make_mock_behavior(profile: str) -> Dict[str, Any]:
    rule = PROFILE_RULES[profile]
    q_lo, q_hi = rule["quality_range"]
    c_lo, c_hi = rule["consumability_range"]
    f_lo, f_hi = rule["format_stability_range"]
    lat_lo, lat_hi = rule["latency_range_ms"]
    fail_lo, fail_hi = rule["failure_probability_range"]
    drift_lo, drift_hi = rule["drift_probability_range"]

    base_latency = randi(lat_lo, lat_hi)
    jitter = randi(60, 180)

    return {
        "base_latency_ms": base_latency,
        "latency_jitter_ms": jitter,
        "quality_range": [randf(q_lo, (q_lo + q_hi) / 2, 3), randf((q_lo + q_hi) / 2, q_hi, 3)],
        "format_stability": randf(f_lo, f_hi, 4),
        "consumability": randf(c_lo, c_hi, 4),
        "failure_probability": randf(fail_lo, fail_hi, 4),
        "drift_probability": randf(drift_lo, drift_hi, 4),
    }

def make_price(profile: str) -> float:
    lo, hi = PROFILE_RULES[profile]["price_range"]
    return randf(lo, hi, 4)

def make_trust_seed(profile: str) -> Tuple[float, int]:
    rule = PROFILE_RULES[profile]
    t_lo, t_hi = rule["trust_seed_range"]
    r_lo, r_hi = rule["rating_count_range"]
    return randf(t_lo, t_hi, 2), randi(r_lo, r_hi)

def apply_service_update(
    svc: Dict[str, Any],
    *,
    category: str,
    profile: str,
    service_key: str,
    name: str,
    description: str,
    tags: List[str],
    price: float,
    mock_behavior: Dict[str, Any],
) -> Dict[str, Any]:
    svc["service_key"] = service_key
    svc["name"] = name
    svc["category"] = category
    svc["description"] = description

    if "price" in svc:
        svc["price"] = price
    if "price_per_unit" in svc:
        svc["price_per_unit"] = price

    svc["tags"] = tags

    # 常见 URI / endpoint 字段
    if "agentdns_uri" in svc:
        svc["agentdns_uri"] = f"agentdns://experiment/market/{service_key}"
    if "agentdns_url" in svc:
        svc["agentdns_url"] = f"agentdns://experiment/market/{service_key}"
    if "agentdns_path" in svc:
        svc["agentdns_path"] = f"/mock/{service_key}"

    caps = svc.get("capabilities")
    if not isinstance(caps, dict):
        caps = {}
        svc["capabilities"] = caps

    caps["service_key"] = service_key
    caps["profile_name"] = profile
    caps["features"] = tags
    caps["mock_behavior"] = mock_behavior

    # 某些 catalog 在顶层也保留 profile_name
    svc["profile_name"] = profile

    # 协议字段兜底
    svc.setdefault("protocol", "HTTP")
    svc.setdefault("supported_protocols", ["HTTP"])
    svc.setdefault("authentication_required", False)
    svc.setdefault("pricing_model", "per_call")

    return svc

def main() -> None:
    base_catalog = load_base_catalog()
    base_services = base_catalog["services"]
    index = build_index(base_services)

    services_out: List[Dict[str, Any]] = []
    trust_seed_out: List[Dict[str, Any]] = []

    seq_by_cat: Dict[str, int] = {}

    for category, layout in CATEGORY_LAYOUT.items():
        subintents = CATEGORY_SUBINTENTS[category]
        sub_idx = 0

        for profile, count in layout.items():
            for _ in range(count):
                seq_by_cat[category] = seq_by_cat.get(category, 0) + 1
                seq = seq_by_cat[category]

                template = choose_template(index, category, profile)
                service_key = make_service_key(category, seq)
                name = make_service_name(category, profile, seq)
                subintent = subintents[sub_idx % len(subintents)]
                sub_idx += 1

                description = make_description(category, profile, seq, subintent)
                tags = make_tags(category, profile, subintent)
                price = make_price(profile)
                mock_behavior = make_mock_behavior(profile)
                trust_seed, rating_count_seed = make_trust_seed(profile)

                svc = apply_service_update(
                    template,
                    category=category,
                    profile=profile,
                    service_key=service_key,
                    name=name,
                    description=description,
                    tags=tags,
                    price=price,
                    mock_behavior=mock_behavior,
                )

                services_out.append(svc)
                trust_seed_out.append({
                    "service_key": service_key,
                    "category": category,
                    "profile_name": profile,
                    "trust_seed": trust_seed,
                    "rating_count_seed": rating_count_seed,
                })

    catalog_out = {
        "market_name": B2_HARD_MARKET_NAME,
        "service_count": len(services_out),
        "services": services_out,
    }

    with open(OUTPUT_DIR / "service_catalog.json", "w", encoding="utf-8") as f:
        json.dump(catalog_out, f, ensure_ascii=False, indent=2)

    with open(OUTPUT_DIR / "trust_seed.json", "w", encoding="utf-8") as f:
        json.dump({
            "market_name": B2_HARD_MARKET_NAME,
            "service_count": len(trust_seed_out),
            "items": trust_seed_out,
        }, f, ensure_ascii=False, indent=2)

    # 打印汇总
    from collections import Counter
    cat_counter = Counter()
    prof_counter = Counter()
    cat_prof_counter = Counter()

    for s in services_out:
        cat = s["category"]
        prof = extract_profile(s)
        cat_counter[cat] += 1
        prof_counter[prof] += 1
        cat_prof_counter[(cat, prof)] += 1

    print(f"[done] market_name={B2_HARD_MARKET_NAME}")
    print(f"[done] service_count={len(services_out)}")
    print("[done] category counts:")
    for cat, n in cat_counter.items():
        print(" ", cat, n)
    print("[done] profile counts:")
    for prof, n in prof_counter.items():
        print(" ", prof, n)
    print("[done] output files:")
    print(" ", OUTPUT_DIR / "service_catalog.json")
    print(" ", OUTPUT_DIR / "trust_seed.json")

if __name__ == "__main__":
    main()