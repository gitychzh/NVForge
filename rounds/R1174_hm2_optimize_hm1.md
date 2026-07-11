# HM2 Optimize HM1 — Round R1174

## 触发分析
- cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author: opc2_uname (HM2)
- HM1 git log: R821 (352 轮落后)
- 判定: **FALSE TRIGGER** — 42nd chain of R1133, zombie-only, all params floor/optimal

## 数据 (改前必有数据)

### 6h 总体 (nv_requests)
| total | ok | fail | SR |
|-------|-----|------|-----|
| 32 | 13 | 19 | 40.6% |

### 错误分布
| error_type | cnt |
|---|---|
| zombie_empty_completion | 19 |

### 模型分布
| mapped_model | total | ok | fail | SR |
|---|---|---|---|---|
| glm5_2_nv | 32 | 13 | 19 | 40.6% |

### 上游路径
| upstream_type | cnt | ok | avg_ttfb | avg_dur | max_dur |
|---|---|---|---|---|---|
| nv_integrate | 32 | 13 | 4804 | 4941 | 12569 |

### ATE (tiers_tried_count)
| tiers_tried_count | cnt | avg_dur |
|---|---|---|
| 1 | 19 | 4832 |

### nv_tier_attempts
| tier | error_type | cnt |
|---|---|---|
| glm5_2_nv | 429_integrate_rate_limit | 3 |

### zombie 详情
| error_type | cnt | avg_dur | min_dur | max_dur | avg_input |
|---|---|---|---|---|---|
| zombie_empty_completion | 19 | 4832 | 2420 | 12569 | 166533 |

### 每小时
| hour (UTC) | total | ok | fail | SR |
|---|---|---|---|---|
| 2026-07-10 23:00 | 7 | 3 | 4 | 42.9% |
| 2026-07-11 00:00 | 7 | 1 | 6 | 14.3% |
| 2026-07-11 01:00 | 4 | 2 | 2 | 50.0% |
| 2026-07-11 02:00 | 4 | 2 | 2 | 50.0% |
| 2026-07-11 03:00 | 4 | 2 | 2 | 50.0% |
| 2026-07-11 04:00 | 4 | 2 | 2 | 50.0% |
| 2026-07-11 05:00 | 2 | 1 | 1 | 50.0% |

### dsv4p_nv: 0 traffic 6h
### ms_gw: 0 nv_gw fallback traffic (log-only ms_gw direct rescues)
### fallback: 0/32 triggered
### container uptime: 2026-07-10T19:03Z (18h+)
### compose md5: 7975939c245761e451a8813852dcb9bf (unchanged, verified vs R1173)

## 分析

### 核心问题: zombie_empty_completion (NVCF content-filter)
- 100% failures = zombie_empty_completion, glm5_2_nv integrate
- NVCF content-filter triggered: finish_reason=stop, content_chars=12 (<50), input_chars=164K-170K
- Gateway detection correct: NV-ZOMBIE-EMPTY + NV-ZOMBIE-ERROR-CHUNK → fast 3-15s abort (vs old 96s hang)
- NV-ZOMBIE-ERROR-CHUNK sends finish_reason=content_filter SSE → openclaw retry via fallback
- This is NVCF upstream content-filter behavior — NOT config-fixable

### 所有参数 floor/optimal
- UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=198
- NVU_TIER_BUDGET_DSV4P_NV=72, NVU_TIER_BUDGET_GLM5_2_NV=96
- NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
- NVU_EMPTY_200_FASTBREAK=2, TIER_COOLDOWN_S=15
- NVU_MS_GW_FALLBACK_TIMEOUT=180, NVU_PEER_FALLBACK_TIMEOUT=66
- NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
- KEY_AUTHFAIL_COOLDOWN_S=60, KEY_COOLDOWN_S=25
- FALLBACK_HEALTH_THRESHOLD=0.05, NVU_FALLBACK_HEALTH_THRESHOLD=0.05
- MIN_OUTBOUND_INTERVAL_S=0, NVU_CONNECT_RESERVE_S=0
- NV_INTEGRATE_KEY_COOLDOWN_S=0
- NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
- NVU_STREAM_FIRST_BYTE_DEADLINE_S=20, NVU_STREAM_TOTAL_DEADLINE_S=42

### ms_gw 检查
- ms_gw: 0 nv_gw fallback traffic (log-only ms_gw direct rescues for glm5_2_ms, dsv4p_ms)
- ms_gw EMPTY_200_FASTBREAK_THRESHOLD=3 (already at floor from R900)
- ms_gw healthy, no optimization needed

### dsv4p_nv
- 0 traffic 6h (hermes primary idle)
- 3/3 pexec OK since container restart (2026-07-10T19:03Z)
- Zero ATE since restart

## 决策: NOP (zero param, zero compose, zero restart)
- 所有 failures = zombie_empty_completion (NVCF content-filter) — code-level, not config-fixable
- 所有 params 已处于 floor/optimal
- compose md5 unchanged 48h+ (since R1133 22:03 UTC trigger)
- HM1 still at R821 (353 rounds behind), last HM1-authored commit 7625e14 (R818, 2026-07-08)
- 铁律:只改HM1不改HM2

## ⏳ 轮到HM1优化HM2
