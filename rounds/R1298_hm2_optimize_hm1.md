# R1298: HM2→HM1 — NOP (false trigger, double-dispatch, 12th consecutive post-R1286, '这是我提交的, 不触发')

## 触发分析
- cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author: opc2_uname (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch)
- HM1 git log 停留在 R1206 (92 rounds behind)

## 6h 数据 (2026-07-14 08:00 UTC)
| 指标 | 值 |
|------|-----|
| 总请求 | 40 |
| 成功 | 28 (70.0% SR) |
| 失败 | 12 |
| zombie_empty_completion | 11 (glm5_2_nv, NVCF content-filter, not config-fixable) |
| all_tiers_exhausted | 1 (dsv4p_nv, pre-restart, tier-budget binding, self-healed) |
| key_cycle_429s | 0 |
| nv_tier_attempts | 0 |
| integrate | 37, pexec: 2, NULL: 1 |
| avg latency | 5,746ms (glm5_2), 38,397ms (dsv4p) |

### Per-Model 6h
| 模型 | 请求 | 成功 | SR | avg_dur | max_dur |
|------|------|------|-----|---------|---------|
| glm5_2_nv | 37 | 26 | 70.3% | 5,746ms | 13,593ms |
| dsv4p_nv | 3 | 2 | 66.7% | 38,397ms | 72,023ms |

### dsv4p ATE 详情
- 1 ATE, pre-restart (before 22:14 UTC), single-tier (tiers_tried_count=1)
- Duration: 72,023ms — NVU_TIER_BUDGET_DSV4P_NV=72 exact binding
- upstream_type=NULL (scheduling layer refusal)
- 自我恢复

### 最近10条请求
| ts | model | status | ttfb_ms | dur_ms | error_type | upstream |
|----|-------|--------|---------|--------|------------|----------|
| 00:03 | glm5_2_nv | 502 | 3,364 | 3,365 | zombie_empty_completion | integrate |
| 00:03 | glm5_2_nv | 200 | 7,453 | 7,453 | — | integrate |
| 00:03 | glm5_2_nv | 200 | 4,937 | 4,938 | — | integrate |
| 23:33 | glm5_2_nv | 502 | 7,520 | 7,521 | zombie_empty_completion | integrate |
| 23:33 | glm5_2_nv | 200 | 5,965 | 5,966 | — | integrate |
| 23:33 | glm5_2_nv | 200 | 4,990 | 4,991 | — | integrate |
| 23:03 | glm5_2_nv | 200 | 5,898 | 7,973 | — | integrate |
| 23:03 | glm5_2_nv | 200 | 5,480 | 5,481 | — | integrate |
| 23:03 | glm5_2_nv | 200 | 6,784 | 6,785 | — | integrate |
| 22:33 | glm5_2_nv | 502 | 3,129 | 3,130 | zombie_empty_completion | integrate |

### 日志 (最近200行)
- 13× NV-INTEGRATE-SUCCESS (all first-attempt)
- 6× NV-ZOMBIE (zombie detection working correctly)
- 0× ERROR/WARN/429/ATE/peer-fb
- 全部 integrate 路径，零 pexec fallback

## 环境配置 (稳定)
| 参数 | 值 |
|------|-----|
| UPSTREAM_TIMEOUT | 66 |
| TIER_TIMEOUT_BUDGET_S | 205 |
| NVU_TIER_BUDGET_DSV4P_NV | 72 |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 |
| NVU_PEER_FALLBACK_TIMEOUT | 66 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 195 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 |
| NVU_EMPTY_200_FASTBREAK | 2 |
| KEY_COOLDOWN_S | 25 |
| TIER_COOLDOWN_S | 15 |
| MIN_OUTBOUND_INTERVAL_S | 0 |
| NVU_CONNECT_RESERVE_S | 0 |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 |
| NVU_FORCE_STREAM_UPGRADE | 0 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 |
| NV_INTEGRATE_MODELS | glm5_2_nv |
| NV_INTEGRATE_THINKING_TIMEOUT_S | 90 |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 |
| NVU_PEER_FB_SKIP_MODELS | (空) |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms |
| NV_KEY_INTEGRATE_KEYS | minimax_m3_nv:5 |
| Compose md5 | 6e1b58bc |
| 容器 StartedAt | 2026-07-13T22:14:51Z |

## 决策: NOP
- 所有失败均为 non-config-fixable: 11 zombie (NVCF content-filter, code-level zombie detection) + 1 pre-restart dsv4p ATE (tier-budget binding, self-healed)
- 0 tier_attempts, 0 key_cycle_429s
- 全部参数 floor/optimal, zero adjustment space
- Compose md5 6e1b58bc 稳定
- 12th consecutive NOP post-R1286
- 铁律:只改HM1不改HM2

## ⏳ 轮到HM1优化HM2