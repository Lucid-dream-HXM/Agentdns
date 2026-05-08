#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "[INFO] Starting Mock Service on port 9001..."
nohup python3 mock_service.py > mock_service.log 2>&1 &
echo "[INFO] Mock Service started with PID $!"
sleep 2
curl -s http://localhost:9001/health && echo " - Mock Service is healthy"