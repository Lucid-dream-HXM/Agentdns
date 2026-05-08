#!/bin/bash

# 确保在项目根目录运行（关键！）
cd "$(dirname "$0")"

# 检查并启动数据库服务
echo "Checking database services..."

# 尝试启动 PostgreSQL 服务
if ! sudo service postgresql status 2>/dev/null | grep -q "online"; then
    echo "Starting PostgreSQL service..."
    sudo service postgresql start
fi

# 检查数据库是否存在，如果不存在则创建
DB_EXISTS=$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='agentdns';")

if [ "$DB_EXISTS" != '1' ]; then
    echo "Creating database and user for AgentDNS..."
    sudo -u postgres psql -c "CREATE USER agentdns WITH PASSWORD 'your_password_here';"
    sudo -u postgres createdb -O agentdns agentdns
else
    echo "Database 'agentdns' already exists."
fi

echo "Starting AgentDNS backend..."
uvicorn agentdns-backend.app.main:app \
  --reload \
  --host 0.0.0.0 \
  --port 8000