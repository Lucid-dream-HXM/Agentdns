from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any, Dict, List

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATES = ROOT / 'tasks' / 'task_templates.yaml'
DEFAULT_OUTPUT = ROOT / 'outputs' / 'sample' / 'task_instances.json'

DEFAULT_MATERIAL_POOL = {
    'office_study': [
        '请整理以下课程资料，抽取重点概念并生成结构化摘要。',
        '请把会议讨论内容整理成纪要，并提取关键行动项。',
        '请对学习笔记进行总结，并输出层级化要点。',
    ],
    'information_processing': [
        '从以下报道中抽取事件时间、地点、人物和结果，并输出 JSON。',
        '请把多段文本中的重复信息合并后进行结构化输出。',
        '请把原始材料转换为统一模板并校验字段完整性。',
    ],
    'complex_agent': [
        '请先规划处理流程，再完成多文档整合与最终结论生成。',
        '给定复杂任务描述，请拆分子任务并调用合适服务完成。',
        '请对多来源信息进行检索筛选、抽取与聚合。',
    ],
    'constrained_tasks': [
        '在预算有限前提下完成结构化抽取并输出合法 JSON。',
        '在时延受限条件下完成摘要与信息提取。',
        '请在低成本条件下输出格式正确、内容可消费的结果。',
    ],
}


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open('r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_task_templates(path: Path) -> List[Dict[str, Any]]:
    return load_yaml(path)['templates']


def instantiate_task(template: Dict[str, Any], index: int, rng: random.Random) -> Dict[str, Any]:
    scenario_family = template['scenario_family']
    prompt = rng.choice(DEFAULT_MATERIAL_POOL[scenario_family])
    return {
        'task_id': f"task_{scenario_family}_{index:03d}",
        'template_id': template['template_id'],
        'template_name': template['template_name'],
        'scenario_family': scenario_family,
        'complexity_level': template['complexity_level'],
        'task_prompt': prompt,
        'task_goal': template['task_goal'],
        'step_chain': template['step_chain'],
        'required_service_categories': template['required_service_categories'],
        'constraints': template['constraints'],
        'source_material_refs': [f'{scenario_family}_material_{index:03d}'],
    }


def build_task_instances(templates: List[Dict[str, Any]], per_template: int, seed: int) -> Dict[str, Any]:
    rng = random.Random(seed)
    instances: List[Dict[str, Any]] = []
    task_index = 1
    for template in templates:
        for _ in range(per_template):
            instances.append(instantiate_task(template, task_index, rng))
            task_index += 1
    return {
        'version': 1,
        'seed': seed,
        'task_count': len(instances),
        'tasks': instances,
    }


def save_task_instances(payload: Dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='实例化实验任务。')
    parser.add_argument('--templates', type=Path, default=DEFAULT_TEMPLATES)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--seed', type=int, default=20260419)
    parser.add_argument('--per-template', type=int, default=2)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    templates = load_task_templates(args.templates)
    payload = build_task_instances(templates, per_template=args.per_template, seed=args.seed)
    save_task_instances(payload, args.output)
    print(f"已生成任务实例：{args.output}，任务数量={payload['task_count']}")


if __name__ == '__main__':
    main()
