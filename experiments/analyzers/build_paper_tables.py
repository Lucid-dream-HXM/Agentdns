from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List


def load_csv(path: Path) -> Dict[str, str]:
    with path.open('r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return next(reader)


def collect_group_summaries(root: Path) -> List[Dict[str, str]]:
    rows = []
    for summary_path in root.rglob('minimal_summary.csv'):
        row = load_csv(summary_path)
        row['group_id'] = summary_path.parent.name
        row['experiment_id'] = summary_path.parent.parent.name
        rows.append(row)
    return rows


def collect_lifecycle_summaries(root: Path) -> List[Dict[str, str]]:
    rows = []
    for csv_path in root.rglob('lifecycle_summary.csv'):
        with csv_path.open('r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                row['group_id'] = csv_path.parent.name
                row['experiment_id'] = csv_path.parent.parent.name
                rows.append(row)
    return rows


def write_csv(path: Path, rows: List[Dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='构建论文级结果总表。')
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    group_rows = collect_group_summaries(args.root)
    lifecycle_rows = collect_lifecycle_summaries(args.root)
    write_csv(args.output_dir / 'paper_group_summary.csv', group_rows)
    write_csv(args.output_dir / 'paper_lifecycle_summary.csv', lifecycle_rows)
    print(f'已写出论文级表格：{args.output_dir}')


if __name__ == '__main__':
    main()
