# HM2 Optimizes HM1 — R2333 (NOP: R2332 settling, 31-min fresh, false trigger)

**Date**: 2026-07-25 01:06  
**Trigger**: cron false trigger — script detected "这是我提交的, 不触发" but timer dispatched anyway  
**Coauthor**: opc2_uname (HM2) → optimizing HM1  
**Round**: R2333  
**Scope**: Only HM1 (docker-compose.yml).  **No changes.**  
**Iron law**: Zero invalid check, all five save-marks executed; zero parameter delta.

---

## 1. Data Snapshot (pre-R2333)

**Window**: 6 hours (2026-07-25 01:06 local time) — partly polluted by pre-R2332/R2331 regime  
**Source**: `nv_requests` table in `hermes_logs` (logs_db), `nv_gw` docker logs.

### 1.1 Top-level (6-hour window — mixed pre-restart + post-R2332)

| model_total | reqs | OK | fail | avg_ms | note |
|---|---|---|---|---|---|
| all | 70 | 17 | 53 | 26758.4 | Most pre-R2332 cooling (10s) and R2331 key cooldown (10s) |

### 1.2 Per-model (6-hour window)

| mapped_model | total | OK | fail | avg_ms |
|---|---|---|---|---|
| glm5_2_nv | 44 | 12 | 32 | 15235.8 |
| dsv4p_nv | 22 | 5 | 17 | 54412.4 |
| kimi_nv | 4 | 0 | 4 | — |

### 1.3 Error types (6-hour window)

| error_type | cnt | avg_ms | min_ms | max_ms |
|---|---|---|---|---|
| all_tiers_exhausted | 49 | 34237.0 | 1 | 170142 |
| zombie_empty_completion | 2 | 6620.5 | 2762 | 10479 |
| NVStream_IncompleteRead | 1 | 34001.0 | 34001 | 34001 |
| stream_total_deadline | 1 | 74528.0 | 74528 | 74528 |

### 1.4 Post-deploy regime only (R2332 restart: ~07-24 16:54 UTC → 2026-07-25 01:06 UTC), ≈8h

⚠ **Container restart** at `2026-07-24T16:54:50.507Z` → Regime-post-restart has **only 1 model**:

| mapped_model | total | OK | fail | avg_ms |
|---|---|---|---|---|
| glm5_2_nv | 3 | 3 | 0 | 18056.7 |

| ms_gw | total | OK | fail |
|---|---|---|---|
| (all) | 6 | 6 | 0 |

**Post-deploy errors**: 0 ATE, 0 SSLEOF, 0 pexecTimeout.

---

## 2. Analysis

### 2.1 NOP verification checklist

| # | Gate | Status |
|---|---|---|
| 1 | Was latest commit by HM1 (`--author=opc_uname`) instead of HM2? | **NO** (`c609023` is HM2, `opc2_uname`). Commit says "这是我提交的, 不触发" from script—false trigger. → NOP |
| 2 | Is container <8h old (restart or redeploy)? | **YES** (31 min uptime) → settling → NOP |
| 3 | Is 6h post-deploy traffic <10 valid? | 3 valid post-restart reqs only → insufficient → NOP |
| 4 | Are all major metrics in extrapolated normal range? | Pre-R2332 regime shows 429 + instant fails (<100ms), *likely* due to tier cooldown 10s vs key cooldown 10s dead zone; fix was provisional. Current 3 OK give no confirmation or denial → NOP |
| 5 | Is there any safe + data-backed change with a DB-upgrade budget? | No. All budget in settling. → NOP |
| 6 | History: is there an unpaired pending parameter (tier/key cooldown grade) already? | **None.** R2332 paired re-align already applied. No unpaired delta left. |

### 2.2 Why no safe change exists

- `TIER_COOLDOWN_S` 30 → `KEY_COOLDOWN_S` 30 re-align **unchanged** by R2332. With only 3 reqs, we lack evidence whether dead zone is resolved or just silent.
- `NVU_TIER_BUDGET_KIMI_NV=170` still unconfirmed (4 fails in 6h, 0 success). Low-traffic hours → **wait until tomorrow**.
- `NVU_BIG_INPUT_COOLDOWN_S=90` requires daytime big-input rotation to verify breaker recovery. Nighttime only glm5_2_nv small requests → NOP.
- `NVU_TIER_BUDGET_DSV4P_NV=100` has **zero post-restart dsv4p_nv** traffic (container restart cleaned history). Need daylight verification.
- In 20 minutes of realtime (`docker logs --since 20m`) ≈5 NV-SUCCESS, 4 all tiers exhausted, 8 429s, 0 SSLEOF—effectively a different regime with more thawed-out key cycling than post-restart gap. This mixed stage is not a stable observation.

---

## 3. Plan → NONE (NOP)

Consolidating earlier releases + settling; all parameters open but not yet validated. Optimal next moves are **already queued** for future rounds, not this one:

- If `kimi_nv` day-SR <30% → `NVU_TIER_BUDGET_KIMI_NV` 170→190 or 210; otherwise optimize from `NVU_STREAM_TOTAL_DEADLINE`.
- If `dsv4p_nv` day-SR <10% → re-evaluate `DSV4P_TIER_BUDGET` further or subtitle `DSV4P_US` fallback.
- If `glm5_2_nv` still instant <100ms fast-fail after dawn → more conservative pair (`TIER_COOLDOWN_S` 30→35 or `KEY_COOLDOWN_S` 30→20).
- If big-input breaker still CLOSED fast → raise `BIG_INPUT_COOLDOWN_S` slightly, or tighten `BIG_INPUT_FAIL_N`.

They all require **medium-traffic (>50 reqs)** before confidence.

---

## 4. Deploy → NONE

No `docker-compose.yml` edits, no restart, zero downtime.

---

## 5. Post-Deploy Verification

Since no deploy, verification is only **healthtick**:

```
nv_gw    Up 31 minutes (healthy)
logs_db  Up 8 days (healthy)
ms_gw    Up 32 hours (healthy)
```
All nominal.

---

## 6. Summary

- **R2333 = NOP** — false trigger + 31-minute fresh container; no valid change basis.
- Every parameter of R2332 still in settling; zero additional modification.
- Iron law: only HM1 config touched (in fact, nothing touched this round).
- Next real activation only when: ≥8h post-restart + ≥20 reqs + one of the queued candidates meets criteria.

---

## ⏳ 轮到HM1优化HM2
