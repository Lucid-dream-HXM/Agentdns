from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from experiments.runners.end_to_end_runner import load_group_definition, load_json, run_task_batch

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX = ROOT / 'configs' / 'experiments' / 'experiment_matrix.yaml'
DEFAULT_GROUPS = ROOT / 'configs' / 'experiments' / 'group_definitions.yaml'
DEFAULT_MARKET = ROOT / 'outputs' / 'sample' / 'full_service_catalog.json'
DEFAULT_TASKS = ROOT / 'outputs' / 'sample' / 'formal_task_instances.json'
DEFAULT_OUTPUT_DIR = ROOT / 'outputs' / 'sample' / 'lifecycle_results'


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open('r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def get_experiment(path: Path, experiment_id: str) -> Dict[str, Any]:
    config = load_yaml(path)
    for item in config['experiments']:
        if item['experiment_id'] == experiment_id:
            return item
    raise ValueError(f'未找到实验定义：{experiment_id}')


def get_group_name(path: Path, group_id: str) -> str:
    config = load_yaml(path)
    for item in config['groups']:
        if item['group_id'] == group_id:
            return item['group_name']
    raise ValueError(f'未找到组别：{group_id}')


def summarize_round(rows: List[Dict[str, Any]]) -> Dict[str, float]:
    total = len(rows)
    success = sum(1 for row in rows if row['task_success'])
    utility = sum(float(row['oracle_final_utility']) for row in rows) / max(total, 1)
    cost = sum(float(row['oracle_total_cost']) for row in rows) / max(total, 1)
    return {
        'task_count': total,
        'task_success_rate': round(success / total, 4) if total else 0.0,
        'avg_oracle_utility': round(utility, 4),
        'avg_total_cost': round(cost, 4),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='运行生命周期实验。')
    parser.add_argument('--experiment-id', default='lifecycle')
    parser.add_argument('--matrix', type=Path, default=DEFAULT_MATRIX)
    parser.add_argument('--groups', type=Path, default=DEFAULT_GROUPS)
    parser.add_argument('--market', type=Path, default=DEFAULT_MARKET)
    parser.add_argument('--tasks', type=Path, default=DEFAULT_TASKS)
    parser.add_argument('--output-dir', type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument('--seed', type=int, default=20260419)
    parser.add_argument('--rounds', type=int, default=4)
    parser.add_argument('--max-tasks', type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    experiment = get_experiment(args.matrix, args.experiment_id)
    catalog = load_json(args.market)
    tasks = load_json(args.tasks)
    output_dir = args.output_dir / args.experiment_id
    output_dir.mkdir(parents=True, exist_ok=True)

    for offset, group_id in enumerate(experiment['group_ids']):
        group_name = get_group_name(args.groups, group_id)
        group = load_group_definition(args.groups, group_name)
        rows = []
        for round_index in range(1, args.rounds + 1):
            task_records, _, _, _ = run_task_batch(group, catalog, tasks, args.seed + offset + round_index, max_tasks=args.max_tasks)
            summary = summarize_round([item.to_dict() for item in task_records])
            summary['round_index'] = round_index
            summary['group_name'] = group_name
            summary['phase_name'] = ['冷启动', '短期预热', '中期运行', '持续运行'][min(round_index - 1, 3)]
            rows.append(summary)
        group_dir = output_dir / group_id
        group_dir.mkdir(parents=True, exist_ok=True)
        with (group_dir / 'lifecycle_summary.csv').open('w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['group_name', 'round_index', 'phase_name', 'task_count', 'task_success_rate', 'avg_oracle_utility', 'avg_total_cost'])
            writer.writeheader()
            writer.writerows(rows)
        print(f'已完成生命周期实验组别：{group_name}')


if __name__ == '__main__':
    main()
