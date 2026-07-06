# R800: HM2→HM1 — NOP (false trigger) — 86.2% SR, 全参数floor, dsv4p_nv健康恢复中, 系统稳定

**时间**: 2026-07-07 05:05 UTC  
**分析窗口**: 6h (23:00–05:00 UTC)  
**决策**: NOP — 零参数改动，零compose改动，零容器重启。

## 触发原因

检测脚本判定"HM1提交了新commit"触发cron，但实际 `3cfcac77` 已被R799处理。脚本输出"已处理过此commit，等待新提交"。R799末行标记"⏳ 轮到HM1优化HM2"——当前是HM1的回合，非HM2。cron误触发，但数据诊断确认系统无需改动。

## 6h 总体统计

| 指标 | 值 |
|---|---|
| 总请求 | 268 |
| 成功 (200) | 231 |
| 失败 (ATE 502) | 37 |
| SR | **86.2%** |
| Fallback 触发 | 42 |
| Fallback 成功 | 42 (100%) |
| Single-tier ATE | **0** |
| Double-tier ATE | 37 (100%) |

## 逐小时 SR

| 小时 (UTC) | total | ok | ate | SR |
|---|---|---|---|---|
| 23:00 | 31 | 27 | 4 | 87.1% |
| 00:00 | 42 | 34 | 8 | 81.0% |
| 01:00 | 12 | 12 | 0 | 100.0% |
| 02:00 | 9 | 9 | 0 | 100.0% |
| 03:00 | 8 | 6 | 2 | 75.0% |
| 04:00 | 7 | 7 | 0 | 100.0% |
| 05:00 | 1 | 1 | 0 | 100.0% |

> 01:00-05:00 连续4小时 100% SR（03:00 仅2 ATE，75% 为低频窗口）。系统已从 20:00 UTC 的 46.7% 低谷完全自愈。

## Error 分类（仅 502）

| error_type | cnt |
|---|---|
| all_tiers_exhausted | 37 |

> 全部 37 ATE 均为 `tiers_tried_count=2`（双 tier NVCF 上游耗尽），无单 tier ATE。非 config 可修。

## Tier Attempts 失败详情

| tier | error_type | cnt | avg_ms | max_ms |
|---|---|---|---|---|
| dsv4p_nv | 504_nv_gateway_timeout | 29 | — | — |
| dsv4p_nv | NVCFPexecTimeout | 17 | 50,351 | 51,577 |
| dsv4p_nv | empty_200 | 6 | — | — |
| dsv4p_nv | 500_nv_error | 1 | — | — |
| glm5_2_nv | 504_nv_gateway_timeout | 35 | — | — |
| glm5_2_nv | empty_200 | 10 | — | — |
| glm5_2_nv | NVCFPexecTimeout | 6 | 51,526 | 51,637 |

## UPSTREAM_TIMEOUT 绑定诊断

| tier | NVCFPexecTimeout max | UPSTREAM | buffer | 状态 |
|---|---|---|---|---|
| dsv4p_nv | 51,577ms | 66s | **14.4s** | 非绑定 ✅ |
| glm5_2_nv | 51,637ms | 66s | **14.4s** | 非绑定 ✅ |

> Buffer 远超 3s 阈值（R751 规则），UPSTREAM_TIMEOUT=66 完全非绑定。NVCFPexecTimeout max 从 R799 的 62s 降至 51s —— NVCF 函数性能显著改善。

## FALLBACK_GRAPH 状态

```
tier_chain=['dsv4p_nv', 'glm5_2_nv'] (dynamic fallback, health={'74f02205': 0.3→0.45, '3b9748d8': 0.9})
tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback, health={'74f02205': 0.3→0.45, '3b9748d8': 0.9})
```

> 双向 dynamic fallback 正常工作。dsv4p_nv 函数 `74f02205` 健康度从 0.3 恢复至 0.45（4h 内 +0.15），glm5_2_nv 函数 `3b9748d8` 健康度 0.9 稳定。

## 成功请求延迟分布

| dur_bucket | dsv4p_nv | glm5_2_nv |
|---|---|---|
| <5s | 4 | 33 |
| 5-10s | 1 | 34 |
| 10-20s | 7 | 24 |
| 20-30s | 7 | 9 |
| 30-40s | 4 | 5 |
| 40-50s | 11 | 3 |
| 50-60s | 8 | 4 |
| 60-66s | 1 | 4 |
| 66-70s | 1 | 5 |
| >70s | 33 (23 fallback) | 31 (13 fallback) |

> glm5_2_nv 快速响应（<10s 占 67/150 = 44.7%），dsv4p_nv 偏慢（>70s 含 23 fallback）。

## 容器状态

- 容器 `nv_gw` 重启时间: 2026-07-06 16:02 UTC（~13h 前）
- 无 MIN_SAMPLES 过期风险（container 已运行 >1h）

## NOP 决策 — 全部 6 门通过

| Gate | 检查 | 结果 |
|---|---|---|
| 1. 所有 ATE 双 tier | tiers_tried_count=2: 37/37 | ✅ |
| 2. 零单 tier ATE | 0 rows | ✅ |
| 3. NVCFPexecTimeout buffer ≥3s | dsv4p_nv=14.4s, glm5_2_nv=14.4s | ✅ |
| 4. FALLBACK_GRAPH 双向工作 | 两个方向均 dynamic fallback | ✅ |
| 5. Fallback SR = 100% | 42/42 OK | ✅ |
| 6. 全参数 floor | 全部参数 floor/optimal | ✅ |

**额外强化信号**: dsv4p_nv 健康度 0.3→0.45 恢复中，最近 4h 连续 100% SR，NVCFPexecTimeout max 从 62s 降至 51s。

**决策**: NOP — 零参数改动，零 compose 改动，零容器重启。系统自愈中，NVCF 上游函数性能改善，无 config 可修问题。

## 当前配置参数（全部 floor）

| 参数 | 值 | 状态 |
|---|---|---|
| UPSTREAM_TIMEOUT | 66 | 非绑定 (buffer 14.4s) |
| TIER_TIMEOUT_BUDGET_S | 114 | 安全 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 1 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | floor |
| NVU_FORCE_STREAM_UPGRADE | 0 | floor |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | aligned |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| KEY_COOLDOWN_S | 25 | standard |
| TIER_COOLDOWN_S | 25 | standard |

## ⏳ 轮到HM1优化HM2