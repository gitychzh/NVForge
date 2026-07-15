# R1417: HM2→HM1 — NOP (zombie_empty_completion dominant, all params floor/optimal, R1415 settling)

## 1. 数据诊断 (6h window, HM1 nv_gw)

### 整体统计
| 指标 | 值 |
|---|---|
| 总请求 | 25 |
| 成功 (200) | 18 |
| 失败 | 7 |
| 成功率 | 72.0% |
| tier_attempts | 0 |
| host_machine | opc_uname only (HM1) |

### 按模型
| 模型 | upstream | 请求 | 成功 | 失败 | SR | avg_ttfb | avg_dur |
|---|---|---|---|---|---|---|---|
| glm5_2_nv | nv_integrate | 18 | 14 | 4 | 77.8% | 9,493ms | 9,522ms |
| dsv4p_nv | nvcf_pexec | 5 | 3 | 2 | 60.0% | 21,256ms | 21,256ms |
| dsv4p_nv | (ATE) | 2 | 1 | 1 | 50.0% | 177ms | 56,083ms |

### 每小时 SR
| 小时 (UTC) | 请求 | 成功 | 失败 | SR |
|---|---|---|---|---|
| 00:00 | 4 | 4 | 0 | 100.0% |
| 01:00 | 6 | 5 | 1 | 83.3% |
| 02:00 | 6 | 4 | 2 | 66.7% |
| 03:00 | 9 | 5 | 4 | 55.6% |

### 错误类型
| 错误类型 | 数量 | 平均延迟 | 分布 |
|---|---|---|---|
| zombie_empty_completion | 6 | 13,479ms | 4 glm5_2_nv, 2 dsv4p_nv |
| all_tiers_exhausted | 1 | 106,052ms | dsv4p_nv (pre-R1415) |

### 24h zombie_empty_completion 全景
| 总计 | dsv4p_nv | glm5_2_nv |
|---|---|---|
| 32 | 2 | 30 |

## 2. 错误详细分析

### zombie_empty_completion (6, 85.7% of failures)
- dsv4p_nv: 2×, avg input ~210K chars, avg duration 23,624ms
- glm5_2_nv: 4×, avg input ~208K chars, avg duration 8,407ms
- **根因**: NVCF content-filter — finish_reason=stop 但 content_chars=8-12 < 50, input_chars >= 157K
- Gateway zombie detection + error-chunk 正确触发 openclaw fallback
- **判定**: 代码级特性，不可配置修复。NVCF 后端行为。

### all_tiers_exhausted (1, 14.3%)
- dsv4p_nv: 1×, 02:06 UTC, duration 106,052ms, tiers_tried_count=1, fallback_occurred=false
- error_subcategory: all_tiers_failed_in_mapped_tier
- **判定**: Pre-R1415 数据。R1415 已将 NVU_TIER_BUDGET_DSV4P_NV 106→112。容器在 03:25 UTC 重启，此 ATE 发生在重启前。

## 3. 容器状态

| 参数 | 值 |
|---|---|
| 容器 | nv_gw Up (healthy) |
| 重启时间 | 2026-07-15T03:25:06Z (R1415 部署) |
| Compose md5 | 59dc3c54c49324859d1d31e7e422b31b |
| NVU_TIER_BUDGET_DSV4P_NV | 112 (R1415) |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 |
| UPSTREAM_TIMEOUT | 66 |
| TIER_TIMEOUT_BUDGET_S | 205 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 195 |
| NVU_PEER_FALLBACK_TIMEOUT | 66 |
| NVU_PEER_FB_SKIP_MODELS | (空) |
| NVU_EMPTY_200_FASTBREAK | 2 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 |
| NVU_FORCE_STREAM_UPGRADE | 0 |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 |
| TIER_COOLDOWN_S | 15 |
| KEY_COOLDOWN_S | 25 |
| MIN_OUTBOUND_INTERVAL_S | 0 |
| NVU_CONNECT_RESERVE_S | 0 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 |
| FALLBACK_HEALTH_THRESHOLD | 0.05 |

## 4. 日志信号 (post-restart, 03:25 UTC+)

```
[11:33:20.2] [NV-REQ] glm5_2_nv→glm5_2_nv tier_chain=['glm5_2_nv'] (no fallback, 3model)
[11:33:23.9] [NV-INTEGRATE-SUCCESS] glm5_2_nv k1 succeeded on first attempt
[11:33:37.7] [NV-INTEGRATE-SUCCESS] glm5_2_nv k2 succeeded on first attempt
[11:33:40.5] [NV-ZOMBIE-EMPTY] (glm5_2_nv) zombie empty completion: content_chars=12 < 50, input_chars=209884
[11:33:40.5] [NV-ZOMBIE-ERROR-CHUNK] (glm5_2_nv) sent finish_reason=timeout error SSE chunk
[11:36:06.1] [NV-SUCCESS] dsv4p_nv k3 succeeded on first attempt
[11:36:22.6] [NV-SUCCESS] dsv4p_nv k4 succeeded on first attempt
[11:36:36.1] [NV-SUCCESS] dsv4p_nv k5 succeeded on first attempt
[11:36:49.1] [NV-ZOMBIE-EMPTY] (dsv4p_nv) zombie empty completion: content_chars=8 < 50, input_chars=210357
[11:36:49.1] [NV-ZOMBIE-ERROR-CHUNK] (dsv4p_nv) sent finish_reason=timeout error SSE chunk
```

- 4 post-restart NV-SUCCESS (first-attempt): 3 dsv4p_nv, 1 glm5_2_nv
- 2 post-restart zombie: 1 glm5_2_nv, 1 dsv4p_nv — NVCF content-filter
- 0 ATE, 0 tier_attempts, 0 key cycling
- (no fallback, 3model) — expected (R832 FALLBACK_GRAPH={})
- Post-restart SR: 5/7 = 71.4% (2 zombies from NVCF, not config-fixable)

## 5. 决策

**NOP — 零参数变更。**

- 6/7 failures (85.7%) = zombie_empty_completion: NVCF content-filter，代码级特性，不可配置修复
- 1/7 failure = ATE dsv4p_nv: pre-R1415 数据，R1415 已增加 NVU_TIER_BUDGET_DSV4P_NV 106→112
- 0 tier_attempts: 无 key cycling 问题
- 0 SSLEOF: 无 proxy 连接问题
- 所有参数 floor/optimal:
  - 3 FASTBREAK params at optimal (pexec=1, integrate=1, empty_200=2)
  - 3 TIER_BUDGET params at optimal (dsv4p=112, glm5_2=96, minimax=100)
  - 所有 floor params at 0 (MIN_OUTBOUND, CONNECT_RESERVE, INTEGRATE_KEY_COOLDOWN)
  - TIER_COOLDOWN_S=15, KEY_COOLDOWN_S=25 稳定
- Post-restart 数据积累中，R1415 变更生效正常
- 等待更多 post-restart 数据确认 BUDGET_DSV4P_NV=112 是否充分

**铁律: 只改HM1不改HM2**
## ⏳ 轮到HM1优化HM2
