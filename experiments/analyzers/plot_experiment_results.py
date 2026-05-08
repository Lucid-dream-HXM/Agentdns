from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt

ELEMENT_BLUE = '#409EFF'
ELEMENT_GREEN = '#67C23A'
TEXT = '#303133'
GRID = '#EBEEF5'
BORDER = '#DCDFE6'

plt.rcParams['font.sans-serif'] = ['Noto Sans CJK JP', 'Noto Sans CJK SC', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def load_rows(path: Path):
    with path.open('r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def plot_bar(rows, metric, output_path: Path, title: str):
    labels = [row['group_id'] for row in rows]
    values = [float(row[metric]) for row in rows]
    fig, ax = plt.subplots(figsize=(12, 6), dpi=220)
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')
    colors = [ELEMENT_BLUE if i % 2 == 0 else ELEMENT_GREEN for i in range(len(values))]
    bars = ax.bar(labels, values, color=colors, zorder=3)
    ax.grid(axis='y', color=GRID, linewidth=1.2, zorder=0)
    for s in ['top', 'right']:
        ax.spines[s].set_visible(False)
    ax.spines['left'].set_color(BORDER)
    ax.spines['bottom'].set_color(BORDER)
    ax.set_title(title, fontsize=16, color=TEXT, weight='bold', pad=14)
    ax.tick_params(axis='x', rotation=25, labelsize=10)
    ax.tick_params(axis='y', labelsize=10, colors=TEXT)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value, f'{value:.4f}', ha='center', va='bottom', fontsize=9, color=TEXT)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches='tight')
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='生成论文级实验图。')
    parser.add_argument('--summary', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = load_rows(args.summary)
    if not rows:
        raise SystemExit('汇总文件为空')
    plot_bar(rows, 'task_success_rate', args.output_dir / 'task_success_rate.png', '各组任务成功率对比')
    plot_bar(rows, 'avg_oracle_utility', args.output_dir / 'avg_oracle_utility.png', '各组平均综合效用对比')
    plot_bar(rows, 'avg_total_cost', args.output_dir / 'avg_total_cost.png', '各组平均总成本对比')
    print(f'已生成论文级图表：{args.output_dir}')


if __name__ == '__main__':
    main()
