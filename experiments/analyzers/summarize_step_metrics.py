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
    success = sum(1 for row in rows if row['step_success'])
    quality = [float(row['oracle_step_quality_score']) for row in rows]
    consumability = [float(row['oracle_step_consumability_score']) for row in rows]
    return {
        'step_count': total,
        'step_success_count': success,
        'step_success_rate': round(success / total, 4) if total else 0.0,
        'avg_step_quality': round(mean(quality), 4) if quality else 0.0,
        'std_step_quality': round(pstdev(quality), 4) if len(quality) > 1 else 0.0,
        'avg_step_consumability': round(mean(consumability), 4) if consumability else 0.0,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='汇总步骤级指标。')
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
    print(f'已写出步骤级汇总：{args.output}')


if __name__ == '__main__':
    main()
