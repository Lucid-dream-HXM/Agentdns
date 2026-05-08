#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)/experiments"
python "$ROOT/market/generate_service_instances.py" --output "$ROOT/outputs/sample/service_catalog.json"
python "$ROOT/market/validate_service_catalog.py" --catalog "$ROOT/outputs/sample/service_catalog.json"
python "$ROOT/market/export_market_seed.py" --catalog "$ROOT/outputs/sample/service_catalog.json" --output "$ROOT/outputs/sample/service_seed_payload.json"
python "$ROOT/tasks/instantiate_tasks.py" --output "$ROOT/outputs/sample/task_instances.json" --per-template 2
python "$ROOT/tasks/validate_task_instances.py" --tasks "$ROOT/outputs/sample/task_instances.json" --catalog "$ROOT/outputs/sample/service_catalog.json"
PYTHONPATH="$(cd "$(dirname "$0")" && pwd)" python "$ROOT/runners/end_to_end_runner.py" --group-name "基础解析组" --market "$ROOT/outputs/sample/service_catalog.json" --tasks "$ROOT/outputs/sample/task_instances.json" --output-dir "$ROOT/outputs/sample/run_results"
