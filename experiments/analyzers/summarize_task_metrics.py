from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Dict, List


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows = []
    with path.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def summarize(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(rows)
    success = sum(1 for row in rows if row['task_success'])
    utilities = [float(row['oracle_final_utility']) for row in rows]
    costs = [float(row['oracle_total_cost']) for row in rows]
    latencies = [int(row['oracle_total_latency_ms']) for row in rows]
    return {
        'task_count': total,
        'task_success_count': success,
        'task_success_rate': round(success / total, 4) if total else 0.0,
        'avg_oracle_utility': round(mean(utilities), 4) if utilities else 0.0,
        'std_oracle_utility': round(pstdev(utilities), 4) if len(utilities) > 1 else 0.0,
        'avg_total_cost': round(mean(costs), 4) if costs else 0.0,
        'avg_total_latency_ms': round(mean(latencies), 2) if latencies else 0.0,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='汇总任务级指标。')
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = load_jsonl(args.input)
    summary = summarize(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(summary.keys()))
        writer.writeheader()
        writer.writerow(summary)
    print(f'已写出汇总结果：{args.output}')


if __name__ == '__main__':
    main()
