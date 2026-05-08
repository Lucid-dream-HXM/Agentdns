from __future__ import annotations

import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
import json
import random
from collections import defaultdict
from typing import Any, Dict, List

import yaml

from experiments.tasks.instantiate_tasks import instantiate_task, load_task_templates

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATES = ROOT / 'tasks' / 'task_templates.yaml'
DEFAULT_PLAN = ROOT / 'configs' / 'tasks' / 'task_generation_plan.yaml'
DEFAULT_OUTPUT = ROOT / 'outputs' / 'sample' / 'formal_task_instances.json'


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open('r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def build_formal_task_set(templates: List[Dict[str, Any]], plan: Dict[str, Any], mode: str, seed: int) -> Dict[str, Any]:
    rng = random.Random(seed)
    mode_plan = plan['plans'][mode]
    per_template = mode_plan['per_template']
    scenario_targets = mode_plan['scenario_targets']

    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for template in templates:
        grouped[template['scenario_family']].append(template)

    tasks: List[Dict[str, Any]] = []
    task_index = 1
    for scenario_family, target in scenario_targets.items():
        candidates = grouped.get(scenario_family, [])
        if not candidates:
            continue
        while sum(1 for item in tasks if item['scenario_family'] == scenario_family) < target:
            progress = False
            for template in candidates:
                current_per_template = sum(
                    1 for item in tasks
                    if item['scenario_family'] == scenario_family and item['template_id'] == template['template_id']
                )
                if current_per_template >= per_template:
                    continue
                tasks.append(instantiate_task(template, task_index, rng))
                task_index += 1
                progress = True
                if sum(1 for item in tasks if item['scenario_family'] == scenario_family) >= target:
                    break
            if not progress:
                break

    return {
        'version': 1,
        'mode': mode,
        'seed': seed,
        'task_count': len(tasks),
        'tasks': tasks,
    }


def save_payload(payload: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='构建正式实验任务集。')
    parser.add_argument('--templates', type=Path, default=DEFAULT_TEMPLATES)
    parser.add_argument('--plan', type=Path, default=DEFAULT_PLAN)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--mode', choices=['debug', 'formal'], default='formal')
    parser.add_argument('--seed', type=int, default=20260419)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    templates = load_task_templates(args.templates)
    plan = load_yaml(args.plan)
    payload = build_formal_task_set(templates, plan, args.mode, args.seed)
    save_payload(payload, args.output)
    print(f"已生成 {args.mode} 任务集：{args.output}，任务数量={payload['task_count']}")


if __name__ == '__main__':
    main()
