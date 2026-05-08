from __future__ import annotations

import argparse
import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from experiments.local.agentdns_http_client import AgentDNSHttpClient


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='检查本地 AgentDNS 接口是否可用。')
    parser.add_argument('--config', type=Path, default=Path(__file__).resolve().parents[1] / 'configs' / 'local_runtime.yaml')
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client = AgentDNSHttpClient(args.config)
    agents = client.config['agents']
    if not agents:
        raise SystemExit('本地运行配置中缺少 agents')
    first_agent = agents[0]
    services = client.search_services(
        api_key=first_agent['api_key'],
        query='summary service',
        category=None,
        include_trust=True,
        sort_by='balanced',
        limit=3,
    )
    print({'base_url': client.base_url, 'candidate_count': len(services), 'first_service': services[0].get('name') if services else None})


if __name__ == '__main__':
    main()
