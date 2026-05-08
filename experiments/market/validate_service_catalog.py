from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / 'outputs' / 'sample' / 'service_catalog.json'

REQUIRED_FIELDS = {
    'service_id',
    'service_key',
    'service_name',
    'category',
    'category_name',
    'profile_name',
    'price',
    'base_latency_ms',
    'quality_range',
    'format_stability',
    'consumability',
    'failure_probability',
    'drift_probability',
    'description',
}


def load_service_catalog(path: Path) -> Dict[str, Any]:
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def check_unique_keys(services: List[Dict[str, Any]]) -> List[str]:
    keys = [item['service_key'] for item in services if 'service_key' in item]
    duplicates = [key for key, count in Counter(keys).items() if count > 1]
    return [f'存在重复 service_key: {key}' for key in duplicates]


def check_required_fields(services: List[Dict[str, Any]]) -> List[str]:
    issues: List[str] = []
    for item in services:
        missing = REQUIRED_FIELDS - set(item.keys())
        if missing:
            issues.append(f"服务 {item.get('service_key', '<unknown>')} 缺少字段: {sorted(missing)}")
    return issues


def check_ranges(services: List[Dict[str, Any]]) -> List[str]:
    issues: List[str] = []
    for item in services:
        key = item.get('service_key', '<unknown>')
        if item.get('price', 0) < 0:
            issues.append(f'{key} 的 price 小于 0')
        if item.get('base_latency_ms', 0) <= 0:
            issues.append(f'{key} 的 base_latency_ms 不合法')
        for field in ['format_stability', 'consumability', 'failure_probability', 'drift_probability']:
            value = item.get(field)
            if value is None or not (0 <= value <= 1):
                issues.append(f'{key} 的 {field} 不在 [0, 1] 范围内')
    return issues


def check_category_distribution(services: List[Dict[str, Any]]) -> Counter:
    return Counter(item['category'] for item in services)


def check_profile_distribution(services: List[Dict[str, Any]]) -> Counter:
    return Counter(item['profile_name'] for item in services)


def validate_catalog(catalog: Dict[str, Any]) -> List[str]:
    services = catalog.get('services', [])
    issues: List[str] = []
    issues.extend(check_unique_keys(services))
    issues.extend(check_required_fields(services))
    issues.extend(check_ranges(services))
    if catalog.get('service_count') != len(services):
        issues.append('service_count 与实际服务数量不一致')
    if not services:
        issues.append('服务目录为空')
    return issues


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='校验实验服务市场。')
    parser.add_argument('--catalog', type=Path, default=DEFAULT_CATALOG)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    catalog = load_service_catalog(args.catalog)
    issues = validate_catalog(catalog)
    category_counter = check_category_distribution(catalog.get('services', []))
    profile_counter = check_profile_distribution(catalog.get('services', []))

    print('类别分布:', dict(category_counter))
    print('画像分布:', dict(profile_counter))
    if issues:
        print('校验失败：')
        for issue in issues:
            print('-', issue)
        raise SystemExit(1)
    print('服务目录校验通过。')


if __name__ == '__main__':
    main()
