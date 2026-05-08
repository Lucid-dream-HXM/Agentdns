from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
import yaml

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME_CONFIG = ROOT / 'configs' / 'local_runtime.yaml'


class AgentDNSHttpClient:
    """面向本地 AgentDNS HTTP 接口的轻量客户端。

    这一版在原始 batch6 的基础上增强了三个能力：
    1. 为 discovery / call / review / trust 请求记录客户端侧耗时；
    2. 提供 detail 版本方法，返回 response body、headers、status_code、latency 等元信息；
    3. 保持旧方法兼容，避免影响已有调用逻辑。
    """

    def __init__(self, runtime_config_path: Path = DEFAULT_RUNTIME_CONFIG):
        self.runtime_config_path = runtime_config_path
        self.config = self._load_yaml(runtime_config_path)['runtime']
        self.base_url = self.config['base_url'].rstrip('/')
        self.timeout = int(self.config['request_timeout_sec'])
        self.endpoint_paths = self.config['endpoint_paths']

    @staticmethod
    def _load_yaml(path: Path) -> Dict[str, Any]:
        with path.open('r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def auth_headers(self, api_key: str) -> Dict[str, str]:
        headers = dict(self.config.get('default_headers', {}))
        headers['Authorization'] = f'Bearer {api_key}'
        return headers

    def build_url(self, endpoint_key: str, **kwargs: Any) -> str:
        path_template = self.endpoint_paths[endpoint_key]
        return f"{self.base_url}{path_template.format(**kwargs)}"

    @staticmethod
    def _safe_json(response: requests.Response) -> Dict[str, Any]:
        try:
            return response.json()
        except json.JSONDecodeError:
            return {'raw_response': response.text}

    def _post_json(self, *, url: str, api_key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        started = time.perf_counter()
        response = requests.post(
            url,
            headers=self.auth_headers(api_key),
            json=payload,
            timeout=self.timeout,
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        body = self._safe_json(response)
        return {
            'status_code': response.status_code,
            'headers': dict(response.headers),
            'body': body,
            'latency_ms': latency_ms,
            'response': response,
        }

    def _get_json(self, *, url: str, api_key: str) -> Dict[str, Any]:
        started = time.perf_counter()
        response = requests.get(
            url,
            headers=self.auth_headers(api_key),
            timeout=self.timeout,
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        body = self._safe_json(response)
        response.raise_for_status()
        return {
            'status_code': response.status_code,
            'headers': dict(response.headers),
            'body': body,
            'latency_ms': latency_ms,
            'response': response,
        }

    def search_services_detailed(
        self,
        *,
        api_key: str,
        query: str,
        category: Optional[str],
        include_trust: bool,
        sort_by: str,
        limit: Optional[int] = None,
        max_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            'query': query,
            'return_tool_format': False,
            'include_trust': include_trust,
            'sort_by': sort_by,
            'limit': limit or self.config.get('search_top_k', 10),
        }
        if category:
            payload['category'] = category
        if max_price is not None:
            payload['max_price'] = max_price

        result = self._post_json(
            url=self.build_url('discovery_search'),
            api_key=api_key,
            payload=payload,
        )
        body = result['body']
        result.update({
            'request_payload': payload,
            'services': body.get('services', []),
            'total': body.get('total'),
            'query': body.get('query', query),
        })
        return result

    def search_services(
        self,
        *,
        api_key: str,
        query: str,
        category: Optional[str],
        include_trust: bool,
        sort_by: str,
        limit: Optional[int] = None,
        max_price: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        return self.search_services_detailed(
            api_key=api_key,
            query=query,
            category=category,
            include_trust=include_trust,
            sort_by=sort_by,
            limit=limit,
            max_price=max_price,
        )['services']

    def call_service_detailed(
        self,
        *,
        api_key: str,
        service: Dict[str, Any],
        task_input: Dict[str, Any],
    ) -> Dict[str, Any]:
        capabilities = service.get('capabilities') or {}
        service_key = capabilities.get('service_key') or task_input.get('service_key')
        if not service_key:
            raise RuntimeError(f"服务 {service.get('name', '<unknown>')} 缺少 capabilities.service_key")

        payload = {
            'agentdns_url': service['agentdns_uri'],
            'input_data': {
                'service_key': service_key,
                'task_input': task_input,
                'stage': task_input.get('stage', 'formal_experiment'),
            },
            'method': 'POST',
        }
        result = self._post_json(
            url=self.build_url('service_call'),
            api_key=api_key,
            payload=payload,
        )
        response = result['response']
        result.update({
            'request_payload': payload,
            'usage_id': self.extract_usage_id(response),
            'call_status': result['body'].get('status'),
            'call_result': result['body'].get('result'),
        })
        return result

    def call_service(
        self,
        *,
        api_key: str,
        service: Dict[str, Any],
        task_input: Dict[str, Any],
    ) -> requests.Response:
        return self.call_service_detailed(
            api_key=api_key,
            service=service,
            task_input=task_input,
        )['response']

    def submit_review_detailed(self, *, api_key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        result = self._post_json(
            url=self.build_url('submit_review'),
            api_key=api_key,
            payload=payload,
        )
        result['request_payload'] = payload
        return result

    def submit_review(self, *, api_key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self.submit_review_detailed(api_key=api_key, payload=payload)['body']

    def get_trust_summary_detailed(self, *, api_key: str, service_id: int) -> Dict[str, Any]:
        result = self._get_json(
            url=self.build_url('trust_summary', service_id=service_id),
            api_key=api_key,
        )
        result['service_id'] = service_id
        return result

    def get_trust_summary(self, *, api_key: str, service_id: int) -> Dict[str, Any]:
        return self.get_trust_summary_detailed(api_key=api_key, service_id=service_id)['body']

    @staticmethod
    def extract_usage_id(response: requests.Response) -> Optional[int]:
        value = response.headers.get('X-AgentDNS-Usage-ID')
        if not value:
            return None
        try:
            return int(value)
        except ValueError:
            return None

    @staticmethod
    def parse_response_body(response: requests.Response) -> Dict[str, Any]:
        try:
            return response.json()
        except json.JSONDecodeError:
            return {'raw_response': response.text}
