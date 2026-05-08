from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from experiments.local.agentdns_http_client import AgentDNSHttpClient
from experiments.local.review_payload_builder import build_review_payload
from experiments.local.selectors import (
    choose_basic_resolution_service,
    choose_direct_general_service,
    choose_full_multi_step_service,
    choose_simple_rule_service,
    choose_trust_feedback_service,
    choose_vector_enhanced_service,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GROUPS = ROOT / 'configs' / 'experiments' / 'group_definitions.yaml'
DEFAULT_TASKS = ROOT / 'outputs' / 'sample' / 'formal_task_instances_v2.json'
DEFAULT_RUNTIME = ROOT / 'configs' / 'local_runtime.yaml'
DEFAULT_OUTPUT_DIR = ROOT / 'outputs' / 'local_http_runs'


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def choose_service(group_name: str, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    mapping = {
        '直接通用服务组': choose_direct_general_service,
        '简单规则路由组': choose_simple_rule_service,
        '基础解析组': choose_basic_resolution_service,
        '向量召回增强组': choose_vector_enhanced_service,
        '信任反馈闭环组': choose_trust_feedback_service,
        '完整多步协同组': choose_full_multi_step_service,
    }
    return mapping[group_name](candidates)


def discovery_params(group_name: str) -> Dict[str, Any]:
    if group_name == '直接通用服务组':
        return {'include_trust': False, 'sort_by': 'relevance', 'category': None}
    if group_name == '简单规则路由组':
        return {'include_trust': False, 'sort_by': 'relevance'}
    if group_name == '基础解析组':
        return {'include_trust': False, 'sort_by': 'relevance'}
    if group_name == '向量召回增强组':
        return {'include_trust': False, 'sort_by': 'balanced'}
    return {'include_trust': True, 'sort_by': 'balanced'}


CATEGORY_SHORT_QUERIES = {
    'routing_classification': '分类路由',
    'text_summary': '文本摘要',
    'structured_extraction': '结构化抽取',
    'aggregation': '聚合',
    'format_conversion': '格式转换',
    'validation_correction': '校验纠错',
    'retrieval': '检索',
    'planning': '规划',
    'translation': '翻译',
    'rewriting_polishing': '改写润色',
}


def safe_trust_summary(client: AgentDNSHttpClient, api_key: str, service_id: Optional[int]) -> Dict[str, Any]:
    if not service_id:
        return {'ok': False, 'body': None, 'error': 'missing_service_id'}
    try:
        result = client.get_trust_summary_detailed(api_key=api_key, service_id=service_id)
        return {'ok': True, 'body': result['body'], 'latency_ms': result['latency_ms']}
    except Exception as exc:  # noqa: BLE001
        return {'ok': False, 'body': None, 'error': str(exc)}


def extract_trust_score(summary: Dict[str, Any]) -> Optional[float]:
    if not summary:
        return None
    for key in ('trust_score', 'score', 'current_trust_score'):
        value = summary.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    return None


def build_step_record(*,
                      step_id: int,
                      required_category: str,
                      query: str,
                      query_source: str,
                      task_prompt: str,
                      query_anchor: str,
                      pre_filter_candidate_count: int,
                      post_filter_candidate_count: int,
                      candidate_categories: List[str],
                      post_filter_candidate_categories: List[str],
                      candidates: List[Dict[str, Any]],
                      selected: Dict[str, Any],
                      selected_rank: int,
                      trust_before: Dict[str, Any]) -> Dict[str, Any]:
    capabilities = selected.get('capabilities') or {}
    return {
        'step_id': step_id,
        'required_category': required_category,
        'query': query,
        'query_source': query_source,
        'task_prompt': task_prompt,
        'query_anchor': query_anchor,
        'pre_filter_candidate_count': pre_filter_candidate_count,
        'post_filter_candidate_count': post_filter_candidate_count,
        'candidate_categories': candidate_categories,
        'post_filter_candidate_categories': post_filter_candidate_categories,
        'candidate_count': len(candidates),
        'candidate_service_ids': [svc.get('id') for svc in candidates],
        'candidate_service_keys': [(svc.get('capabilities') or {}).get('service_key') for svc in candidates],
        'candidate_service_names': [svc.get('name') for svc in candidates],
        'candidate_profiles': [(svc.get('capabilities') or {}).get('profile_name') for svc in candidates],
        'candidate_trust_scores': [svc.get('trust_score') for svc in candidates],
        'candidate_prices': [svc.get('price_per_unit') for svc in candidates],
        'selected_rank': selected_rank,
        'selected_service_id': selected.get('id'),
        'selected_service_name': selected.get('name'),
        'selected_service_key': capabilities.get('service_key'),
        'selected_profile_name': capabilities.get('profile_name'),
        'selected_consumability': (capabilities.get('mock_behavior') or {}).get('consumability'),
        'selected_format_stability': (capabilities.get('mock_behavior') or {}).get('format_stability'),
        'selected_category': selected.get('category'),
        'selected_price_per_unit': selected.get('price_per_unit'),
        'selected_trust_score': selected.get('trust_score'),
        'trust_before_raw': trust_before.get('body'),
        'trust_before_score': extract_trust_score(trust_before.get('body') or {}),
        'step_started_at': utc_now_iso(),
    }


def run_task(client: AgentDNSHttpClient, api_key: str, group_name: str, task: Dict[str, Any], run_id: str) -> Dict[str, Any]:
    task_started_at = utc_now_iso()
    selected_history: List[Dict[str, Any]] = []
    total_cost = 0.0
    total_latency_ms = 0
    success_step_count = 0
    review_success_count = 0
    review_failure_count = 0

    scenario_family = task.get('scenario_family') or task.get('scenario_id') or task.get('category')
    complexity_level = task.get('complexity_level')
    required_categories = task.get('required_service_categories', [])

    for step_index, category_id in enumerate(required_categories, start=1):
        params = discovery_params(group_name)
        category = None if group_name == '直接通用服务组' else category_id
        task_prompt = (task.get('task_prompt') or '').strip()
        category_anchor = CATEGORY_SHORT_QUERIES.get(category_id, category_id or '')

        if task_prompt and category_anchor:
            query = f"{category_anchor} {task_prompt}".strip()
            query_source = 'hybrid_task_prompt'
        elif task_prompt:
            query = task_prompt
            query_source = 'task_prompt'
        else:
            query = category_anchor or '任务处理'
            query_source = 'category_fallback'

        search_result = client.search_services_detailed(
            api_key=api_key,
            query=query,
            category=category,
            include_trust=params['include_trust'],
            sort_by=params['sort_by'],
            limit=10,
        )
        def candidate_category(c):
            if c.get('category'):
                return c.get('category')
            uri = c.get('agentdns_uri') or c.get('agentdns_url') or ''
            parts = uri.replace('agentdns://', '').split('/')
            return parts[1] if len(parts) >= 2 else None

        raw_candidates = search_result['services']
        pre_filter_candidate_count = len(raw_candidates)

        candidates = [c for c in raw_candidates if candidate_category(c) == category_id]

        post_filter_candidate_count = len(candidates)
        if not candidates:
            step_record = {
                'step_id': step_index,
                'required_category': category_id,
                'query': query,
                'query_source': query_source,
                'task_prompt': task_prompt,
                'query_anchor': category_anchor,
                'discovery_sort_by': params['sort_by'],
                'include_trust': params['include_trust'],
                'pre_filter_candidate_count': pre_filter_candidate_count,
                'post_filter_candidate_count': post_filter_candidate_count,
                'candidate_categories': [candidate_category(c) for c in raw_candidates],
                'post_filter_candidate_categories': [candidate_category(c) for c in candidates],
                'candidate_count': 0,
                'candidate_service_ids': [],
                'candidate_service_keys': [],
                'candidate_service_names': [],
                'candidate_profiles': [],
                'candidate_trust_scores': [],
                'candidate_prices': [],
                'search_total': search_result.get('total', 0),
                'search_latency_ms': search_result.get('latency_ms', 0),
                'step_status': 'no_candidate',
                'step_started_at': utc_now_iso(),
                'step_finished_at': utc_now_iso(),
            }
            selected_history.append(step_record)
            total_latency_ms += search_result.get('latency_ms', 0)
            break

        selected = choose_service(group_name, candidates)
        selected_rank = next((idx + 1 for idx, svc in enumerate(candidates) if svc.get('id') == selected.get('id')), -1)
        trust_before = safe_trust_summary(client, api_key, selected.get('id'))
        step_row = build_step_record(
            step_id=step_index,
            required_category=category_id,
            query=query,
            query_source=query_source,
            task_prompt=task_prompt,
            query_anchor=category_anchor,
            pre_filter_candidate_count=pre_filter_candidate_count,
            post_filter_candidate_count=post_filter_candidate_count,
            candidate_categories=[candidate_category(c) for c in raw_candidates],
            post_filter_candidate_categories=[candidate_category(c) for c in candidates],
            candidates=candidates,
            selected=selected,
            selected_rank=selected_rank,
            trust_before=trust_before,
        )
        total_latency_ms += search_result.get('latency_ms', 0)

        call_result = client.call_service_detailed(
            api_key=api_key,
            service=selected,
            task_input={
                'text': task.get('task_prompt'),
                'task_id': task['task_id'],
                'step_id': step_index,
                'stage': 'local_http_experiment',
            },
        )
        call_body = call_result['body']
        usage_id = call_result.get('usage_id')
        step_cost = float(selected.get('price_per_unit') or 0.0)
        total_cost += step_cost
        total_latency_ms += call_result.get('latency_ms', 0)

        step_row.update({
            'step_call_status_code': call_result.get('status_code'),
            'step_call_latency_ms': call_result.get('latency_ms'),
            'step_cost': round(step_cost, 6),
            'usage_id': usage_id,
            'call_status': call_result.get('call_status'),
            'call_result_excerpt': str(call_result.get('call_result'))[:200],
            'call_response_body': call_body,
        })

        review_payload = None
        review_response = None
        trust_after = None
        review_error = None
        if usage_id is not None:
            review_payload = build_review_payload(
                usage_id=usage_id,
                selected_service=selected,
                call_data=call_body,
                group_name=group_name,
                task_id=task.get('task_id'),
                step_id=step_index,
            )
            try:
                review_response = client.submit_review_detailed(api_key=api_key, payload=review_payload)
                review_success_count += 1
            except Exception as exc:  # noqa: BLE001
                review_error = str(exc)
                review_failure_count += 1
            trust_after = safe_trust_summary(client, api_key, selected.get('id'))

        step_row.update({
            'review_payload': review_payload,
            'review_response_body': None if review_response is None else review_response.get('body'),
            'review_latency_ms': None if review_response is None else review_response.get('latency_ms'),
            'review_status_code': None if review_response is None else review_response.get('status_code'),
            'review_error': review_error,
            'trust_after_raw': None if trust_after is None else trust_after.get('body'),
            'trust_after_score': None if trust_after is None else extract_trust_score(trust_after.get('body') or {}),
            'step_finished_at': utc_now_iso(),
            'step_status': 'success' if call_body.get('status') in {'success', 'partial'} else 'failed',
        })
        selected_history.append(step_row)

        if call_body.get('status') not in {'success', 'partial'}:
            return {
                'run_id': run_id,
                'group_name': group_name,
                'task_id': task['task_id'],
                'scenario_family': scenario_family,
                'complexity_level': complexity_level,
                'task_prompt': task.get('task_prompt'),
                'required_service_categories': required_categories,
                'status': 'failed',
                'failure_type': 'service_execution_failed',
                'query_source': query_source,
                'task_started_at': task_started_at,
                'task_finished_at': utc_now_iso(),
                'total_latency_ms': total_latency_ms,
                'total_cost': round(total_cost, 6),
                'step_count': step_index,
                'success_step_count': success_step_count,
                'review_success_count': review_success_count,
                'review_failure_count': review_failure_count,
                'steps': selected_history,
            }

        success_step_count += 1

    return {
        'run_id': run_id,
        'group_name': group_name,
        'task_id': task['task_id'],
        'scenario_family': scenario_family,
        'complexity_level': complexity_level,
        'task_prompt': task.get('task_prompt'),
        'required_service_categories': required_categories,
        'status': 'success',
        'failure_type': None,
        'task_started_at': task_started_at,
        'task_finished_at': utc_now_iso(),
        'total_latency_ms': total_latency_ms,
        'total_cost': round(total_cost, 6),
        'step_count': len(required_categories),
        'success_step_count': success_step_count,
        'review_success_count': review_success_count,
        'review_failure_count': review_failure_count,
        'steps': selected_history,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='通过本地 AgentDNS HTTP 接口执行实验任务。')
    parser.add_argument('--group-name', default='基础解析组')
    parser.add_argument('--tasks', type=Path, default=DEFAULT_TASKS)
    parser.add_argument('--groups', type=Path, default=DEFAULT_GROUPS)
    parser.add_argument('--runtime-config', type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument('--output-dir', type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument('--agent-index', type=int, default=0)
    parser.add_argument('--max-tasks', type=int, default=8)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    load_group_definition(args.groups, args.group_name)
    tasks = load_json(args.tasks)['tasks'][: args.max_tasks]
    client = AgentDNSHttpClient(args.runtime_config)
    agent = client.config['agents'][args.agent_index]
    run_id = f"{args.group_name}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    rows = []
    for task in tasks:
        rows.append(run_task(client, agent['api_key'], args.group_name, task, run_id))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_dir / f"{args.group_name}_local_http_runs.jsonl"
    with output_path.open('w', encoding='utf-8') as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f'已写出本地 HTTP 运行结果：{output_path}')


if __name__ == '__main__':
    main()
