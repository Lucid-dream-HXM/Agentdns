from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME = ROOT / 'configs' / 'local_runtime.yaml'

GROUPS = [
    '直接通用服务组',
    '简单规则路由组',
    '基础解析组',
    '向量召回增强组',
    '信任反馈闭环组',
    '完整多步协同组',
]


def run_command(cmd: List[str]) -> None:
    print('执行:', ' '.join(str(item) for item in cmd))
    subprocess.run(cmd, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='通过本地 AgentDNS HTTP 接口顺序运行正式实验组。')
    parser.add_argument('--python', default=sys.executable)
    parser.add_argument('--runtime-config', type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument('--max-tasks', type=int, default=8)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'outputs' / 'local_http_suite')
    return parser.parse_args()


def summarize_group(output_path: Path) -> Dict[str, object]:
    rows = [json.loads(line) for line in output_path.read_text(encoding='utf-8').splitlines() if line.strip()]
    total = len(rows)
    success = sum(1 for row in rows if row.get('status') == 'success')
    failed = total - success
    avg_cost = round(sum(float(row.get('total_cost') or 0.0) for row in rows) / total, 6) if total else 0.0
    avg_latency_ms = round(sum(int(row.get('total_latency_ms') or 0) for row in rows) / total, 2) if total else 0.0
    avg_steps = round(sum(int(row.get('step_count') or 0) for row in rows) / total, 2) if total else 0.0
    review_success = sum(int(row.get('review_success_count') or 0) for row in rows)
    review_failed = sum(int(row.get('review_failure_count') or 0) for row in rows)
    return {
        'file': output_path.name,
        'total_tasks': total,
        'success_tasks': success,
        'failed_tasks': failed,
        'success_rate': round(success / total, 4) if total else 0.0,
        'avg_total_cost': avg_cost,
        'avg_total_latency_ms': avg_latency_ms,
        'avg_steps': avg_steps,
        'review_success_count': review_success,
        'review_failure_count': review_failed,
    }


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    suite_run_id = datetime.now(timezone.utc).strftime('local_http_suite_%Y%m%dT%H%M%SZ')
    summaries: List[Dict[str, object]] = []

    for group_name in GROUPS:
        run_command([
            args.python,
            str(ROOT / 'runners' / 'local_http_runner.py'),
            '--group-name', group_name,
            '--runtime-config', str(args.runtime_config),
            '--max-tasks', str(args.max_tasks),
            '--output-dir', str(args.output_dir),
        ])
        output_path = args.output_dir / f'{group_name}_local_http_runs.jsonl'
        if output_path.exists():
            group_summary = summarize_group(output_path)
            group_summary['group_name'] = group_name
            summaries.append(group_summary)

    manifest = {
        'suite_run_id': suite_run_id,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'max_tasks': args.max_tasks,
        'groups': summaries,
    }
    manifest_path = args.output_dir / 'suite_manifest.json'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'已写出 suite 清单：{manifest_path}')


if __name__ == '__main__':
    main()
