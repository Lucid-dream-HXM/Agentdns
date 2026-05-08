# B1 冷启动实验结果冻结包

## 冻结时间
2026-04-20

## 实验条件（重要口径说明）
- **非完全冷启动**，而是：**主观信任冷启动 + 客观使用历史保留**
  - reviews/trust_stats：已清零（4706条reviews，22条trust_stats）
  - usage_records：保留（部分服务仍有历史调用记录）
- 因此 trust_score 仍受客观分驱动，不完全是 0

## 已验证结论
1. trust 机制本身是活的（单条fail review可拉低trust ~2分，初始信任100→68）
2. trust 真实参与 discovery 排序（4个类目中3个出现排序差异）
3. 标准市场 trust_delta≈0 是"高信任饱和"实验现象，非实现bug
4. 冷启动条件：失败review后trust即时大幅下降（100→68），之后进入慢衰减

## 包含内容
- `cold_start_warmup/` — 信任反馈闭环组+基础解析组 各4任务运行结果

## 核心数据
- 信任反馈闭环组 trust_delta: mean=-0.08（连续失败review慢衰减）
- 基础解析组 trust_delta: mean=-0.08（无trust反馈，持续慢衰减）
- 3/4类目(tran/summary/extraction)出现trust导致的排序变化

## 下一步
进入 B2：诱骗增强市场 3组×24任务试探包
