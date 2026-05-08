from __future__ import annotations

import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
from typing import Any, Dict, List

import yaml

from experiments.runners.end_to_end_runner import (
    DEFAULT_GROUPS,
    generate_minimal_summary,
    load_group_definition,
    load_json,
    run_task_batch,
    write_jsonl,
)
from experiments.evaluators.oracle_schema import (
    serialize_selection_records,
    serialize_step_records,
    serialize_task_records,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX = ROOT / 'configs' / 'experiments' / 'experiment_matrix.yaml'
DEFAULT_MARKET = ROOT / 'outputs' / 'sample' / 'service_catalog.json'
DEFAULT_TASKS = ROOT / 'outputs' / 'sample' / 'formal_task_instances.json'
DEFAULT_OUTPUT_DIR = ROOT / 'outputs' / 'sample' / 'ablation_results'


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open('r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_experiment_definition(path: Path, experiment_id: str) -> Dict[str, Any]:
    config = load_yaml(path)
    for item in config['experiments']:
        if item['experiment_id'] == experiment_id:
            return item
    raise ValueError(f'未找到实验定义：{experiment_id}')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='运行关键机制消融实验。')
    parser.add_argument('--experiment-id', type=str, default='mechanism_ablation')
    parser.add_argument('--matrix', type=Path, default=DEFAULT_MATRIX)
    parser.add_argument('--groups', type=Path, default=DEFAULT_GROUPS)
    parser.add_argument('--market', type=Path, default=DEFAULT_MARKET)
    parser.add_argument('--tasks', type=Path, default=DEFAULT_TASKS)
    parser.add_argument('--output-dir', type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument('--seed', type=int, default=20260419)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    experiment = load_experiment_definition(args.matrix, args.experiment_id)
    catalog = load_json(args.market)
    tasks = load_json(args.tasks)

    output_dir = args.output_dir / args.experiment_id
    output_dir.mkdir(parents=True, exist_ok=True)
    for offset, group_id in enumerate(experiment['group_ids']):
        group = load_group_definition(args.groups, next_name_by_id(args.groups, group_id))
        task_records, step_records, selection_records, raw_records = run_task_batch(group, catalog, tasks, args.seed + offset)
        group_dir = output_dir / group_id
        write_jsonl(group_dir / 'raw_task_runs.jsonl', raw_records)
        write_jsonl(group_dir / 'oracle_task_records.jsonl', serialize_task_records(task_records))
        write_jsonl(group_dir / 'oracle_step_records.jsonl', serialize_step_records(step_records))
        write_jsonl(group_dir / 'oracle_selection_records.jsonl', serialize_selection_records(selection_records))
        generate_minimal_summary(task_records, group_dir / 'minimal_summary.csv')
        print(f'已完成组别：{group["group_name"]}')


def next_name_by_id(group_path: Path, group_id: str) -> str:
    config = load_yaml(group_path)
    for item in config['groups']:
        if item['group_id'] == group_id:
            return item['group_name']
    raise ValueError(f'未找到组别 ID：{group_id}')


if __name__ == '__main__':
    main()
