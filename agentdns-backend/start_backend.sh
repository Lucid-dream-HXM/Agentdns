#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "[INFO] Working directory: $SCRIPT_DIR"
echo "[INFO] Starting AgentDNS backend..."

nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
echo "[INFO] Backend starting in background with PID $!"