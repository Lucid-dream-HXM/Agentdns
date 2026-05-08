import html
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple
from urllib.parse import quote

import httpx


ROOT = Path("/home/hxm/projects/AgentDNS")
OUT = ROOT / "thesis_figures" / "chapter5"
BASE_URL = os.environ.get("AGENTDNS_BASE_URL", "http://127.0.0.1:8010")
MOCK_URL = os.environ.get("MOCK_TRANSLATION_URL", "http://127.0.0.1:8011/translate")


def wait_for_service(url: str, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            response = httpx.get(url, timeout=2.0)
            if response.status_code < 500:
                return
        except Exception as exc:
            last_error = exc
        time.sleep(0.5)
    raise RuntimeError(f"Service not ready: {url}; last_error={last_error}")


def request(
    client: httpx.Client,
    method: str,
    path: str,
    *,
    token: str = None,
    json_body: Dict[str, Any] = None,
    params: Dict[str, Any] = None,
) -> Tuple[httpx.Response, Dict[str, Any]]:
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = client.request(
        method,
        f"{BASE_URL}{path}",
        headers=headers,
        json=json_body,
        params=params,
        timeout=30.0,
    )
    try:
        parsed = response.json()
    except Exception:
        parsed = {"raw_response": response.text}
    if response.status_code >= 400:
        raise RuntimeError(f"{method} {path} failed: {response.status_code} {parsed}")
    return response, parsed


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: ("***REDACTED***" if key.lower() in {"access_token", "token", "service_api_key", "api_key", "email"} else redact(val))
            for key, val in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str) and "@" in value:
        return value.split("@", 1)[0][:2] + "***@***"
    return value


def pick(obj: Dict[str, Any], keys: Iterable[str]) -> Dict[str, Any]:
    return {key: obj.get(key) for key in keys if key in obj}


def json_pretty(obj: Any) -> str:
    return json.dumps(redact(obj), ensure_ascii=False, indent=2, default=str)


def code_block(obj: Any) -> str:
    return html.escape(json_pretty(obj))


def method_badge(method: str) -> str:
    colors = {"GET": "get", "POST": "post", "PUT": "put", "DELETE": "delete"}
    return f'<span class="method {colors.get(method, "post")}">{html.escape(method)}</span>'


def endpoint(method: str, path: str) -> str:
    return f'<div class="endpoint">{method_badge(method)}<span>{html.escape(path)}</span></div>'


def panel(title: str, method: str, path: str, request_body: Any, response_body: Any, status: str = "200 OK", headers: Dict[str, Any] = None) -> str:
    header_html = ""
    if headers:
        header_html = f'<div class="meta">响应头: <code>{html.escape(json.dumps(headers, ensure_ascii=False))}</code></div>'
    return f"""
    <section class="panel">
      <div class="panel-head">
        <div>
          <h2>{html.escape(title)}</h2>
          {endpoint(method, path)}
        </div>
        <div class="status">{html.escape(status)}</div>
      </div>
      <div class="grid two">
        <div>
          <h3>请求参数</h3>
          <pre>{code_block(request_body)}</pre>
        </div>
        <div>
          <h3>真实响应</h3>
          <pre>{code_block(response_body)}</pre>
          {header_html}
        </div>
      </div>
    </section>
    """


def write_html(name: str, title: str, body: str, subtitle: str = "") -> Path:
    path = OUT / name
    style = """
    :root {
      color: #172033;
      background: #f6f8fb;
      font-family: "Inter", "Segoe UI", "Microsoft YaHei", Arial, sans-serif;
    }
    * { box-sizing: border-box; }
    body { margin: 0; background: #f6f8fb; }
    .page { width: 1440px; min-height: 920px; padding: 44px 54px; }
    .titlebar { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 26px; border-bottom: 2px solid #d9e1ec; padding-bottom: 18px; }
    h1 { margin: 0; font-size: 34px; letter-spacing: 0; color: #152238; }
    .subtitle { margin-top: 8px; font-size: 18px; color: #53627a; }
    .chip { border: 1px solid #bfd0e5; background: #fff; border-radius: 6px; padding: 8px 12px; font-size: 16px; color: #41516b; }
    .panel { background: #fff; border: 1px solid #d8e0ec; border-radius: 8px; box-shadow: 0 10px 26px rgba(26, 47, 75, .08); padding: 22px; margin-bottom: 22px; }
    .panel-head { display: flex; justify-content: space-between; gap: 22px; align-items: flex-start; margin-bottom: 18px; }
    h2 { margin: 0 0 10px; font-size: 24px; letter-spacing: 0; color: #1c2a44; }
    h3 { margin: 0 0 9px; font-size: 16px; letter-spacing: 0; color: #40506a; font-weight: 700; }
    .endpoint { display: flex; align-items: center; gap: 10px; font-family: "Cascadia Mono", "JetBrains Mono", Consolas, monospace; color: #2f425f; font-size: 16px; }
    .method { min-width: 58px; text-align: center; color: #fff; border-radius: 4px; padding: 5px 8px; font-weight: 800; font-size: 14px; }
    .post { background: #2f855a; } .get { background: #2563a8; } .put { background: #8a5b12; } .delete { background: #b83232; }
    .status { flex: 0 0 auto; background: #e8f6ef; color: #176447; border: 1px solid #b7e2cc; border-radius: 6px; padding: 8px 12px; font-weight: 800; font-size: 16px; }
    .grid { display: grid; gap: 18px; }
    .two { grid-template-columns: 1fr 1fr; }
    pre { margin: 0; min-height: 250px; max-height: 560px; overflow: hidden; white-space: pre-wrap; word-break: break-word; background: #0f172a; color: #e6edf7; border-radius: 7px; padding: 18px; font: 15px/1.46 "Cascadia Mono", "JetBrains Mono", Consolas, monospace; }
    .meta { margin-top: 12px; font-size: 15px; color: #4a5a73; }
    code { font-family: "Cascadia Mono", "JetBrains Mono", Consolas, monospace; background: #eef3f9; color: #21324d; padding: 2px 5px; border-radius: 4px; }
    .note { color: #5a6b82; font-size: 15px; margin-top: 10px; }
    .wide pre { max-height: 690px; }
    """
    path.write_text(
        f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(title)}</title>
  <style>{style}</style>
</head>
<body>
  <main class="page">
    <header class="titlebar">
      <div>
        <h1>{html.escape(title)}</h1>
        <div class="subtitle">{html.escape(subtitle)}</div>
      </div>
      <div class="chip">AgentDNS / FastAPI / API v1</div>
    </header>
    {body}
  </main>
</body>
</html>
""",
        encoding="utf-8",
    )
    return path


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    wait_for_service(f"{BASE_URL}/health")
    wait_for_service("http://127.0.0.1:8011/health")

    stamp = str(int(time.time()))
    username = f"figuser_{stamp}"
    email = f"figuser_{stamp}@example.com"
    password = "AgentDNS2026!"
    org_name = f"thesis-ai-{stamp}"
    agentdns_path = f"{org_name}/nlp/translate"

    with httpx.Client() as client:
        _, user = request(
            client,
            "POST",
            "/api/v1/auth/register",
            json_body={
                "username": username,
                "email": email,
                "full_name": "Thesis Figure User",
                "is_active": True,
                "password": password,
            },
        )
        _, login = request(
            client,
            "POST",
            "/api/v1/auth/login",
            json_body={"username": username, "password": password},
        )
        token = login["access_token"]
        _, org = request(
            client,
            "POST",
            "/api/v1/organizations/",
            token=token,
            json_body={
                "name": org_name,
                "domain": f"{org_name}.agentdns.test",
                "display_name": "Thesis AI Services",
                "description": "AgentDNS thesis demonstration organization",
                "website": "https://agentdns.local",
            },
        )
        service_body = {
            "name": "TextTranslateAgent",
            "category": "nlp",
            "description": "Text translation service for LLM multi-agent workflows. Supports translate language conversion summary.",
            "version": "1.0.0",
            "is_public": True,
            "endpoint_url": MOCK_URL,
            "protocol": "HTTP",
            "authentication_required": False,
            "pricing_model": "per_request",
            "price_per_unit": 0.0,
            "currency": "CNY",
            "tags": ["translation", "translate", "nlp", "llm-agent"],
            "capabilities": {
                "task": "text_translation",
                "source_lang": "zh",
                "target_lang": "en",
                "agentdns": True,
            },
            "agentdns_path": agentdns_path,
            "http_method": "POST",
            "http_mode": "sync",
            "input_description": "{\"text\":\"string\",\"source_lang\":\"zh\",\"target_lang\":\"en\"}",
            "output_description": "{\"translated_text\":\"string\",\"quality\":\"demo\"}",
        }
        service_resp, service = request(
            client,
            "POST",
            "/api/v1/services/",
            token=token,
            params={"organization_id": org["id"]},
            json_body=service_body,
        )

        search_body = {
            "query": "查找可用于文本翻译的服务 translate language conversion",
            "category": "nlp",
            "organization": org_name,
            "protocol": "HTTP",
            "limit": 5,
            "return_tool_format": True,
            "sort_by": "relevance",
            "include_trust": True,
        }
        search_resp, search = request(
            client,
            "POST",
            "/api/v1/client/discovery/search",
            token=token,
            json_body=search_body,
        )
        agentdns_uri = service["agentdns_uri"]
        resolve_path = f"/api/v1/discovery/resolve/{quote(agentdns_uri, safe='')}"
        resolve_resp, resolve = request(client, "GET", resolve_path, token=token)

        call_body = {
            "agentdns_url": agentdns_uri,
            "input_data": {
                "text": "面向LLM多智能体的根域名解析系统",
                "source_lang": "zh",
                "target_lang": "en",
                "task_id": "thesis-fig-5-5",
            },
            "method": "POST",
        }
        call_resp, call_result = request(
            client,
            "POST",
            "/api/v1/client/services/call",
            token=token,
            json_body=call_body,
        )
        tracking = {
            "X-AgentDNS-Usage-ID": call_resp.headers.get("X-AgentDNS-Usage-ID"),
            "X-AgentDNS-Request-ID": call_resp.headers.get("X-AgentDNS-Request-ID"),
        }

    registration_response = pick(
        service,
        [
            "id",
            "name",
            "category",
            "agentdns_uri",
            "protocol",
            "http_method",
            "http_mode",
            "price_per_unit",
            "organization_id",
            "created_at",
        ],
    )
    registration_request = pick(
        service_body,
        [
            "name",
            "category",
            "description",
            "endpoint_url",
            "protocol",
            "http_method",
            "http_mode",
            "price_per_unit",
            "agentdns_path",
        ],
    )
    registration_request["organization_id"] = org["id"]
    registration_request["endpoint_url"] = "http://127.0.0.1:8011/translate"

    fig3 = panel(
        "服务注册接口测试结果",
        "POST",
        f"/api/v1/services/?organization_id={org['id']}",
        {
            "organization_id": org["id"],
            "service": registration_request,
        },
        registration_response,
        status=f"{service_resp.status_code} Created/OK",
    )
    write_html(
        "fig5_3_service_register.html",
        "图5.3 服务注册接口测试结果图",
        fig3,
        "服务注册 -> AgentDNS URI 生成 -> 返回服务基础信息",
    )

    search_view = {
        "query": search.get("query"),
        "total": search.get("total"),
        "tools": [
            pick(item, ["name", "organization", "agentdns_url", "protocol", "method", "http_mode", "trust_score", "success_rate", "rating_count"])
            for item in search.get("tools", [])[:1]
        ],
    }
    resolve_view = pick(
        resolve,
        [
            "name",
            "organization",
            "agentdns_url",
            "protocol",
            "method",
            "http_mode",
            "trust_score",
            "success_rate",
            "rating_count",
        ],
    )
    fig4 = f"""
    <section class="panel wide">
      <div class="panel-head">
        <div>
          <h2>自然语言查询返回候选服务</h2>
          {endpoint("POST", "/api/v1/client/discovery/search")}
        </div>
        <div class="status">{search_resp.status_code} OK</div>
      </div>
      <div class="grid two">
        <div>
          <h3>查询请求</h3>
          <pre>{code_block(search_body)}</pre>
        </div>
        <div>
          <h3>候选服务结果</h3>
          <pre>{code_block(search_view)}</pre>
        </div>
      </div>
    </section>
    <section class="panel wide">
      <div class="panel-head">
        <div>
          <h2>AgentDNS URI 解析得到调用信息</h2>
          {endpoint("GET", "/api/v1/discovery/resolve/{agentdns_uri}")}
        </div>
        <div class="status">{resolve_resp.status_code} OK</div>
      </div>
      <div class="grid two">
        <div>
          <h3>解析目标</h3>
          <pre>{code_block({"agentdns_uri": agentdns_uri})}</pre>
        </div>
        <div>
          <h3>解析结果</h3>
          <pre>{code_block(resolve_view)}</pre>
        </div>
      </div>
    </section>
    """
    write_html(
        "fig5_4_search_and_resolve.html",
        "图5.4 服务查询与解析接口测试结果图",
        fig4,
        "自然语言查询 -> 候选工具列表 -> AgentDNS URI 解析",
    )

    call_view = {
        "proxy_call_status": "success",
        "upstream_result": call_result,
        "usage_tracking": tracking,
    }
    fig5 = panel(
        "代理调用接口测试结果",
        "POST",
        "/api/v1/client/services/call",
        call_body,
        call_view,
        status=f"{call_resp.status_code} OK",
    )
    write_html(
        "fig5_5_proxy_call.html",
        "图5.5 代理调用接口测试结果图",
        fig5,
        "AgentDNS URI -> proxy 层转发 -> mock 上游服务返回真实结果",
    )

    summary = {
        "base_url": BASE_URL,
        "mock_url": MOCK_URL,
        "user_id": user["id"],
        "organization_id": org["id"],
        "service_id": service["id"],
        "agentdns_uri": agentdns_uri,
        "usage_id": tracking["X-AgentDNS-Usage-ID"],
        "request_id": tracking["X-AgentDNS-Request-ID"],
        "html_files": [
            "fig5_3_service_register.html",
            "fig5_4_search_and_resolve.html",
            "fig5_5_proxy_call.html",
        ],
    }
    (OUT / "agentdns_api_run_summary.json").write_text(json_pretty(summary), encoding="utf-8")
    print(json_pretty(summary))


if __name__ == "__main__":
    main()
