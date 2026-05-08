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
    matches = sum(1 for row in rows if row['service_type_match'])
    regrets = [float(row['selection_regret']) for row in rows]
    pool_sizes = [int(row['candidate_pool_size']) for row in rows]
    return {
        'selection_count': total,
        'service_type_match_rate': round(matches / total, 4) if total else 0.0,
        'avg_selection_regret': round(mean(regrets), 4) if regrets else 0.0,
        'std_selection_regret': round(pstdev(regrets), 4) if len(regrets) > 1 else 0.0,
        'avg_candidate_pool_size': round(mean(pool_sizes), 2) if pool_sizes else 0.0,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='汇总选择级指标。')
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
    print(f'已写出选择级汇总：{args.output}')


if __name__ == '__main__':
    main()
