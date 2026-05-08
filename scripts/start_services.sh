#!/bin/bash
set -m

cd /home/hxm/projects/AgentDNS/agentdns-backend

echo "[1/4] Starting uvicorn..."
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
UVICORN_PID=$!
echo "Uvicorn PID: $UVICORN_PID"

echo "[2/4] Waiting 12s for backend to be ready..."
sleep 12

echo "[3/4] Starting mock service..."
python3 /home/hxm/projects/AgentDNS/experiments/mock_services/mock_service.py &
MOCK_PID=$!
echo "Mock PID: $MOCK_PID"

echo "[4/4] Waiting 3s for mock to be ready..."
sleep 3

echo "Checking backend..."
curl -s --connect-timeout 5 http://127.0.0.1:8000/docs | head -1 || echo "Backend not ready"

echo ""
echo "Backend and Mock are running. Ready for smoke test."
echo "Uvicorn PID: $UVICORN_PID"
echo "Mock PID: $MOCK_PID"
echo ""

# Don't exit - keep services running
wait
