from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List


def read_csv_row(path: Path) -> Dict[str, str]:
    with path.open('r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return next(reader)


def collect_summaries(root: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for summary_path in root.rglob('minimal_summary.csv'):
        row = read_csv_row(summary_path)
        parents = summary_path.parts
        row['group_id'] = summary_path.parent.name
        row['experiment_id'] = summary_path.parent.parent.name
        maybe_variant = summary_path.parent.parent.parent.name if len(parents) >= 4 else ''
        if maybe_variant.endswith('_results'):
            row['market_variant'] = 'standard'
        else:
            row['market_variant'] = maybe_variant
        rows.append(row)
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='聚合所有主实验最小汇总结果。')
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = collect_summaries(args.root)
    if not rows:
        raise SystemExit('未发现 minimal_summary.csv')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f'已聚合实验结果：{args.output}')


if __name__ == '__main__':
    main()
