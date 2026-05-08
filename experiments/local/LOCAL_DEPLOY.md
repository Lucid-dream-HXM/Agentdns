# 本地部署与接口实验说明

## 目标
本批代码用于直接部署在本地，通过 AgentDNS 本地 HTTP 接口执行发现、调用与评价闭环。

## 使用前提
1. 本地 AgentDNS 后端已启动
2. 本地数据库与实验市场已 seed 完成
3. 本地 mock service 已启动
4. `configs/local_runtime.yaml` 中的 `base_url` 与 `api_key` 已更新为本机可用值

## 建议顺序
1. 先执行 `experiments/local/check_local_stack.py`
2. 再执行 `experiments/runners/local_http_runner.py`
3. 最后执行 `experiments/runners/local_formal_http_suite.py`

## 重要说明
- 本批代码优先调用现有本地 API 接口，不主动修改主项目主链路
- 若后续需要更精确的系统内消融，可能仍需在主项目中增加实验模式开关或调试字段
