#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/hxm/projects/AgentDNS"
PY="$ROOT/agentdns-new-backend/venv/bin/python"
OUT="$ROOT/thesis_figures/chapter5"

mkdir -p "$OUT"

cd "$ROOT/agentdns-backend"
DATABASE_URL="sqlite:///$OUT/agentdns_figures.db" \
OPENAI_API_KEY="" \
ENCRYPTION_KEY="I2L9UG4DfbcTgSEbvqQZtfJ3Q1zHhFHZ6vVsAnKf6vk=" \
REDIS_URL="redis://localhost:6379/15" \
nohup "$PY" -m uvicorn app.main:app --host 127.0.0.1 --port 8010 \
  > "$OUT/backend.log" 2>&1 &
echo $! > "$OUT/backend.pid"

cd "$ROOT"
nohup "$PY" -m uvicorn thesis_figures.chapter5.mock_translation_service:app --host 127.0.0.1 --port 8011 \
  > "$OUT/mock.log" 2>&1 &
echo $! > "$OUT/mock.pid"

echo "backend_pid=$(cat "$OUT/backend.pid")"
echo "mock_pid=$(cat "$OUT/mock.pid")"
