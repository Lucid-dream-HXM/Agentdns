from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any, Dict, List

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATEGORY_CONFIG = ROOT / 'configs' / 'market' / 'service_categories.yaml'
DEFAULT_PROFILE_CONFIG = ROOT / 'configs' / 'market' / 'service_profiles.yaml'
DEFAULT_OUTPUT = ROOT / 'outputs' / 'sample' / 'service_catalog.json'

PROFILE_SUFFIXES = {
    '旗舰通用型': ['旗舰', '全能', '专业'],
    '平衡实用型': ['平衡', '通用', '实用'],
    '低价基础型': ['经济', '基础', '轻量'],
    '低时延响应型': ['极速', '快响', '低延迟'],
    '领域专精型': ['专精', '领域', '专家'],
    '漂移波动型': ['波动', '漂移', '不稳'],
    '故障脆弱型': ['脆弱', '故障敏感', '易错'],
    '诱骗失真型': ['低价快响', '诱骗', '表面优'],
}

CATEGORY_NAME_PREFIX = {
    'text_summary': '摘要',
    'structured_extraction': '抽取',
    'routing_classification': '路由',
    'translation': '翻译',
    'rewriting_polishing': '改写',
    'format_conversion': '格式',
    'validation_correction': '校验',
    'retrieval': '检索',
    'planning': '规划',
    'aggregation': '聚合',
}

SMALL_MARKET_COUNTS = {
    'text_summary': 5,
    'structured_extraction': 5,
    'routing_classification': 4,
    'aggregation': 4,
    'planning': 3,
    'retrieval': 3,
    'format_conversion': 2,
    'validation_correction': 2,
}


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open('r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def interpolate(low: float, high: float, rng: random.Random) -> float:
    return round(rng.uniform(low, high), 4)


def pick_profile(category: Dict[str, Any], rng: random.Random) -> str:
    profiles = category['allowed_profiles']
    weights = []
    for name in profiles:
        if name == '平衡实用型':
            weights.append(4)
        elif name in {'旗舰通用型', '领域专精型'}:
            weights.append(2)
        else:
            weights.append(1)
    return rng.choices(profiles, weights=weights, k=1)[0]


def build_service_name(category_id: str, profile_name: str, idx: int, rng: random.Random) -> str:
    prefix = CATEGORY_NAME_PREFIX.get(category_id, '服务')
    suffix = rng.choice(PROFILE_SUFFIXES.get(profile_name, ['标准']))
    return f'{prefix}{suffix}服务{idx:02d}'


def make_service_key(category_id: str, idx: int) -> str:
    return f'svc_{category_id}_{idx:03d}'


def generate_service_instance(
    category: Dict[str, Any],
    profile: Dict[str, Any],
    index: int,
    rng: random.Random,
) -> Dict[str, Any]:
    category_id = category['category_id']
    profile_name = profile['profile_name']
    service_name = build_service_name(category_id, profile_name, index, rng)

    quality = interpolate(*profile['quality_range'], rng)
    latency = int(rng.uniform(*profile['latency_range_ms']))
    cost = interpolate(*profile['cost_range'], rng)
    format_stability = interpolate(*profile['format_stability_range'], rng)
    consumability = interpolate(*profile['consumability_range'], rng)

    return {
        'service_id': index,
        'service_key': make_service_key(category_id, index),
        'service_name': service_name,
        'category': category_id,
        'category_name': category['category_name'],
        'profile_name': profile_name,
        'price': cost,
        'base_latency_ms': latency,
        'latency_jitter_ms': int(max(50, latency * 0.15)),
        'quality_range': profile['quality_range'],
        'format_stability': format_stability,
        'consumability': consumability,
        'failure_probability': profile['failure_probability'],
        'drift_probability': profile['drift_probability'],
        'tags': [category['category_name'], profile_name, *category['core_use_cases']],
        'description': f"{service_name}，属于{category['category_name']}，画像为{profile_name}。{profile['description']}",
    }


def resolve_category_targets(categories: List[Dict[str, Any]], small_market: bool) -> List[Dict[str, Any]]:
    resolved = []
    for category in categories:
        item = dict(category)
        item['resolved_target_count'] = SMALL_MARKET_COUNTS.get(category['category_id'], 0) if small_market else category['target_count']
        if item['resolved_target_count'] > 0:
            resolved.append(item)
    return resolved


def build_profile_map(profile_config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {item['profile_name']: item for item in profile_config['profiles']}


def generate_service_catalog(
    category_config_path: Path = DEFAULT_CATEGORY_CONFIG,
    profile_config_path: Path = DEFAULT_PROFILE_CONFIG,
    *,
    seed: int = 20260419,
    small_market: bool = True,
) -> Dict[str, Any]:
    rng = random.Random(seed)
    category_config = load_yaml(category_config_path)
    profile_config = load_yaml(profile_config_path)
    profile_map = build_profile_map(profile_config)

    categories = resolve_category_targets(category_config['categories'], small_market)
    services: List[Dict[str, Any]] = []
    service_index = 1
    for category in categories:
        for _ in range(category['resolved_target_count']):
            profile_name = pick_profile(category, rng)
            service = generate_service_instance(category, profile_map[profile_name], service_index, rng)
            services.append(service)
            service_index += 1

    return {
        'version': 1,
        'seed': seed,
        'small_market': small_market,
        'service_count': len(services),
        'services': services,
    }


def save_service_catalog(catalog: Dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('w', encoding='utf-8') as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='生成实验服务市场。')
    parser.add_argument('--category-config', type=Path, default=DEFAULT_CATEGORY_CONFIG)
    parser.add_argument('--profile-config', type=Path, default=DEFAULT_PROFILE_CONFIG)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--seed', type=int, default=20260419)
    parser.add_argument('--full-market', action='store_true', help='生成完整 100 服务市场。')
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    catalog = generate_service_catalog(
        args.category_config,
        args.profile_config,
        seed=args.seed,
        small_market=not args.full_market,
    )
    save_service_catalog(catalog, args.output)
    print(f"已生成服务市场：{args.output}，服务数量={catalog['service_count']}")


if __name__ == '__main__':
    main()
