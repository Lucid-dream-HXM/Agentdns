from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

ROOT = Path(__file__).resolve().parents[1]


def run_command(cmd):
    print('执行:', ' '.join(str(item) for item in cmd))
    subprocess.run(cmd, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='顺序运行正式实验套件。')
    parser.add_argument('--python', default=sys.executable)
    parser.add_argument('--max-tasks', type=int, default=24)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    market = ROOT / 'outputs' / 'sample' / 'full_service_catalog.json'
    tasks = ROOT / 'outputs' / 'sample' / 'formal_task_instances_v2.json'
    market_dir = ROOT / 'outputs' / 'sample' / 'market_variants'

    run_command([args.python, str(ROOT / 'runners' / 'overall_effectiveness_runner.py'), '--market', str(market), '--tasks', str(tasks), '--output-dir', str(ROOT / 'outputs' / 'sample' / 'overall_effectiveness_suite'), '--max-tasks', str(args.max_tasks)])
    run_command([args.python, str(ROOT / 'runners' / 'ablation_runner.py'), '--market', str(market), '--tasks', str(tasks), '--output-dir', str(ROOT / 'outputs' / 'sample' / 'ablation_suite')])
    run_command([args.python, str(ROOT / 'runners' / 'robustness_runner.py'), '--market-dir', str(market_dir), '--tasks', str(tasks), '--output-dir', str(ROOT / 'outputs' / 'sample' / 'robustness_suite'), '--max-tasks', str(args.max_tasks)])
    run_command([args.python, str(ROOT / 'runners' / 'lifecycle_runner.py'), '--market', str(market), '--tasks', str(tasks), '--output-dir', str(ROOT / 'outputs' / 'sample' / 'lifecycle_suite'), '--max-tasks', str(args.max_tasks), '--rounds', '4'])


if __name__ == '__main__':
    main()
