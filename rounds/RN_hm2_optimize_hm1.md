## R781 (HM2→HM1) — NOP — 98.1% SR双函数健康持续改善，零参数变更

### 诊断数据

| 指标 | 值 |
|------|-----|
| 6h总请求 | 312 |
| 6h OK | 306 (98.1%) |
| 6h Fail | 6 (1.9%) |

### 按模型

| 模型 | 请求数 | OK | SR | avg TTFB | avg Dur |
|------|--------|----|----|-----------|----------|
| dsv4p_nv | 169 | 163 | 96.4% | 52,142ms | 56,830ms |
| glm5_2_nv | 138 | 138 | 100.0% | 27,415ms | 27,488ms |
| kimi_nv | 5 | 5 | 100.0% | 5,299ms | 5,352ms |

### NVCFPexecTimeout（非绑定诊断）

| Tier | max(ms) | UPSTREAM | gap | 判定 |
|------|---------|----------|-----|------|
| dsv4p_nv | 60,823 | 66 | 5.2s | 非绑定 |
| glm5_2_nv | 62,389 | 66 | 3.6s | 非绑定（但距≥3s阈值仅0.6s） |

### 函数健康度（日志）

- dsv4p_nv: 0.545→0.688（持续改善）
- glm5_2_nv: 0.80→0.95（强且持续改善）

### 逐小时 SR

| 小时 (UTC) | 请求 | OK | SR |
|-----------|------|-----|------|
| 20:00 | 9 | 8 | 88.9% |
| 21:00 | 34 | 32 | 94.1% |
| 22:00 | 42 | 41 | 97.6% |
| 23:00 | 42 | 41 | 97.6% |
| 00:00 | 34 | 33 | 97.1% |
| 01:00-10:00 | 各小时 | 全部 | **100%** |

最近连续10小时100% SR。

### ATE 分析

6个ATE全部为 `all_tiers_exhausted`，`tiers_tried_count=2`，`fallback_actually_attempted=false`。
avg 184s, max 228s ≈ BUDGET=114 × 2。NVCF 上游双tier真实耗尽，非配置可修复。

### Fallback 成功率

- Fallback成功: 56次 (avg 98,906ms, max 226,133ms)
- 直接成功: 250次 (avg 27,124ms)
- 日志确认双向fallback正常工作: `tier_chain=['glm5_2_nv', 'dsv4p_nv']` 和 `['dsv4p_nv', 'glm5_2_nv']` 均存在

### 429分布

dsv4p_nv: k0=14, k1=7, k2=7, k3=7, k4=10 — 轻度不均匀，但函数健康度1.0，SR 96.4%，不构成FASTBREAK增加触发条件。

### 当前配置

- UPSTREAM_TIMEOUT=66
- TIER_TIMEOUT_BUDGET_S=114
- NVU_PEXEC_TIMEOUT_FASTBREAK=1
- NVU_EMPTY_200_FASTBREAK=1
- FALLBACK_HEALTH_THRESHOLD=0.10
- MIN_OUTBOUND_INTERVAL_S=0
- KEY_COOLDOWN_S=25
- TIER_COOLDOWN_S=25
- NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
- NV_INTEGRATE_KEY_COOLDOWN_S=0

### 决策：NOP（零变更）

**不调整任何参数。** 理由：
1. SR 98.1%，连续10小时100% — 系统已稳定
2. 双函数健康度均持续改善，呈上升趋势
3. NVCFPexecTimeout 双函数均非绑定（dsv4p_nv +5.2s, glm5_2_nv +3.6s），UPSTREAM减少不安全（glm5_2_nv仅0.6s冗余）
4. FASTBREAK=1 已最优：429分布轻度不均匀但不足以触发Path B，函数健康度>0.5不触发Path A
5. 6个ATE均为NVCF上游双tier真实耗尽，不可配置修复
6. 双向fallback 100%正常

### 容器信息

- 启动时间: 2026-07-05 23:47:10 UTC（已运行~10.7h）
- MIN_SAMPLES 已过期 → tier_chain 基于真实健康度，当前双tier均健康

## ⏳ 轮到HM1优化HM2