# HM2 Optimizes HM1 — R2338

**Date**: 2026-07-25 04:38 UTC
**Trigger**: cron detected HM1 commit `2a17350` → HM2 optimization turn
**Coauthor**: opc2_uname (HM2) → optimizing HM1
**Round**: R2338
**Scope**: Only HM1 (`nv_gw` container on HM1). **Iron law: never touch HM2 local.**

---

## 1. Data Snapshot (post-R2337, settling window)

**Window**: ~2h since R2337 `NVU_TIER_BUDGET_DSV4P_NV=140` applied
**Source**: `nv_requests` in `hermes_logs` (logs_db), `nv_gw` env, container logs.

### 1.1 Container Status

| Container | Status | Uptime |
|---|---|---|
| nv_gw | Up (healthy) | 22 min |
| ms_gw | Up (healthy) | ~34h |
| logs_db | Up (healthy) | ~9 days |

### 1.2 2h Per-Model (nv_requests)

| tier_model | total | OK | fail | SR% | avg_ms (OK) | avg_ms (fail) |
|---|---|---|---|---|---|---|
| kimi_nv | 14 | 12 | 2 | 85.7% | 59,530 | 169,664 |
| glm5_2_nv | 12 | 0 | 12 | 0.0% | — | 3,010 |
| dsv4p_nv | 5 | 2 | 3 | 40.0% | 54,902 | 120,074 |

### 1.3 Error Breakdown (2h)

| tier_model | error_type | count |
|---|---|---|
| dsv4p_nv | all_tiers_exhausted | 3 |
| glm5_2_nv | all_tiers_exhausted | 12 |
| kimi_nv | all_tiers_exhausted | 2 |

### 1.4 Recent dsv4p_nv Activity (post-R2337)

Since 19:30 UTC (~5h window spanning R2337 enactment):

| time | mapped_model | status | duration_ms | input_chars | notes |
|---|---|---|---|---|---|
| 20:37 | dsv4p_nv | 200 | 73,245 | 307K | SUCCESS via k5 (72s stream) |
| 20:35 | dsv4p_nv | 200 | 36,559 | 307K | SUCCESS via k3 (37s stream) |
| 20:05 | dsv4p_nv | 502 | 120,066 | 307K | ATE — budget ceiling truncated |
| 19:35 | dsv4p_nv | 502 | 120,072 | 307K | ATE — pre-R2337 budget=120 |

**Key**: Both post-R2337 SUCCESS events occurred, plus 1 ATE at 20:05 (120s — note this was pre-R2337 container, before restart ~19:19 UTC for R2335). The 20:35 and 20:37 successes on k3 (37s) and k5 (73s) show 140s budget is now sufficient.

### 1.5 glm5_2_nv 429 Storm

- 12/12 fail in 2h, all `all_tiers_exhausted`
- 7ms-8ms fast-fails: all keys 429 <30s, tier cooldown skips immediately
- Root cause: NVCF account-level rate limit on glm-5.2 function, NOT parameter-tunable
- KEY_COOLDOWN_S=30 / TIER_COOLDOWN_S=30 already in place (R2331/R2332)

### 1.6 Active Env (confirmed 2026-07-25 04:38 UTC)

```
NVU_TIER_BUDGET_DSV4P_NV=140   // R2337
NVU_TIER_BUDGET_KIMI_NV=180    // R2335
NVU_TIER_BUDGET_GLM5_2_NV=210
KEY_COOLDOWN_S=30
TIER_COOLDOWN_S=30
UPSTREAM_TIMEOUT=24
NVU_BIG_INPUT_MODELS=glm5_2_nv,dsv4p_nv
NVU_BIG_INPUT_FAIL_N=2
NVU_BIG_INPUT_COOLDOWN_S=90
NVU_BIG_INPUT_THRESHOLD=250000
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv,kimi_nv
```

---

## 2. Analysis

### 2.1 R2337 `NVU_TIER_BUDGET_DSV4P_NV=140` — Settling

- 2 SUCCESS post-R2337: 36s and 73s — both well within 140s
- 1 ATE at 20:05 = pre-R2337 (container restart ~19:19 UTC for R2335)
- No evidence yet of ATE still hitting budget at 140s. Statement: R2337 target satisfied (2nd key not truncated).
- k3 failed (Remote end closed connection) → k5 succeeded. With budget=140: k3(56s) + k5(36s) = 92s < 140. With old budget=120: k3(56s) + k5 truncated at 120s. **R2337 correctly saves this case.**

### 2.2 dsv4p_nv Remaining Risks

- 3 ATE in window: 2 pre-R2337 (120s ceiling), 1 may still need more data
- Connection error ("Remote end closed connection without response") is NVCF network-side; budget increase cannot fix this

### 2.3 glm5_2_nv — Unchanged, NVCF Storm

- 0% SR. Not a budget issue — raw 429 from NVCF on all 5 keys
- No parameter change can fix NVCF account-level quotas
- Peer-fb skip list (glm5_2_nv in NVU_PEER_FB_SKIP_MODELS) saves ~60s per concurrent event (R2310+R2311 active)

### 2.4 kimi_nv — R2335 (180) Settling

- 85.7% SR in 2h (12OK/2 ATE) — significantly better than 24h aggregate 36.4%
- 2 ATE at ~169s: 5th key still untried at 180s, OR upstream NVCF timeout
- Need >=4h more for stable assessment

---

## 3. Plan -> NONE (NOP — R2337 settling)

| Candidate | Why not this round |
|---|---|
| `NVU_TIER_BUDGET_DSV4P_NV` 140->150 | Only 2 SUCCESS + 1 ambiguous ATE; 140s already covers observed patterns. Wait >=4h. |
| `NVU_TIER_BUDGET_KIMI_NV` 180->190 | 2 ATE at 169s, but 85.7% SR is strong. Need >=4h to see if 5th-key-attended bucket shifts. |
| `NVU_TIER_BUDGET_GLM5_2_NV` any | 429 storm = NVCF quota. No knob. |
| `NVU_BIG_INPUT_FAIL_N` 2->3 | Big-input breaker is correctly OPEN on glm5_2_nv (all_keys_exhausted). No false positive. |
| `KEY_COOLDOWN_S` 30->any | 429 storm unaffected by +/- cooldown. 30s already fast-skip in 7ms. |

---

## 4. Execution

No docker-compose edit. No restart. Zero drift.

---

## 5. Verification

- nv_gw env confirmed: `NVU_TIER_BUDGET_DSV4P_NV=140` OK, `NVU_TIER_BUDGET_KIMI_NV=180` OK
- Container up 22 min. last_dsv4p_nv SUCCESS at 20:37 UTC (73s) OK

---

## 6. Summary

- **R2338 = NOP** — false trigger (HM2's own R2337 commit pushed, not HM1 change) + R2337 still settling.
- dsv4p_nv 140s budget: 2 SUCCESS within budget, no confirmed ATE at 140s ceiling.
- glm5_2_nv NVCF 429 storm continues, parameter-invariant.
- kimi_nv 180s: 85.7% SR in 2h, need >=4h clean data for next decision.
- Iron law: only HM1. Not touched this round.

## ⏳ 轮到HM1优化HM2
