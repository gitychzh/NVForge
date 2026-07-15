# HM2 Optimize HM1 — Round R1416

> **触发**: 2026-07-15 11:30 UTC | **作者**: opc2_uname (HM2)
> **类型**: NOP (false trigger, double-dispatch, 574th chain of R1133)
> **铁律**: 只改HM1不改HM2 | 改前必有数据 | 改后必有验证

## 1. 触发分析

cron 脚本输出:
```
[2026-07-15 11:30:56] 这是我提交的, 不触发
```

- 最新 commit: `1cf5ad9` — R1415 (opc2_uname, HM2)
- HM1 本地 git log: R1206 (210 轮落后)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch)

## 2. 数据总览 (6h窗口)

| 指标 | 值 |
|------|-----|
| 总请求 | 20 |
| 成功 (200) | 15 |
| 失败 | 5 |
| 成功率 | 75.0% |
| tier_attempts | 0 |
| ms_gw 6h | 6 total / 5 ok |

### 按模型

| 模型 | 请求 | 成功 | 失败 | SR | 平均延迟 |
|------|------|------|------|-----|---------|
| glm5_2_nv | 16 | 13 | 3 | 81.3% | 9,473ms |
| dsv4p_nv | 4 | 2 | 2 | 50.0% | 43,950ms |

### 错误类型

| 错误类型 | 数量 | 模型 |
|----------|------|------|
| zombie_empty_completion | 4 | 1 dsv4p_nv, 3 glm5_2_nv |
| all_tiers_exhausted | 1 | dsv4p_nv |

### 每小时 SR

| 小时 (UTC) | 请求 | 成功 | 失败 | SR |
|------------|------|------|------|-----|
| 00:00 | 4 | 4 | 0 | 100.0% |
| 01:00 | 6 | 5 | 1 | 83.3% |
| 02:00 | 6 | 4 | 2 | 66.7% |
| 03:00 | 4 | 2 | 2 | 50.0% |

## 3. 错误详细分析

### zombie_empty_completion (4)
- dsv4p_nv: 1×, avg input 209,978 chars, duration 34,426ms
- glm5_2_nv: 3×, avg input 208,682 chars, duration 7,881ms
- **根因**: NVCF content-filter (R1405 fix active: finish_reason=timeout, gateway detection+error-chunk correct)
- **判定**: 代码级特性，不可配置修复

### all_tiers_exhausted (1)
- dsv4p_nv: 1×, duration 106,052ms, tiers_tried_count=1, fallback_occurred=false
- tiers_tried_count=1: dsv4p_nv exhausted 5 keys without fallback
- FALLBACK_GRAPH={} (expected, R832 design), ms_gw fallback available
- BUDGET_DSV4P_NV=112 (R1415 applied: 106→112), BUDGET=205
- **判定**: Pre-R1415 数据 (容器重启前), R1415 已增加 BUDGET_DSV4P_NV 到 112

## 4. 容器状态

| 参数 | 值 |
|------|-----|
| 容器 | nv_gw Up 8 minutes (healthy) |
| 重启时间 | 2026-07-15T03:25:06Z |
| Compose md5 | 59dc3c54c49324859d1d31e7e422b31b |
| NVU_TIER_BUDGET_DSV4P_NV | 112 (R1415) |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 |
| UPSTREAM_TIMEOUT | 66 |
| TIER_TIMEOUT_BUDGET_S | 205 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 195 |
| NVU_PEER_FALLBACK_TIMEOUT | 66 |
| NVU_EMPTY_200_FASTBREAK | 2 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 |
| NVU_FORCE_STREAM_UPGRADE | 0 |

## 5. 日志信号

```
[11:33:20.2] [NV-REQ] mapped_model=glm5_2_nv tier_chain=['glm5_2_nv'] (no fallback, 3model)
[11:33:30.5] [NV-REQ] mapped_model=glm5_2_nv tier_chain=['glm5_2_nv'] (no fallback, 3model)
[11:33:40.5] [NV-ZOMBIE-EMPTY] (glm5_2_nv) passthrough zombie empty completion
[11:33:40.5] [NV-ZOMBIE-ERROR-CHUNK] (glm5_2_nv) sent finish_reason=timeout error SSE chunk
```

- 2 post-restart glm5_2_nv 请求 (03:33 UTC)
- 1 zombie detected + error-chunk sent (R1405 fix active)
- (no fallback, 3model) — expected (R832 FALLBACK_GRAPH={})

## 6. 决策

**NOP — 零参数变更。**

- 4 zombie_empty_completion: NVCF content-filter，代码级特性，不可配置修复
- 1 ATE dsv4p_nv: pre-R1415 数据，R1415 已增加 NVU_TIER_BUDGET_DSV4P_NV 106→112
- 0 tier_attempts: 无 key cycling 问题
- 所有参数 floor/optimal
- 容器已重启，R1415 变更已生效，等待 post-restart 数据积累
- 假触发: HM2 自提交，cron 误派遣

**铁律: 只改HM1不改HM2**

## ⏳ 轮到HM1优化HM2
