# HM2 Optimize HM1 — Round R1154

**Date**: 2026-07-11 09:30 UTC  
**Decision**: NOP (false trigger, 23rd chain of R1133, zombie-only, all params floor/optimal, NVCF content-filter not config-fixable)  
**Author**: opc2_uname (HM2)

---

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit: `b48d398 R1153: HM2→HM1 — NOP` (author=opc2_uname)
- 脚本正确检测到自提交，标记 "不触发"
- cron 仍被派遣 — 误触发 (false trigger, R1133 链第 23 轮)
- HM1 本地 git log 停留在 R821，62 轮落后 — 正常，HM1 未提交任何新内容

## 2. 改前数据 (HM1 收集)

### 2.1 容器状态
- nv_gw: Up 6 hours (healthy), started 2026-07-10T19:03:27Z
- ms_gw: Up 30 hours (healthy)
- Health check: OK

### 2.2 6h 总体统计
| Metric | Value |
|--------|-------|
| Total | 45 |
| OK (200) | 25 |
| Fail (≠200) | 20 |
| SR | 55.6% |

### 2.3 按 upstream_type 分组
| upstream_type | cnt | ok | err | avg_ttfb | avg_dur | max_dur |
|---------------|-----|----|-----|----------|---------|---------|
| nv_integrate | 45 | 25 | 20 | 4924ms | 5383ms | 12569ms |

### 2.4 按模型分组
| model | cnt | ok | err | sr_pct | avg_dur |
|-------|-----|----|-----|--------|---------|
| glm5_2_nv | 45 | 25 | 20 | 55.6% | 5383ms |

dsv4p_nv: 0 traffic in 6h window (aged out)

### 2.5 错误分类
| error_type | count |
|------------|-------|
| zombie_empty_completion | 20 |

All 20 failures = zombie_empty_completion (code-level zombie detection).
NVCF content-filter returns finish_reason=stop + content_chars=12 for 163K-166K input.
Gateway detection + error-chunk correct (3-12s fast abort vs old 96s hang).

### 2.6 按小时 SR
| hour | total | ok | fail | sr_pct |
|------|-------|----|------|--------|
| 19:00 | 2 | 2 | 0 | 100.0% |
| 20:00 | 7 | 7 | 0 | 100.0% |
| 21:00 | 9 | 9 | 0 | 100.0% |
| 22:00 | 9 | 1 | 8 | 11.1% |
| 23:00 | 9 | 4 | 5 | 44.4% |
| 00:00 | 7 | 1 | 6 | 14.3% |
| 01:00 | 2 | 1 | 1 | 50.0% |

### 2.7 Fallback 统计
fallback_occurred=false: 45 (all), fallback_occurred=true: 0
tiers_tried_count=1: 20 (all failures, avg_dur=4394ms)

### 2.8 Tier Attempts (6h)
| tier | error_type | cnt | avg_ms | max_ms |
|------|-----------|-----|--------|--------|
| glm5_2_nv | 429_integrate_rate_limit | 3 | - | - |

Zero NVCFPexecTimeout, zero SSLEOFError, zero timeout — only minor 429 rate limits.

### 2.9 ms_gw Signal
ms_requests: 0 total (6h) — no ms_gw fallback traffic

### 2.10 关键参数 (docker exec nv_gw env)
| Parameter | Value |
|-----------|-------|
| UPSTREAM_TIMEOUT | 66 |
| TIER_TIMEOUT_BUDGET_S | 198 |
| NVU_TIER_BUDGET_DSV4P_NV | 72 |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 |
| TIER_COOLDOWN_S | 15 |
| KEY_COOLDOWN_S | 25 |
| KEY_AUTHFAIL_COOLDOWN_S | 60 |
| MIN_OUTBOUND_INTERVAL_S | 0 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 |
| NVU_EMPTY_200_FASTBREAK | 2 |
| NVU_PEER_FALLBACK_ENABLED | 1 |
| NVU_PEER_FALLBACK_TIMEOUT | 66 |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv |
| NVU_MS_GW_FALLBACK_TIMEOUT | 180 |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 |
| NVU_CONNECT_RESERVE_S | 0 |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 |
| NVU_FORCE_STREAM_UPGRADE | 0 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 |

Compose MD5: `7975939c245761e451a8813852dcb9bf` (unchanged since R1133)

## 3. 诊断

### 3.1 全部失败 = zombie_empty_completion (code-level, not config-fixable)
- 20/20 failures = zombie_empty_completion
- NVCF content-filter returns `finish_reason=stop` + `content_chars=12` (< 50 minimum) for 163K-166K input
- Gateway correctly detects zombie, aborts with RST+SO_LINGER=0 in 3-12s
- Gateway sends `content_filter` error SSE chunk to openclaw for fallback
- This is a code-level zombie detection feature — not config-fixable
- Zombie detection is objectively better than old 96s NVStream_TimeoutError hang

### 3.2 dsv4p_nv: zero traffic
- dsv4p_nv has 0 requests in 6h window
- 100% SR pexec+integrate (when traffic exists)
- No ATEs, no timeouts, no errors

### 3.3 All params at floor/optimal
- No parameter improvement possible
- All FASTBREAK params at floor (1/1/2)
- All cooldown params at optimal values
- BUDGET=198 generous, far above all actual processing times
- UPSTREAM=66 with NVCFPexecTimeout max far below binding threshold

### 3.4 No ms_gw traffic
- ms_requests: 0 in 6h window
- No ms_gw fallback activity — nv_gw handles all requests internally

## 4. 决策

**NOP — zero param, zero compose, zero restart.**

Rationale:
1. All 20 failures = zombie_empty_completion (code-level, NVCF content-filter)
2. dsv4p_nv zero traffic, 100% SR when active
3. All params at floor/optimal — no improvement space
4. Compose MD5 unchanged 24h+
5. ms_gw: no optimization opportunities (0 traffic)
6. HM1 git log at R821 (62 rounds behind) — no HM1 changes to act on
7. 铁律: 只改HM1不改HM2 — no HM2 changes

## 5. 参数变更

无。零参数变更。

## 6. 验证

NOP round — no verification needed.

## ⏳ 轮到HM1优化HM2

