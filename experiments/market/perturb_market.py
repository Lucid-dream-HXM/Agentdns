from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any, Dict

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / 'outputs' / 'sample' / 'full_service_catalog.json'
DEFAULT_OUTPUT_DIR = ROOT / 'outputs' / 'sample' / 'market_variants'


def load_catalog(path: Path) -> Dict[str, Any]:
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def save_catalog(catalog: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)


def apply_variant(catalog: Dict[str, Any], variant: str, seed: int) -> Dict[str, Any]:
    rng = random.Random(seed)
    services = []
    for item in catalog.get('services', []):
        service = dict(item)
        if variant == 'drift_enhanced' and service['profile_name'] in {'漂移波动型', '平衡实用型'}:
            service['drift_probability'] = min(0.45, service['drift_probability'] + 0.12)
            service['consumability'] = max(0.35, round(service['consumability'] - rng.uniform(0.03, 0.10), 4))
        elif variant == 'fault_enhanced' and service['profile_name'] in {'故障脆弱型', '低价基础型'}:
            service['failure_probability'] = min(0.40, service['failure_probability'] + 0.10)
            service['format_stability'] = max(0.30, round(service['format_stability'] - rng.uniform(0.05, 0.12), 4))
        elif variant == 'deceptive_enhanced' and service['profile_name'] in {'诱骗失真型', '低时延响应型'}:
            service['price'] = round(max(0.005, service['price'] * 0.85), 4)
            service['base_latency_ms'] = int(max(150, service['base_latency_ms'] * 0.85))
            service['consumability'] = max(0.20, round(service['consumability'] - rng.uniform(0.10, 0.18), 4))
        services.append(service)
    payload = dict(catalog)
    payload['variant'] = variant
    payload['services'] = services
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='生成复杂市场扰动版本。')
    parser.add_argument('--input', type=Path, default=DEFAULT_INPUT)
    parser.add_argument('--output-dir', type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument('--seed', type=int, default=20260419)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base_catalog = load_catalog(args.input)
    for variant in ['standard', 'drift_enhanced', 'fault_enhanced', 'deceptive_enhanced']:
        catalog = base_catalog if variant == 'standard' else apply_variant(base_catalog, variant, args.seed)
        save_catalog(catalog, args.output_dir / f'{variant}.json')
        print(f'已生成市场版本：{variant}')


if __name__ == '__main__':
    main()
