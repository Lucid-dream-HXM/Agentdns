from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / 'outputs' / 'sample' / 'service_catalog.json'
DEFAULT_OUTPUT = ROOT / 'outputs' / 'sample' / 'service_seed_payload.json'


def load_catalog(path: Path) -> Dict[str, Any]:
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def transform_to_seed_format(catalog: Dict[str, Any]) -> List[Dict[str, Any]]:
    payload = []
    for item in catalog.get('services', []):
        payload.append(
            {
                'service_key': item['service_key'],
                'name': item['service_name'],
                'category': item['category'],
                'category_name': item['category_name'],
                'description': item['description'],
                'price': item['price'],
                'tags': item['tags'],
                'profile_name': item['profile_name'],
                'mock_behavior': {
                    'base_latency_ms': item['base_latency_ms'],
                    'latency_jitter_ms': item['latency_jitter_ms'],
                    'quality_range': item['quality_range'],
                    'format_stability': item['format_stability'],
                    'consumability': item['consumability'],
                    'failure_probability': item['failure_probability'],
                    'drift_probability': item['drift_probability'],
                },
            }
        )
    return payload


def save_seed_payload(payload: List[Dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='导出适合 seed 使用的服务负载。')
    parser.add_argument('--catalog', type=Path, default=DEFAULT_CATALOG)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    catalog = load_catalog(args.catalog)
    payload = transform_to_seed_format(catalog)
    save_seed_payload(payload, args.output)
    print(f'已导出 seed 负载：{args.output}，条目数={len(payload)}')


if __name__ == '__main__':
    main()
