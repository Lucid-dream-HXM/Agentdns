from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Set

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TASKS = ROOT / 'outputs' / 'sample' / 'task_instances.json'
DEFAULT_CATALOG = ROOT / 'outputs' / 'sample' / 'service_catalog.json'

REQUIRED_TASK_FIELDS = {
    'task_id',
    'template_id',
    'scenario_family',
    'complexity_level',
    'task_prompt',
    'step_chain',
    'required_service_categories',
    'constraints',
    'source_material_refs',
}


def load_json(path: Path) -> Dict[str, Any]:
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def extract_market_categories(catalog: Dict[str, Any]) -> Set[str]:
    return {item['category'] for item in catalog.get('services', [])}


def validate_tasks(tasks: Dict[str, Any], market_categories: Set[str]) -> List[str]:
    issues: List[str] = []
    for task in tasks.get('tasks', []):
        missing = REQUIRED_TASK_FIELDS - set(task.keys())
        if missing:
            issues.append(f"任务 {task.get('task_id', '<unknown>')} 缺少字段: {sorted(missing)}")
            continue
        if not task['step_chain']:
            issues.append(f"任务 {task['task_id']} 的 step_chain 为空")
        unavailable = [item for item in task['required_service_categories'] if item not in market_categories]
        if unavailable:
            issues.append(f"任务 {task['task_id']} 依赖市场中不存在的服务类别: {unavailable}")
        if task['complexity_level'] not in {'L1', 'L2', 'L3'}:
            issues.append(f"任务 {task['task_id']} 的复杂度层级不合法")
    return issues


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='校验任务实例。')
    parser.add_argument('--tasks', type=Path, default=DEFAULT_TASKS)
    parser.add_argument('--catalog', type=Path, default=DEFAULT_CATALOG)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tasks = load_json(args.tasks)
    catalog = load_json(args.catalog)
    issues = validate_tasks(tasks, extract_market_categories(catalog))
    if issues:
        print('任务实例校验失败：')
        for issue in issues:
            print('-', issue)
        raise SystemExit(1)
    print('任务实例校验通过。')


if __name__ == '__main__':
    main()
