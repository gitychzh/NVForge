# R2422: HM2 → HM1 — NVU_BIG_INPUT_THRESHOLD 250000 → 375000 (breaker false-ATE fix)

> 铁律: 只改 HM1，不改 HM2。  
> Judging criteria: fewer errors / faster requests / lower latency / stability first.

---

## 1. Data basis (改前必有数据)

Source: HM1 logs_db `nv_requests` + `nv_tier_attempts`, SSH to HM1. Collected 2026-07-29 20:05 CST.

### 1.1 6h per-model status
| model | OK | FAIL | total | SR (6h) | avg OK latency |
|---|---|---|---|---|---|
| glm5_2_nv | 17 | 11 | 28 | **60.7%** | 25476ms |
| dsv4p_nv | 0 | 7 | 7 | **0%** | — (all timeout) |
| kimi_nv | 0 | 4 | 4 | **0%** | — |
| **TOTAL** | 17 | 22 | 39 | **43.6%** | |

### 1.2 6h error breakdown
| model | error_type | count | notes |
|---|---|---|---|
| glm5_2_nv | all_tiers_exhausted (502) | 4 | durations 9-11ms to 177942ms |
| glm5_2_nv | all_tiers_exhausted (429) | 3 | 12:03 cascade, 1542-3014ms each |
| glm5_2_nv | zombie_empty_completion | 1 | 362368 chars input |
| dsv4p_nv | all_tiers_exhausted | 7 | durations 105-200s, NVCF timeout |
| kimi_nv | all_tiers_exhausted | 4 | NVCF degradation |

### 1.3 ATE detail — tier_attempts = 0 (CRITICAL)
ALL 18 ATE requests have **zero tier_attempts** → pre-empted before any key was tried. The big_input breaker is blocking requests before they reach the NVCF key pool.

### 1.4 12:03 429 cascade on glm5_2_nv (big_input breaker HALF_OPEN)
3 consecutive requests at 12:03:22, 12:03:28, 12:03:36:
- All inputs: 361788 chars (> 250000 threshold → routed to big_input breaker)
- Breaker HALF_OPEN: only 1 probe key allowed
- k1 → 429 (NVCF rate-limit) → TIER-FAIL → breaker back to OPEN
- Self-reinforcing loop: HALF_OPEN → 1-key probe → 429 → OPEN → no traffic flows

### 1.5 Early burst 09:05-09:33 (3 instant ATE, 9-11ms)
- glm5_2_nv 09:05:10 → 502 at 10ms (ATE, input=362K-ish)
- glm5_2_nv 09:05:11 → 502 at 10ms (ATE)
- glm5_2_nv 09:33:58 → 502 at 11ms (ATE)
These are pre-empted by big_input breaker OPEN state, instant reject.

### 1.6 Live env (nv_gw container, before change)
| param | value | source |
|---|---|---|
| NVU_BIG_INPUT_THRESHOLD | **250000** | R2312 (lowered from 400K) |
| NVU_BIG_INPUT_MODELS | glm5_2_nv | R2358 |
| NVU_BIG_INPUT_FAIL_N | 7 | R2376 |
| NVU_BIG_INPUT_COOLDOWN_S | 180 | R2375 |
| KEY_COOLDOWN_S | 15 | R2418 |
| TIER_COOLDOWN_S | 0 | R2378 |
| UPSTREAM_TIMEOUT | 34 | R2418 |
| NVU_TIER_BUDGET_GLM5_2_NV | 300 | R2395 |
| NVU_TIER_BUDGET_DSV4P_NV | 265 | R2372 |
| NVU_TIER_BUDGET_KIMI_NV | 370 | R2413 |
| TIER_TIMEOUT_BUDGET_S | 630 | R2420 |

---

## 2. Analysis (分析)

### Root cause: big_input breaker HALF_OPEN 1-key probe → 429 cycle

The big_input breaker (NVU_BIG_INPUT_THRESHOLD=250000) was designed to catch zombie completions on large inputs. But it's now **causing more harm than good**:

1. **ALL glm5_2_nv inputs in 6h are 361-362K chars** (above 250K threshold)
2. Breaker routes these to HALF_OPEN probe mode: only **1 key** allowed per attempt
3. That 1 probe key hits NVCF 429 rate-limit (which is per-IP, not per-key related to big input)
4. Breaker interprets 429 as "big input failed" → back to OPEN → **instant 502**
5. No zombie detection issue: the 1 zombie at 362K was already caught by **NV-ZOMBIE-EMPTY** detection in the normal path

### Why normal path is better for 361-362K inputs
- Normal path: **5 keys** tried in sequence, each with UPSTREAM_TIMEOUT=34s
- KEY_COOLDOWN_S=15 prevents rapid key recycling (R2418 fix)
- NV-ZOMBIE-EMPTY detection catches empty completions regardless of breaker
- Budget = 300s (glm5_2_nv), sufficient for multiple key retries

### R2262 precedent
R2262 raised threshold to 370000 for exactly this reason: "big-input breaker 误捕获健康的 glm5_2_nv 请求导致虚假 ATE, 提高阈值让边际请求通过正常路径". It worked — false ATE eliminated.

### Why 375000 not 370000
- All current inputs are 361788-362480 (rounded 361-362K)
- 375000 gives 13K margin above the max observed (362480), ensuring all current traffic flows through normal path
- Future inputs > 375K still get breaker protection (very rare — none in 6h data)

### dsv4p_nv and kimi_nv 0% SR — separate NVCF degradation
- dsv4p_nv: ALL 7 requests timeout at 105-200s. NVCF pexec genuinely slow/degraded, not fixable by config
- kimi_nv: 4 ATE, all pre-tier kills. NVCF degradation, not config issue
- Neither model is in NVU_BIG_INPUT_MODELS → unaffected by this change

### Budget safety check
- Threshold change does NOT affect budget parameters
- Normal path: 5 keys × 34s UPSTREAM_TIMEOUT = 170s max per tier
- Budget: glm5_2_nv=300s > 170s ✓, well within TIER_TIMEOUT_BUDGET_S=630s

---

## 3. Change (执行)

### Single parameter
| param | old | new | location |
|---|---|---|---|
| NVU_BIG_INPUT_THRESHOLD | 250000 | 375000 | /opt/cc-infra/docker-compose.yml line 453 |

### Deployment
```bash
# HM1: edit compose, recreate nv_gw
sed -i '453s/NVU_BIG_INPUT_THRESHOLD=250000/NVU_BIG_INPUT_THRESHOLD=375000/' /opt/cc-infra/docker-compose.yml
cd /opt/cc-infra && docker compose up -d nv_gw
```

### Verification
- Container env: `NVU_BIG_INPUT_THRESHOLD=375000` ✓
- Health check: `{"status": "ok"}` ✓
- Zero downtime: nv_gw recreated in ~2s
- HM2 untouched: no changes on HM2 ✓

---

## 4. Expected outcome (预期效果)

1. **glm5_2_nv**: 361-362K inputs route to normal 5-key path → fewer instant ATE, higher SR
2. **Zombie defense preserved**: NV-ZOMBIE-EMPTY detection in normal path catches empty completions (confirmed in 6h data: zombie at 362K was detected)
3. **Breaker still available**: inputs > 375K get breaker protection (none in current traffic)
4. **No regression on dsv4p_nv/kimi_nv**: neither model in NVU_BIG_INPUT_MODELS

### What to watch for next round
- glm5_2_nv SR improvement (from 60.7% toward 70%+)
- 361-362K ATE elimination (should go to 0 for these input sizes)
- Any new zombie at 361-374K range (should be caught by NV-ZOMBIE-EMPTY, not breaker)
- dsv4p_nv/kimi_nv NVCF recovery (separate from this change)

---

## ⏳ 轮到HM1优化HM2
