from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List


def load_csv(path: Path) -> Dict[str, str]:
    with path.open('r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return next(reader)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='合并多个实验组的汇总结果。')
    parser.add_argument('--inputs', type=Path, nargs='+', required=True)
    parser.add_argument('--group-names', nargs='+', required=True)
    parser.add_argument('--output', type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows: List[Dict[str, str]] = []
    for group_name, path in zip(args.group_names, args.inputs):
        row = load_csv(path)
        row['group_name'] = group_name
        rows.append(row)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ['group_name'] + [key for key in rows[0].keys() if key != 'group_name']
    with args.output.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f'已输出组间比较结果：{args.output}')


if __name__ == '__main__':
    main()
