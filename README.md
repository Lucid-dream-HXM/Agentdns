# AgentDNS

面向 LLM Agent 的根域名命名与服务发现系统。基于 DNS 命名思想，为 AI Agent 提供语义化服务注册、发现、代理调用与信任评价的完整基础设施。

## 核心特性

- **语义化服务发现** — 基于向量检索的自然语言服务搜索，支持按信任评分排序
- **AgentDNS URI 体系** — `agentdns://org/path` 格式的统一服务寻址
- **安全代理调用** — 内置认证、API Key 管理、用量追踪与计费闭环
- **信任评价体系** — 多维度服务评价（任务适配度、输出质量、协议遵从性等），自动计算信任分数
- **多协议支持** — HTTP/MCP/A2A 等多种服务协议
- **完整实验框架** — 冷启动、生命周期、鲁棒性、消融、诱骗市场等实验场景

## 技术栈

| 组件 | 技术 |
|------|------|
| Web 框架 | FastAPI |
| 数据库 | PostgreSQL |
| 向量数据库 | Milvus |
| ORM | SQLAlchemy |
| 认证 | JWT (passlib + bcrypt) |
| 嵌入模型 | 火山方舟 Doubao Embedding |
| 容器化 | Docker Compose |

## 快速开始

### 前置条件

- Linux / macOS
- Python 3.10+
- Docker & Docker Compose

### 1. 启动数据库服务

```bash
docker-compose up -d
```

### 2. 配置环境变量

```bash
cd agentdns-backend
cp .env.example .env
```

编辑 `.env`，填入：

- `ENCRYPTION_KEY` — 运行 `python scripts/generate_encryption_key.py` 生成
- `OPENAI_API_KEY` — 火山方舟 API Key
- `OPENAI_EMBEDDING_MODEL` — 接入点 ID

### 3. 启动后端

```bash
cd agentdns-backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 创建管理员

```bash
python scripts/create_admin.py
```

### 5. 验证

```bash
curl http://localhost:8000/health
```

访问 http://localhost:8000/docs 查看 Swagger API 文档。

## 项目结构

```
AgentDNS/
├── agentdns-backend/          # 后端服务
│   ├── app/
│   │   ├── api/               # API 路由
│   │   │   ├── client/        # 客户端 API（17 个模块）
│   │   │   ├── auth.py        # 认证
│   │   │   ├── services.py    # 服务管理
│   │   │   ├── discovery.py   # 服务发现
│   │   │   ├── proxy.py       # 服务代理
│   │   │   ├── reviews.py     # 评价与信任
│   │   │   └── ...
│   │   ├── core/              # 核心配置与安全
│   │   ├── models/            # 数据库模型
│   │   ├── schemas/           # Pydantic 数据模型
│   │   ├── services/          # 业务逻辑层
│   │   │   ├── trust_service.py     # 信任计算引擎
│   │   │   ├── billing_service.py   # 计费服务
│   │   │   ├── embedding_service.py # 嵌入服务
│   │   │   ├── milvus_service.py    # 向量检索服务
│   │   │   └── search_engine.py     # 搜索引擎
│   │   ├── database.py
│   │   └── main.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── experiments/               # 实验框架
│   ├── market/                # 市场数据生成
│   ├── tasks/                 # 任务实例化
│   ├── runners/               # 实验运行器
│   ├── mock_services/         # Mock 服务
│   ├── seeds/                 # 种子数据
│   └── outputs/               # 实验输出
├── thesis_figures/            # 论文图表生成
├── scripts/                   # 工具脚本
│   ├── init-db.sql            # 数据库初始化
│   ├── create_admin.py        # 创建管理员
│   ├── insert_test_data.py    # 插入测试数据
│   ├── backfill_trust_stats.py # 信任摘要回填
│   ├── clear_tables.py        # 清空数据表
│   ├── migrate_data.py        # 数据迁移
│   └── generate_encryption_key.py # 密钥生成
├── tests/                     # 测试脚本
│   ├── test_all_apis.py       # 全量 API 测试（Python）
│   ├── test_all_apis.sh       # 全量 API 测试（Bash）
│   ├── test_scenario1_auth_org.py       # 场景1：认证与组织
│   ├── test_scenario2_service_discovery.py # 场景2：服务发现
│   ├── test_scenario3_proxy_billing.py  # 场景3：代理与计费
│   ├── test_reviews_trust.py  # 评价信任闭环测试
│   ├── test_trust_sanity.py   # 信任机制验证
│   └── test_embedding_api.py  # 嵌入 API 连通测试
├── docs/                      # 文档
│   ├── quickstart.md          # 快速入门
│   ├── runbook.md             # 运行手册
│   ├── embedding-api-setup.txt # 嵌入 API 配置指南
│   ├── development-notes/     # 开发笔记
│   └── experiment-design/     # 实验设计文档
├── images/                    # 项目图片
├── docker-compose.yml
├── LICENSE
└── .gitignore
```

## API 概览

### 管理端 API

| 模块 | 路径前缀 | 说明 |
|------|---------|------|
| 认证 | `/api/v1/auth` | 注册、登录、Token |
| 组织管理 | `/api/v1/organizations` | 组织 CRUD |
| 服务管理 | `/api/v1/services` | 服务注册与管理 |
| Agent 管理 | `/api/v1/agents` | 代理 CRUD 与监控 |
| 服务发现 | `/api/v1/discovery` | 语义搜索、URI 解析、分类 |
| 服务代理 | `/api/v1/proxy` | 请求转发与用量追踪 |
| 评价信任 | `/api/v1/reviews` | 服务评价与信任摘要 |
| 计费管理 | `/api/v1/billing` | 账单与使用记录 |
| 公共 API | `/api/v1/public` | 无需认证的公共接口 |

### 客户端 API

| 模块 | 路径前缀 | 说明 |
|------|---------|------|
| 客户端认证 | `/api/v1/client/auth` | 客户端注册登录 |
| 客户端发现 | `/api/v1/client/discovery` | 客户端服务搜索 |
| 客户端服务 | `/api/v1/client/services` | 服务调用与解析 |
| 客户端账户 | `/api/v1/client/account` | 余额、充值、使用历史 |
| 客户端计费 | `/api/v1/client/billing` | 账单与统计 |
| 客户端仪表盘 | `/api/v1/client/dashboard` | 概览与趋势 |
| 客户端 API Key | `/api/v1/client/api-keys` | 密钥管理 |
| 客户端日志 | `/api/v1/client/logs` | 调用日志与统计 |
| 客户端资料 | `/api/v1/client/profile` | 个人资料管理 |
| 客户端自有服务 | `/api/v1/client/user-services` | 已使用服务管理 |
| 客户端通知 | `/api/v1/client/notifications` | 通知管理 |

## 核心业务闭环

1. **用户注册/登录** → 获取 JWT Token
2. **创建组织** → 注册服务到 AgentDNS
3. **服务发现** → 自然语言查询 → Milvus 向量检索 → 信任评分排序
4. **服务解析** → `agentdns://org/path` → 获取服务详情与调用端点
5. **服务调用** → 代理转发 → 记录 Usage → 计费扣款
6. **服务评价** → 多维度评价 → 信任分数重算 → 影响后续搜索排序

## 许可证

Apache License 2.0
