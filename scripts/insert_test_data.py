"""
插入全面的测试数据脚本
为所有API接口测试提供充足的数据
"""
from app.database import SessionLocal
from app.models.user import User
from app.models.organization import Organization
from app.models.service import Service, ServiceMetadata
from app.models.usage import Usage
from app.models.billing import Billing
from app.models.agent import Agent, AgentUsage
from app.models.async_task import AsyncTask
from app.core.security import get_password_hash
import json
import uuid
from datetime import datetime, timedelta

db = SessionLocal()

print("=" * 60)
print("开始插入全面的测试数据...")
print("=" * 60)

# ==================== 1. 创建多个用户 ====================
print("\n[1/8] 创建用户...")
users_data = [
    {"username": "admin", "email": "admin@example.com", "password": "admin123", "role": "admin", "balance": 1000.0},
    {"username": "testuser", "email": "test@example.com", "password": "password123", "role": "user", "balance": 100.0},
    {"username": "developer", "email": "dev@example.com", "password": "dev123", "role": "user", "balance": 500.0},
    {"username": "premium", "email": "premium@example.com", "password": "premium123", "role": "user", "balance": 10000.0},
    {"username": "newbie", "email": "newbie@example.com", "password": "newbie123", "role": "user", "balance": 10.0},
]

users = []
for user_data in users_data:
    existing = db.query(User).filter(User.email == user_data["email"]).first()
    if existing:
        users.append(existing)
        print(f"  ✓ 用户已存在: {existing.username}")
    else:
        user = User(
            username=user_data["username"],
            email=user_data["email"],
            hashed_password=get_password_hash(user_data["password"]),
            full_name=f"{user_data['username'].title()} User",
            role=user_data["role"],
            is_active=True,
            is_verified=True,
            balance=user_data["balance"]
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        users.append(user)
        print(f"  ✓ 创建用户: {user.username} (余额: ${user.balance})")

# ==================== 2. 创建多个组织 ====================
print("\n[2/8] 创建组织...")
orgs_data = [
    {"name": "tech-corp", "domain": "techcorp.com", "display_name": "Tech Corporation", "owner": users[0]},
    {"name": "ai-labs", "domain": "ailabs.io", "display_name": "AI Labs", "owner": users[1]},
    {"name": "cloud-services", "domain": "cloudsvc.net", "display_name": "Cloud Services Inc", "owner": users[2]},
    {"name": "data-analytics", "domain": "dataanalytics.ai", "display_name": "Data Analytics Pro", "owner": users[3]},
]

organizations = []
for org_data in orgs_data:
    existing = db.query(Organization).filter(Organization.name == org_data["name"]).first()
    if existing:
        organizations.append(existing)
        print(f"  ✓ 组织已存在: {existing.name}")
    else:
        org = Organization(
            name=org_data["name"],
            domain=org_data["domain"],
            display_name=org_data["display_name"],
            description=f"This is {org_data['display_name']}",
            website=f"https://{org_data['domain']}",
            owner_id=org_data["owner"].id
        )
        db.add(org)
        db.commit()
        db.refresh(org)
        organizations.append(org)
        print(f"  ✓ 创建组织: {org.name}")

# ==================== 3. 创建多个服务 ====================
print("\n[3/8] 创建服务...")
services_data = [
    # 搜索类服务
    {"name": "web-search", "category": "search", "org": organizations[0], "price": 0.01, "public": True, "path": "tech-corp/search/web"},
    {"name": "image-search", "category": "search", "org": organizations[0], "price": 0.02, "public": True, "path": "tech-corp/search/image"},
    {"name": "video-search", "category": "search", "org": organizations[0], "price": 0.03, "public": False, "path": "tech-corp/search/video"},
    
    # AI类服务
    {"name": "text-generation", "category": "ai", "org": organizations[1], "price": 0.05, "public": True, "path": "ai-labs/ai/text-gen"},
    {"name": "image-generation", "category": "ai", "org": organizations[1], "price": 0.10, "public": True, "path": "ai-labs/ai/image-gen"},
    {"name": "code-assistant", "category": "ai", "org": organizations[1], "price": 0.08, "public": True, "path": "ai-labs/ai/code"},
    {"name": "translation", "category": "ai", "org": organizations[1], "price": 0.02, "public": True, "path": "ai-labs/ai/translate"},
    
    # 云服务
    {"name": "storage", "category": "cloud", "org": organizations[2], "price": 0.001, "public": True, "path": "cloud-services/cloud/storage"},
    {"name": "compute", "category": "cloud", "org": organizations[2], "price": 0.05, "public": True, "path": "cloud-services/cloud/compute"},
    {"name": "database", "category": "cloud", "org": organizations[2], "price": 0.02, "public": False, "path": "cloud-services/cloud/db"},
    
    # 数据分析
    {"name": "data-visualization", "category": "analytics", "org": organizations[3], "price": 0.03, "public": True, "path": "data-analytics/analytics/viz"},
    {"name": "sentiment-analysis", "category": "analytics", "org": organizations[3], "price": 0.04, "public": True, "path": "data-analytics/analytics/sentiment"},
    {"name": "trend-prediction", "category": "analytics", "org": organizations[3], "price": 0.06, "public": True, "path": "data-analytics/analytics/trends"},
]

services = []
for svc_data in services_data:
    existing = db.query(Service).filter(Service.name == svc_data["name"]).first()
    if existing:
        services.append(existing)
        print(f"  ✓ 服务已存在: {existing.name}")
    else:
        service = Service(
            name=svc_data["name"],
            category=svc_data["category"],
            description=f"{svc_data['name'].replace('-', ' ').title()} service provided by {svc_data['org'].display_name}",
            version="1.0.0",
            is_public=svc_data["public"],
            endpoint_url=f"https://api.{svc_data['org'].domain}/{svc_data['name']}",
            protocol="http",
            authentication_required=False,
            pricing_model="per_request",
            price_per_unit=svc_data["price"],
            currency="USD",
            http_method="POST",
            http_mode="sync",
            agentdns_path=svc_data["path"],
            agentdns_uri=f"agentdns://{svc_data['path']}",
            organization_id=svc_data["org"].id
        )
        db.add(service)
        db.commit()
        db.refresh(service)
        services.append(service)
        print(f"  ✓ 创建服务: {service.name} (${service.price_per_unit}/req)")

# ==================== 4. 创建服务元数据 ====================
print("\n[4/8] 创建服务元数据...")
for i, service in enumerate(services):
    existing = db.query(ServiceMetadata).filter(ServiceMetadata.service_id == service.id).first()
    if existing:
        print(f"  ✓ 元数据已存在: {service.name}")
    else:
        metadata = ServiceMetadata(
            service_id=service.id,
            openapi_spec=json.dumps({
                "openapi": "3.0.0",
                "info": {"title": service.name, "version": "1.0.0"},
                "paths": {"/": {"post": {"summary": f"Use {service.name}"}}}
            }),
            examples=json.dumps([{"input": "example", "output": "result"}]),
            rate_limits=json.dumps({"requests_per_minute": 60, "requests_per_hour": 1000}),
            status="active",
            search_keywords=json.dumps([service.category, service.name, service.organization.display_name]),
            health_check_url=f"{service.endpoint_url}/health"
        )
        db.add(metadata)
        db.commit()
        print(f"  ✓ 创建元数据: {service.name}")

# ==================== 5. 创建代理 ====================
print("\n[5/8] 创建代理...")
agents_data = [
    {"name": "web-crawler", "user": users[1], "daily_limit": 50.0, "monthly_limit": 500.0},
    {"name": "chatbot", "user": users[1], "daily_limit": 20.0, "monthly_limit": 200.0},
    {"name": "data-processor", "user": users[2], "daily_limit": 100.0, "monthly_limit": 1000.0},
    {"name": "api-gateway", "user": users[3], "daily_limit": 500.0, "monthly_limit": 5000.0},
    {"name": "test-agent", "user": users[4], "daily_limit": 5.0, "monthly_limit": 50.0},
]

agents = []
for agent_data in agents_data:
    existing = db.query(Agent).filter(Agent.name == agent_data["name"], Agent.user_id == agent_data["user"].id).first()
    if existing:
        agents.append(existing)
        print(f"  ✓ 代理已存在: {existing.name}")
    else:
        agent = Agent(
            name=agent_data["name"],
            description=f"{agent_data['name'].replace('-', ' ').title()} agent for automated tasks",
            api_key=f"agentdns_{uuid.uuid4().hex[:32]}",
            cost_limit_daily=agent_data["daily_limit"],
            cost_limit_monthly=agent_data["monthly_limit"],
            user_id=agent_data["user"].id,
            allowed_services=json.dumps([]),
            rate_limit_per_minute=60
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)
        agents.append(agent)
        print(f"  ✓ 创建代理: {agent.name} (日限: ${agent.cost_limit_daily})")

# ==================== 6. 创建使用记录 ====================
print("\n[6/8] 创建使用记录...")
usage_count = 0
for user in users:
    for service in services[:5]:  # 每个用户使用前5个服务
        for _ in range(3):  # 每个服务使用3次
            usage = Usage(
                user_id=user.id,
                service_id=service.id,
                tokens_used=10 + (usage_count % 100),
                execution_time_ms=50 + (usage_count % 500),
                status_code=200 if usage_count % 10 != 0 else 500
            )
            db.add(usage)
            usage_count += 1

db.commit()
print(f"  ✓ 创建 {usage_count} 条使用记录")

# ==================== 7. 创建代理使用记录 ====================
print("\n[7/8] 创建代理使用记录...")
agent_usage_count = 0
for agent in agents:
    for service in services[:3]:  # 每个代理使用前3个服务
        for _ in range(2):  # 每个服务使用2次
            agent_usage = AgentUsage(
                agent_id=agent.id,
                service_name=service.name,
                request_method="POST",
                request_path=f"/api/{service.name}",
                cost=service.price_per_unit,
                tokens_used=20 + (agent_usage_count % 50),
                response_time_ms=100 + (agent_usage_count % 300),
                status_code=200
            )
            db.add(agent_usage)
            agent_usage_count += 1

db.commit()
print(f"  ✓ 创建 {agent_usage_count} 条代理使用记录")

# ==================== 8. 创建账单记录 ====================
print("\n[8/8] 创建账单记录...")
billing_types = ["usage", "topup", "refund"]
billing_statuses = ["completed", "pending", "failed"]

billing_count = 0
for user in users:
    for i in range(5):  # 每个用户5条账单
        billing = Billing(
            user_id=user.id,
            bill_id=f"BILL-{uuid.uuid4().hex[:12].upper()}",
            bill_type=billing_types[i % 3],
            amount=10.0 + (i * 5.5),
            currency="USD",
            status=billing_statuses[i % 3],
            service_name=services[i % len(services)].name if i % 3 == 0 else None,
            description=f"Test billing record {i+1} for {user.username}"
        )
        db.add(billing)
        billing_count += 1

db.commit()
print(f"  ✓ 创建 {billing_count} 条账单记录")

# ==================== 9. 创建异步任务 ====================
print("\n[9/8] 创建异步任务...")
task_states = ["pending", "running", "succeeded", "failed"]
task_count = 0

for user in users:
    for i, service in enumerate(services[:4]):  # 每个用户为前4个服务创建任务
        task = AsyncTask(
            id=str(uuid.uuid4()),
            service_id=service.id,
            user_id=user.id,
            state=task_states[i % 4],
            input_data=json.dumps({"query": f"test task {i}", "params": {"limit": 10}}),
            result_data=json.dumps({"results": ["item1", "item2"]}) if i % 4 == 2 else None,
            error_message="Connection timeout" if i % 4 == 3 else None,
            progress=0.0 if i % 4 == 0 else (0.5 if i % 4 == 1 else 1.0),
            external_task_id=f"ext_{uuid.uuid4().hex[:8]}",
            estimated_cost=service.price_per_unit * 10,
            actual_cost=service.price_per_unit * 10 if i % 4 == 2 else 0.0,
            is_billed=i % 4 == 2
        )
        db.add(task)
        task_count += 1

db.commit()
print(f"  ✓ 创建 {task_count} 个异步任务")

# ==================== 统计 ====================
print("\n" + "=" * 60)
print("测试数据插入完成！")
print("=" * 60)

# 统计各表数据量
tables = [
    ("users", User),
    ("organizations", Organization),
    ("services", Service),
    ("service_metadata", ServiceMetadata),
    ("usage_records", Usage),
    ("billing_records", Billing),
    ("agents", Agent),
    ("agent_usage", AgentUsage),
    ("async_tasks", AsyncTask)
]

print("\n数据库现状统计:")
print("-" * 40)
for table_name, model in tables:
    count = db.query(model).count()
    print(f"  {table_name:20s}: {count:4d} 条记录")

print("\n" + "=" * 60)
print("可用于测试的API:")
print("=" * 60)
print("""
✓ 用户认证: /auth/* (5个用户可登录)
✓ 组织管理: /organizations/* (4个组织)
✓ 服务管理: /services/* (12个服务)
✓ 服务发现: /discovery/* (多种类别服务)
✓ 代理转发: /proxy/* (12个服务可调用)
✓ 计费管理: /billing/* (25条账单记录)
✓ 代理管理: /agents/* (5个代理)
✓ 异步任务: /proxy/tasks/* (20个任务)
""")

db.close()
print("\n✅ 所有测试数据准备完毕！")
