from __future__ import annotations

import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
import csv
import json
import random
from collections import defaultdict
from statistics import mean
from typing import Any, Dict, List, Tuple

import yaml

from experiments.evaluators.oracle_schema import (
    serialize_selection_records,
    serialize_step_records,
    serialize_task_records,
)
from experiments.evaluators.oracle_selection_evaluator import evaluate_selection
from experiments.evaluators.oracle_step_evaluator import evaluate_step
from experiments.evaluators.oracle_task_evaluator import evaluate_task

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GROUPS = ROOT / 'configs' / 'experiments' / 'group_definitions.yaml'
DEFAULT_MARKET = ROOT / 'outputs' / 'sample' / 'service_catalog.json'
DEFAULT_TASKS = ROOT / 'outputs' / 'sample' / 'task_instances.json'
DEFAULT_OUTPUT_DIR = ROOT / 'outputs' / 'sample' / 'run_results'

CATEGORY_NAME_TO_ID = {
    '文本摘要类': 'text_summary',
    '结构化抽取类': 'structured_extraction',
    '分类路由判断类': 'routing_classification',
    '翻译类': 'translation',
    '改写润色类': 'rewriting_polishing',
    '格式转换类': 'format_conversion',
    '校验纠错类': 'validation_correction',
    '检索信息获取类': 'retrieval',
    '规划拆分类': 'planning',
    '聚合最终生成类': 'aggregation',
}

PROFILE_BIAS = {
    '旗舰通用型': 0.08,
    '平衡实用型': 0.03,
    '低价基础型': -0.03,
    '低时延响应型': -0.01,
    '领域专精型': 0.06,
    '漂移波动型': -0.02,
    '故障脆弱型': -0.06,
    '诱骗失真型': -0.08,
}


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open('r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_json(path: Path) -> Dict[str, Any]:
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def load_group_definition(path: Path, group_name: str) -> Dict[str, Any]:
    config = load_yaml(path)
    for group in config['groups']:
        if group['group_name'] == group_name:
            return group
    raise ValueError(f'未找到实验组：{group_name}')


def build_market_index(catalog: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    market = defaultdict(list)
    for service in catalog.get('services', []):
        market[service['category']].append(service)
    return market



def score_service(service: Dict[str, Any], group: Dict[str, Any], required_category: str, rng: random.Random) -> float:
    profile_bias = PROFILE_BIAS.get(service['profile_name'], 0.0)
    latency_penalty = min(service['base_latency_ms'] / 4000.0, 0.5)
    cost_penalty = min(service['price'] / 0.25, 0.5)
    quality_mid = mean(service['quality_range'])
    score = quality_mid + profile_bias - 0.15 * latency_penalty - 0.10 * cost_penalty

    if group['uses_vector_retrieval']:
        score += 0.04
    if group['uses_reranking']:
        score += 0.03
    if group['uses_trust_feedback']:
        score += 0.02
    if service['category'] != required_category:
        score -= 0.20
    score += rng.uniform(-0.01, 0.01)
    return score



def select_service(candidates: List[Dict[str, Any]], group: Dict[str, Any], required_category: str, rng: random.Random) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    if not candidates:
        raise ValueError(f'类别 {required_category} 无可用候选服务')

    if group['group_name'] == '直接通用服务组':
        scored = [
            {
                'service': service,
                'score': mean(service['quality_range']) - 0.05 * service['price'],
            }
            for service in candidates
        ]
    elif group['group_name'] == '简单规则路由组':
        scored = [
            {
                'service': service,
                'score': -service['price'] - service['base_latency_ms'] / 5000.0,
            }
            for service in candidates
        ]
    else:
        scored = [
            {
                'service': service,
                'score': score_service(service, group, required_category, rng),
            }
            for service in candidates
        ]
    scored.sort(key=lambda item: item['score'], reverse=True)
    selected = scored[0]['service']
    best = max(candidates, key=lambda service: mean(service['quality_range']))
    return selected, best



def simulate_step(
    task: Dict[str, Any],
    step_index: int,
    required_category: str,
    service: Dict[str, Any],
    best_service: Dict[str, Any],
    group: Dict[str, Any],
    rng: random.Random,
):
    quality_mid = mean(service['quality_range'])
    success_threshold = 0.55 if task['complexity_level'] == 'L2' else 0.62
    if group['supports_nested_calling']:
        success_threshold -= 0.03
    if group['uses_trust_feedback']:
        success_threshold -= 0.02

    drift_penalty = service['drift_probability'] * rng.uniform(0, 0.15)
    failure_event = rng.random() < service['failure_probability']
    observed_quality = max(0.0, min(1.0, quality_mid - drift_penalty + rng.uniform(-0.04, 0.04)))
    observed_consumability = max(0.0, min(1.0, service['consumability'] + rng.uniform(-0.05, 0.05)))
    observed_latency_ms = int(service['base_latency_ms'] + rng.uniform(0, service['latency_jitter_ms']))
    observed_cost = round(service['price'], 4)
    step_success = (not failure_event) and observed_quality >= success_threshold and observed_consumability >= 0.58

    observed = {
        'service_key': service['service_key'],
        'category': service['category'],
        'observed_quality': round(observed_quality, 4),
        'observed_consumability': round(observed_consumability, 4),
        'observed_latency_ms': observed_latency_ms,
        'observed_cost': observed_cost,
    }
    best_observed = {
        'service_key': best_service['service_key'],
        'category': best_service['category'],
        'observed_quality': round(mean(best_service['quality_range']), 4),
    }
    step_record, step_utility = evaluate_step(
        task['task_id'],
        f'step_{step_index:02d}',
        required_category,
        observed,
        step_success=step_success,
    )
    selection_record = evaluate_selection(
        task['task_id'],
        f'step_{step_index:02d}',
        candidate_pool_size=1,
        selected_service=observed,
        best_service=best_observed,
        required_category=required_category,
    )
    return step_record, selection_record, step_utility



def run_single_task(
    task: Dict[str, Any],
    group: Dict[str, Any],
    market_index: Dict[str, List[Dict[str, Any]]],
    rng: random.Random,
):
    step_records = []
    selection_records = []
    step_utilities = []

    if not group['supports_multi_step'] and len(task['required_service_categories']) > 1:
        task_record = evaluate_task(
            task_id=task['task_id'],
            group_name=group['group_name'],
            scenario_family=task['scenario_family'],
            task_success=False,
            step_qualities=[],
            step_latencies_ms=[],
            step_costs=[],
            step_utilities=[],
            failure_type='multi_step_not_supported',
        )
        return task_record, step_records, selection_records, {'task_id': task['task_id'], 'group_name': group['group_name'], 'status': 'failed'}

    for index, required_category in enumerate(task['required_service_categories'], start=1):
        if group['group_name'] == '直接通用服务组':
            candidates = [item for services in market_index.values() for item in services]
        else:
            candidates = market_index.get(required_category, [])
        if not candidates:
            task_record = evaluate_task(
                task_id=task['task_id'],
                group_name=group['group_name'],
                scenario_family=task['scenario_family'],
                task_success=False,
                step_qualities=[item.oracle_step_quality_score for item in step_records],
                step_latencies_ms=[item.oracle_step_latency_ms for item in step_records],
                step_costs=[item.oracle_step_cost for item in step_records],
                step_utilities=step_utilities,
                failure_type='no_candidate_found',
            )
            return task_record, step_records, selection_records, {'task_id': task['task_id'], 'group_name': group['group_name'], 'status': 'failed'}

        service, best_service = select_service(candidates, group, required_category, rng)
        step_record, selection_record, step_utility = simulate_step(task, index, required_category, service, best_service, group, rng)
        step_records.append(step_record)
        selection_records.append(selection_record)
        step_utilities.append(step_utility)
        if not step_record.step_success:
            task_record = evaluate_task(
                task_id=task['task_id'],
                group_name=group['group_name'],
                scenario_family=task['scenario_family'],
                task_success=False,
                step_qualities=[item.oracle_step_quality_score for item in step_records],
                step_latencies_ms=[item.oracle_step_latency_ms for item in step_records],
                step_costs=[item.oracle_step_cost for item in step_records],
                step_utilities=step_utilities,
                failure_type='cascading_failure',
            )
            return task_record, step_records, selection_records, {'task_id': task['task_id'], 'group_name': group['group_name'], 'status': 'failed'}

    task_record = evaluate_task(
        task_id=task['task_id'],
        group_name=group['group_name'],
        scenario_family=task['scenario_family'],
        task_success=True,
        step_qualities=[item.oracle_step_quality_score for item in step_records],
        step_latencies_ms=[item.oracle_step_latency_ms for item in step_records],
        step_costs=[item.oracle_step_cost for item in step_records],
        step_utilities=step_utilities,
        failure_type=None,
    )
    raw_record = {
        'task_id': task['task_id'],
        'group_name': group['group_name'],
        'status': 'success',
        'step_count': len(step_records),
        'complexity_level': task['complexity_level'],
    }
    return task_record, step_records, selection_records, raw_record


def run_task_batch(group: Dict[str, Any], catalog: Dict[str, Any], tasks: Dict[str, Any], seed: int, max_tasks: int | None = None) -> Tuple[list, list, list, list]:
    rng = random.Random(seed)
    market_index = build_market_index(catalog)
    task_records: List[TaskOracleRecord] = []
    step_records: List[StepOracleRecord] = []
    selection_records: List[SelectionOracleRecord] = []
    raw_records: List[Dict[str, Any]] = []
    iterable = tasks.get('tasks', [])
    if max_tasks is not None:
        iterable = iterable[:max_tasks]
    for task in iterable:
        task_record, steps, selections, raw_record = run_single_task(task, group, market_index, rng)
        task_records.append(task_record)
        step_records.extend(steps)
        selection_records.extend(selections)
        raw_records.append(raw_record)
    return task_records, step_records, selection_records, raw_records


def write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def generate_minimal_summary(task_records: List[TaskOracleRecord], output_path: Path) -> None:
    total = len(task_records)
    success_count = sum(1 for item in task_records if item.task_success)
    avg_quality = round(mean(item.oracle_final_quality_score for item in task_records), 4) if task_records else 0.0
    avg_cost = round(mean(item.oracle_total_cost for item in task_records), 4) if task_records else 0.0
    avg_utility = round(mean(item.oracle_final_utility for item in task_records), 4) if task_records else 0.0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(
            f,
            fieldnames=['task_count', 'task_success_count', 'task_success_rate', 'avg_final_quality', 'avg_total_cost', 'avg_oracle_utility'],
        )
        writer.writeheader()
        writer.writerow(
            {
                'task_count': total,
                'task_success_count': success_count,
                'task_success_rate': round(success_count / total, 4) if total else 0.0,
                'avg_final_quality': avg_quality,
                'avg_total_cost': avg_cost,
                'avg_oracle_utility': avg_utility,
            }
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='运行最小闭环端到端实验。')
    parser.add_argument('--group-name', type=str, default='基础解析组')
    parser.add_argument('--groups', type=Path, default=DEFAULT_GROUPS)
    parser.add_argument('--market', type=Path, default=DEFAULT_MARKET)
    parser.add_argument('--tasks', type=Path, default=DEFAULT_TASKS)
    parser.add_argument('--output-dir', type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument('--seed', type=int, default=20260419)
    parser.add_argument('--max-tasks', type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    group = load_group_definition(args.groups, args.group_name)
    catalog = load_json(args.market)
    tasks = load_json(args.tasks)
    task_records, step_records, selection_records, raw_records = run_task_batch(group, catalog, tasks, args.seed, args.max_tasks)

    output_dir = args.output_dir / group['group_id']
    write_jsonl(output_dir / 'raw_task_runs.jsonl', raw_records)
    write_jsonl(output_dir / 'oracle_task_records.jsonl', serialize_task_records(task_records))
    write_jsonl(output_dir / 'oracle_step_records.jsonl', serialize_step_records(step_records))
    write_jsonl(output_dir / 'oracle_selection_records.jsonl', serialize_selection_records(selection_records))
    generate_minimal_summary(task_records, output_dir / 'minimal_summary.csv')
    print(f"最小闭环实验完成：{output_dir}")


if __name__ == '__main__':
    main()
