from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows = []
    with path.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def summarize_by_field(rows: List[Dict[str, Any]], field: str) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row[field])].append(row)

    output = []
    for key, items in grouped.items():
        total = len(items)
        success = sum(1 for item in items if item.get('task_success', False))
        utilities = [float(item.get('oracle_final_utility', 0.0)) for item in items]
        costs = [float(item.get('oracle_total_cost', 0.0)) for item in items]
        output.append({
            field: key,
            'task_count': total,
            'task_success_rate': round(success / total, 4) if total else 0.0,
            'avg_oracle_utility': round(mean(utilities), 4) if utilities else 0.0,
            'avg_total_cost': round(mean(costs), 4) if costs else 0.0,
        })
    return sorted(output, key=lambda x: x[field])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='按场景或复杂度拆分任务结果。')
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--field', choices=['scenario_family', 'complexity_level'], required=True)
    parser.add_argument('--output', type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = load_jsonl(args.input)
    summary = summarize_by_field(rows, args.field)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if not summary:
        raise SystemExit('无可汇总数据')
    with args.output.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        writer.writeheader()
        writer.writerows(summary)
    print(f'已写出拆分汇总：{args.output}')


if __name__ == '__main__':
    main()
