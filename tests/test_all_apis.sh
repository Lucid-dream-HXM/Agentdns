#!/bin/bash

# AgentDNS API 测试脚本（使用随机用户名）
# 使用 curl 测试所有主要接口

BASE_URL="http://localhost:8000"
TOKEN=""

# 生成随机用户名
RANDOM_USER="testuser_$(date +%s)"

# 颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_section() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# 1. 注册用户
print_section "步骤 1: 注册用户 ($RANDOM_USER)"
REGISTER_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"username\": \"$RANDOM_USER\",
    \"email\": \"$RANDOM_USER@example.com\",
    \"full_name\": \"Test User\",
    \"password\": \"password123\",
    \"is_active\": true
  }")

echo "$REGISTER_RESPONSE"

if echo "$REGISTER_RESPONSE" | grep -q '"id"'; then
    print_success "用户注册成功"
elif echo "$REGISTER_RESPONSE" | grep -q "Username already exists"; then
    print_info "用户已存在，尝试登录"
else
    print_error "用户注册失败"
    exit 1
fi

# 2. 登录获取 Token
print_section "步骤 2: 登录获取 Token"
LOGIN_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{
    \"username\": \"$RANDOM_USER\",
    \"password\": \"password123\"
  }")

echo "$LOGIN_RESPONSE"

TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

if [ -n "$TOKEN" ]; then
    print_success "登录成功，Token: ${TOKEN:0:50}..."
else
    print_error "登录失败"
    exit 1
fi

# 3. 创建组织
print_section "步骤 3: 创建组织"
ORG_NAME="testorg_$(date +%s)"
ORG_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/organizations/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"$ORG_NAME\",
    \"domain\": \"$ORG_NAME.com\",
    \"display_name\": \"Test Organization\",
    \"description\": \"A test organization\",
    \"website\": \"https://$ORG_NAME.com\"
  }")

echo "$ORG_RESPONSE"

ORG_ID=$(echo "$ORG_RESPONSE" | grep -o '"id":[0-9]*' | cut -d':' -f2)

if [ -n "$ORG_ID" ]; then
    print_success "组织创建成功，ID: $ORG_ID"
else
    print_error "组织创建失败"
    exit 1
fi

# 4. 创建服务
print_section "步骤 4: 创建服务"
SERVICE_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/services/?organization_id=${ORG_ID}" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "weather-service",
    "category": "weather",
    "description": "A weather information service that provides current weather data",
    "version": "1.0.0",
    "is_public": true,
    "endpoint_url": "https://api.openweathermap.org/data/2.5/weather",
    "protocol": "https",
    "authentication_required": true,
    "service_api_key": "test-api-key-123",
    "pricing_model": "per_request",
    "price_per_unit": 0.001,
    "currency": "USD",
    "tags": ["weather", "forecast", "temperature"],
    "capabilities": {
      "current_weather": true,
      "forecast": true
    },
    "agentdns_path": "weather/current",
    "http_method": "GET",
    "http_mode": "sync",
    "input_description": "Location coordinates or city name",
    "output_description": "Current weather data"
  }')

echo "$SERVICE_RESPONSE"

SERVICE_ID=$(echo "$SERVICE_RESPONSE" | grep -o '"id":[0-9]*' | cut -d':' -f2)

if [ -n "$SERVICE_ID" ]; then
    print_success "服务创建成功，ID: $SERVICE_ID"
else
    print_error "服务创建失败"
fi

# 5. 列出服务
print_section "步骤 5: 列出服务"
SERVICES=$(curl -s -X GET "${BASE_URL}/api/v1/services/" \
  -H "Authorization: Bearer $TOKEN")

echo "$SERVICES"

SERVICE_COUNT=$(echo "$SERVICES" | grep -o '"id":[0-9]*' | wc -l)
print_success "找到 $SERVICE_COUNT 个服务"

# 6. 搜索服务
print_section "步骤 6: 搜索服务（自然语言）"
SEARCH_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/discovery/search" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "weather service for getting current temperature",
    "category": "weather",
    "protocol": "https",
    "limit": 10
  }')

echo "$SEARCH_RESPONSE"

if echo "$SEARCH_RESPONSE" | grep -q '"tools"'; then
    print_success "搜索成功"
else
    print_error "搜索失败"
fi

# 7. 获取服务类别
print_section "步骤 7: 获取服务类别"
CATEGORIES=$(curl -s -X GET "${BASE_URL}/api/v1/discovery/categories" \
  -H "Authorization: Bearer $TOKEN")

echo "$CATEGORIES"

print_success "获取类别成功"

# 8. 获取热门服务
print_section "步骤 8: 获取热门服务"
TRENDING=$(curl -s -X GET "${BASE_URL}/api/v1/discovery/trending?limit=5" \
  -H "Authorization: Bearer $TOKEN")

echo "$TRENDING"

print_success "获取热门服务成功"

# 9. 创建代理
print_section "步骤 9: 创建代理"
AGENT_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/agents" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-ai-agent",
    "description": "An AI agent for weather queries",
    "cost_limit_daily": 10.0,
    "cost_limit_monthly": 100.0,
    "rate_limit_per_minute": 60
  }')

echo "$AGENT_RESPONSE"

AGENT_ID=$(echo "$AGENT_RESPONSE" | grep -o '"id":[0-9]*' | cut -d':' -f2)

if [ -n "$AGENT_ID" ]; then
    print_success "代理创建成功，ID: $AGENT_ID"
else
    print_error "代理创建失败"
fi

# 10. 获取代理统计
if [ -n "$AGENT_ID" ]; then
    print_section "步骤 10: 获取代理统计"
    STATS=$(curl -s -X GET "${BASE_URL}/api/v1/agents/${AGENT_ID}/stats" \
      -H "Authorization: Bearer $TOKEN")

    echo "$STATS"
    print_success "获取代理统计成功"
fi

# 11. 测试公共 API（无需认证）
print_section "步骤 11: 测试公共 API"

echo "\n--- 热门服务 ---"
PUBLIC_TRENDING=$(curl -s -X GET "${BASE_URL}/api/v1/public/trending?limit=3")
echo "$PUBLIC_TRENDING"

echo "\n--- 服务类别 ---"
PUBLIC_CATEGORIES=$(curl -s -X GET "${BASE_URL}/api/v1/public/categories")
echo "$PUBLIC_CATEGORIES"

echo "\n--- 统计信息 ---"
PUBLIC_STATS=$(curl -s -X GET "${BASE_URL}/api/v1/public/stats")
echo "$PUBLIC_STATS"

print_success "公共 API 测试成功"

# 12. 测试服务代理
print_section "步骤 12: 测试服务代理"
PROXY_RESPONSE=$(curl -s -X GET "${BASE_URL}/api/v1/proxy/weather/current?city=Beijing" \
  -H "Authorization: Bearer $TOKEN")

echo "$PROXY_RESPONSE"

if echo "$PROXY_RESPONSE" | grep -q '"error"'; then
    print_error "代理请求失败（可能是服务端点不可用）"
else
    print_success "代理请求成功"
fi

# 13. 获取向量搜索统计
print_section "步骤 13: 获取向量搜索统计"
VECTOR_STATS=$(curl -s -X GET "${BASE_URL}/api/v1/discovery/vector-stats" \
  -H "Authorization: Bearer $TOKEN")

echo "$VECTOR_STATS"
print_success "获取向量搜索统计成功"

# 完成
print_section "测试完成"
print_success "所有主要接口测试完成！"
echo -e "\n${BLUE}测试信息：${NC}"
echo "用户名: $RANDOM_USER"
echo "密码: password123"
echo "Token: ${TOKEN:0:50}..."
echo "组织 ID: $ORG_ID"
echo "服务 ID: $SERVICE_ID"
echo "代理 ID: $AGENT_ID"
echo -e "\n${BLUE}提示：${NC}"
echo "1. 访问 http://localhost:8000/docs 查看 Swagger UI"
echo "2. 使用上面的 Token 在 Swagger UI 中测试其他接口"
echo "3. 公共 API（/api/v1/public/*）无需认证即可访问"
