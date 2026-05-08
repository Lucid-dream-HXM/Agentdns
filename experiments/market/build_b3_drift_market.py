
from __future__ import annotations
import copy, json, random
from pathlib import Path
from typing import Any, Dict, List, Tuple
from experiments.market.b3_drift_market_spec import (
    B3_DRIFT_MARKET_NAME, CATEGORY_LAYOUT, PROFILE_RULES, CATEGORY_SUBINTENTS,
    DESCRIPTION_TEMPLATES, CATEGORY_TAGS, DRIFT_MODES, DRIFT_PHASE_RULES,
)

RNG = random.Random(20260421)

DRIFT_LURE_LEVELS = ["high", "medium", "low"]

ROOT = Path("/home/hxm/projects/AgentDNS")
OUTPUT_DIR = ROOT / "experiments" / "outputs" / B3_DRIFT_MARKET_NAME
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CATALOG_CANDIDATES = [
    ROOT / "experiments" / "outputs" / "b2_hard_inclass_deception_market_v1" / "service_catalog.json",
    ROOT / "experiments" / "outputs" / "b2_deception_enhanced" / "service_catalog.json",
    ROOT / "experiments" / "outputs" / "sample" / "full_service_catalog.json",
]

def load_base_catalog():
    for p in CATALOG_CANDIDATES:
        if p.exists():
            print(f"[load] using base catalog: {p}")
            return json.loads(p.read_text(encoding="utf-8"))
    raise FileNotFoundError("No base catalog found.")

def randf(lo, hi, digits=4): return round(RNG.uniform(lo, hi), digits)
def randi(lo, hi): return RNG.randint(lo, hi)

def extract_profile(svc):
    if svc.get("profile_name"): return str(svc["profile_name"])
    caps = svc.get("capabilities") or {}
    if caps.get("profile_name"): return str(caps["profile_name"])
    desc = str(svc.get("description") or "")
    for kw in PROFILE_RULES.keys():
        if kw in desc: return kw
    return ""

def build_index(base_services):
    idx = {}
    for svc in base_services:
        cat = str(svc.get("category") or "")
        prof = extract_profile(svc)
        idx.setdefault((cat, prof), []).append(svc)
        idx.setdefault((cat, "__any__"), []).append(svc)
    return idx

def choose_template(index, category, profile):
    candidates = index.get((category, profile)) or index.get((category, "__any__"))
    if not candidates:
        raise ValueError(f"No template service for category={category}, profile={profile}")
    return copy.deepcopy(RNG.choice(candidates))

def make_service_key(category, seq): return f"svc_{category}_{seq:03d}"

def make_service_name(category, profile, seq):
    cat_cn = {"translation":"翻译","text_summary":"摘要","structured_extraction":"抽取","routing_classification":"路由"}.get(category, category)
    prof_cn = {"平衡实用型":"平衡服务","领域专精型":"专精服务","低价基础型":"经济服务","低时延响应型":"快速服务","诱骗失真型":"增强服务","漂移波动型":"波动服务","故障脆弱型":"脆弱服务"}.get(profile, "服务")
    return f"{cat_cn}{prof_cn}{seq}"

def make_description(category, profile, seq, subintent):
    templates = DESCRIPTION_TEMPLATES.get((category, profile))
    if not templates:
        return f"{category}类服务{seq}，画像为{profile}，面向{subintent}场景。"
    return f"{RNG.choice(templates).format(idx=seq)}重点适配{subintent}场景。"

def make_tags(category, profile, subintent, lure_level=None):
    base_tags = CATEGORY_TAGS.get(category, [])[:]
    tags = [f"{category}类", profile, subintent] + base_tags[:3]

    if profile == "漂移波动型":
        if category == "translation":
            if lure_level == "high":
                tags += ["将这段中文翻译成英文", "术语一致", "英译中", "中译英"]
            elif lure_level == "medium":
                tags += ["中英互译", "技术文档翻译", "会议纪要翻译"]
            else:
                tags += ["翻译处理", "文本转换"]
        elif category == "text_summary":
            if lure_level == "high":
                tags += ["请对以下长文本进行摘要", "三句摘要", "信息密度高", "结论导向摘要"]
            elif lure_level == "medium":
                tags += ["文本摘要", "项目摘要", "研究摘要"]
            else:
                tags += ["摘要处理", "压缩概括"]
        elif category == "structured_extraction":
            if lure_level == "high":
                tags += ["抽取时间、地点、人物", "会议字段抽取", "实验字段抽取", "结构化字段"]
            elif lure_level == "medium":
                tags += ["实体抽取", "字段映射", "工单字段"]
            else:
                tags += ["信息抽取", "要素提取"]

    seen = set()
    out = []
    for t in tags:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out[:8]

def make_mock_behavior(profile, drift_mode=None):
    rule = PROFILE_RULES[profile]
    q_lo, q_hi = rule["quality_range"]
    c_lo, c_hi = rule["consumability_range"]
    f_lo, f_hi = rule["format_stability_range"]
    lat_lo, lat_hi = rule["latency_range_ms"]
    fail_lo, fail_hi = rule["failure_probability_range"]
    drift_lo, drift_hi = rule["drift_probability_range"]
    mb = {
        "base_latency_ms": randi(lat_lo, lat_hi),
        "latency_jitter_ms": randi(60, 180),
        "quality_range": [randf(q_lo, (q_lo + q_hi)/2, 3), randf((q_lo + q_hi)/2, q_hi, 3)],
        "format_stability": randf(f_lo, f_hi, 4),
        "consumability": randf(c_lo, c_hi, 4),
        "failure_probability": randf(fail_lo, fail_hi, 4),
        "drift_probability": randf(drift_lo, drift_hi, 4),
    }
    if profile == "漂移波动型":
        mode = drift_mode or RNG.choice(DRIFT_MODES)
        phase = DRIFT_PHASE_RULES[mode]
        mb["drift_mode"] = mode
        mb["phase_quality"] = phase["phase_quality"]
        mb["phase_consumability"] = phase["phase_consumability"]
        mb["phase_format_stability"] = phase["phase_format_stability"]
    return mb

def make_price(profile):
    lo, hi = PROFILE_RULES[profile]["price_range"]
    return randf(lo, hi, 4)

def make_trust_seed(profile):
    rule = PROFILE_RULES[profile]
    t_lo, t_hi = rule["trust_seed_range"]
    r_lo, r_hi = rule["rating_count_range"]
    return randf(t_lo, t_hi, 2), randi(r_lo, r_hi)

def apply_service_update(svc, category, profile, service_key, name, description, tags, price, mock_behavior):
    svc["service_key"] = service_key
    svc["name"] = name
    svc["category"] = category
    svc["description"] = description
    if "price" in svc: svc["price"] = price
    if "price_per_unit" in svc: svc["price_per_unit"] = price
    svc["tags"] = tags
    svc["profile_name"] = profile
    if "agentdns_uri" in svc: svc["agentdns_uri"] = f"agentdns://experiment/market/{service_key}"
    if "agentdns_url" in svc: svc["agentdns_url"] = f"agentdns://experiment/market/{service_key}"
    if "agentdns_path" in svc: svc["agentdns_path"] = f"/mock/{service_key}"
    caps = svc.get("capabilities") if isinstance(svc.get("capabilities"), dict) else {}
    svc["capabilities"] = caps
    caps["service_key"] = service_key
    caps["profile_name"] = profile
    caps["features"] = tags
    caps["mock_behavior"] = mock_behavior
    svc.setdefault("protocol", "HTTP")
    svc.setdefault("supported_protocols", ["HTTP"])
    svc.setdefault("authentication_required", False)
    svc.setdefault("pricing_model", "per_call")
    svc.setdefault("currency", "USD")
    return svc

def main():
    base_catalog = load_base_catalog()
    index = build_index(base_catalog["services"])
    services_out=[]; trust_seed_out=[]; seq_by_cat={}
    for category, layout in CATEGORY_LAYOUT.items():
        subintents = CATEGORY_SUBINTENTS[category]
        sub_idx = 0; drift_mode_idx = 0
        for profile, count in layout.items():
            for _ in range(count):
                seq_by_cat[category] = seq_by_cat.get(category, 0) + 1
                seq = seq_by_cat[category]
                template = choose_template(index, category, profile)
                subintent = subintents[sub_idx % len(subintents)]; sub_idx += 1
                drift_mode = None; lure_level = None
                if profile == "漂移波动型":
                    drift_mode = DRIFT_MODES[drift_mode_idx % len(DRIFT_MODES)]

                    if drift_mode_idx < 3:
                        lure_level = "high"
                    elif drift_mode_idx < 6:
                        lure_level = "medium"
                    else:
                        lure_level = "low"

                    drift_mode_idx += 1
                svc = apply_service_update(
                    template, category, profile, make_service_key(category, seq),
                    make_service_name(category, profile, seq),
                    make_description(category, profile, seq, subintent),
                    make_tags(category, profile, subintent, lure_level),
                    make_price(profile),
                    make_mock_behavior(profile, drift_mode),
                )
                services_out.append(svc)
                trust_seed, rating_count_seed = make_trust_seed(profile)
                trust_seed_out.append({
                    "service_key": svc["service_key"],
                    "category": category,
                    "profile_name": profile,
                    "trust_seed": trust_seed,
                    "rating_count_seed": rating_count_seed,
                })
    (OUTPUT_DIR / "service_catalog.json").write_text(json.dumps({"market_name": B3_DRIFT_MARKET_NAME, "service_count": len(services_out), "services": services_out}, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT_DIR / "trust_seed.json").write_text(json.dumps({"market_name": B3_DRIFT_MARKET_NAME, "service_count": len(trust_seed_out), "items": trust_seed_out}, ensure_ascii=False, indent=2), encoding="utf-8")
    from collections import Counter
    cat_counter = Counter(); prof_counter = Counter()
    for s in services_out:
        cat_counter[s["category"]] += 1
        prof_counter[extract_profile(s)] += 1
    print(f"[done] market_name={B3_DRIFT_MARKET_NAME}")
    print(f"[done] service_count={len(services_out)}")
    print("[done] category counts:")
    for cat, n in cat_counter.items(): print(" ", cat, n)
    print("[done] profile counts:")
    for prof, n in prof_counter.items(): print(" ", prof, n)
    print("[done] output files:")
    print(" ", OUTPUT_DIR / "service_catalog.json")
    print(" ", OUTPUT_DIR / "trust_seed.json")

if __name__ == "__main__":
    main()
