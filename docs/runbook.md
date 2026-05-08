# AgentDNS 实验运行手册

## 1. 标准启动方式

### Backend
```bash
cd agentdns-backend && bash start_backend.sh
```

### Mock Services
```bash
cd experiments/mock_services && bash start_mock_services.sh
```

## 2. 标准健康检查

### Backend
```bash
bash agentdns-backend/check_backend.sh
```

### Mock Services
```bash
bash experiments/mock_services/check_mock_services.sh
```

## 3. 标准实验入口

### 冷启动实验
```bash
python experiments/scripts/run_v1_v3_coldstart.py
```

### 预热后实验
```bash
python experiments/scripts/run_v1_v3_after_warmup.py
```

## 4. 当前依赖前提

- **PostgreSQL**: 用户 `agentdns`，密码 `agentdns123`，库 `agentdns`
- **.env 路径**: `agentdns-backend/.env`
- **Mock Service 默认端口**: `9001`
- **Backend 默认端口**: `8000`
- **数据库容器**: `postgres-agentdns` (Docker)

## 5. 输出文件位置

- 冷启动结果: `experiments/outputs/runs/v1_vs_v3_coldstart_summary.csv`
- 预热后结果: `experiments/outputs/runs/v1_vs_v3_summary.csv`
- 图表: `experiments/outputs/figures/v1_v3_*.png`
- Oracle 日志: `experiments/outputs/oracle/oracle_calls.jsonl`