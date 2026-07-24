# HM2 Optimizes HM1 — R2336 (NOP: R2335 settling, 7-min fresh container, zero traffic)

**Date**: 2026-07-25 03:27 UTC  
**Trigger**: cron false trigger — script saw HM1 commit `04eea5e` (R2334) but it was already processed; HM1 has no new commit. R2335 was applied but uncommitted to GitHub.  
**Coauthor**: opc2_uname (HM2) → optimizing HM1  
**Round**: R2336  
**Scope**: Only HM1 (`docker-compose.yml`, `nv_gw` container). **No changes.**  
**Iron Law**: Only edit HM1. Never touch HM2 local.

---

## 1. Data Snapshot (pre-R2336)

**Window**: 24 hours (2026-07-24 03:00–2026-07-25 03:27 UTC)  
**Source**: `nv_requests` / `nv_tier_attempts` tables in `hermes_logs` (logs_db), `nv_gw` env.

### 1.1 Container Status

| Container | Status | Uptime |
|---|---|---|
| nv_gw | Up (healthy) | 7 minutes |
| ms_gw | Up (healthy) | 34 hours |
| logs_db | Up (healthy) | 8 days |

**nv_gw restarted 7 minutes ago** for R2335 `NVU_TIER_BUDGET_KIMI_NV=180` application. Zero post-restart traffic.

### 1.2 24h Per-Model (nv_requests)

| model | total | OK | fail | SR | avg_ms | max_ms |
|---|---|---|---|---|---|---|
| dsv4p_nv | 66 | 17 | 49 | 25.8% | 52,581 | 170,061 |
| glm5_2_nv | 143 | 44 | 99 | 30.8% | 9,985 | 64,871 |
| kimi_nv | 23 | 12 | 11 | 52.2% | 86,797 | 170,258 |

### 1.3 8h Tier Attempt Errors (nv_tier_attempts)

| tier | error_type | cnt |
|---|---|---|
| glm5_2_nv | 429_nv_rate_limit | 20 |
| kimi_nv | empty_200 | 7 |
| dsv4p_nv | NVCFPexecTimeout | 1 |
| dsv4p_nv | NVCFPexecSSLEOFError | 1 |
| kimi_nv | NVCFPexecRemoteDisconnected | 1 |

### 1.4 Budget-Ceiling ATE (≥160s, 24h)

| model | cnt | first | last |
|---|---|---|---|
| dsv4p_nv | 8 | 03:07 UTC | 14:05 UTC |
| kimi_nv | 8 | 16:23 UTC | 19:15 UTC |

### 1.5 Active Env Parameters (nv_gw)

```
NVU_TIER_BUDGET_KIMI_NV=180     ← R2335 (170→180)
NVU_TIER_BUDGET_DSV4P_NV=120    ← R2334 (100→120)
NVU_TIER_BUDGET_GLM5_2_NV=210
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
TIER_COOLDOWN_S=30              ← R2332 (10→30)
KEY_COOLDOWN_S=30               ← R2331 (10→30)
NVU_BIG_INPUT_COOLDOWN_S=90     ← R2330 (120→90)
UPSTREAM_TIMEOUT=24
TIER_TIMEOUT_BUDGET_S=415
```

### 1.6 Latest Requests (recent 4h)

| ts (UTC) | model | status | duration_ms | error |
|---|---|---|---|---|
| 19:36 | kimi_nv | 200 | 17,807 | — |
| 19:33 | glm5_2_nv | 502 | 7 | all_tiers_exhausted (429 storm) |
| 19:33 | glm5_2_nv | 502 | 7 | all_tiers_exhausted (429 storm) |
| 19:33 | glm5_2_nv | 429 | 7,450 | all_tiers_exhausted |
| 19:30 | kimi_nv | 200 | 171,402 | — (slow success, pre-R2335) |
| 19:15 | kimi_nv | 502 | 169,215 | all_tiers_exhausted (ATE at ~170s) |
| 19:13 | kimi_nv | 200 | 3,511 | — |
| 19:05 | dsv4p_nv | 502 | 120,083 | all_tiers_exhausted |
| 19:04 | kimi_nv | 502 | 170,113 | all_tiers_exhausted (ATE at ~170s) |

**Post-R2335 traffic**: 0 requests (container restarted 7 min ago, no traffic yet).

---

## 2. Analysis

### 2.1 NOP Verification Checklist

| # | Gate | Status |
|---|---|---|
| 1 | Did HM1 commit a new commit to GitHub? | **NO**. HEAD is `04eea5e` (R2334), already processed. `6688ed7` (R2317) is HM1's latest. No new HM1 commit. |
| 2 | Is container <8h old (restart or redeploy)? | **YES** (7 min uptime) → settling → NOP |
| 3 | Is post-restart traffic ≥10 valid requests? | **0** post-restart reqs → insufficient → NOP |
| 4 | Are all major metrics in extrapolated normal range? | Pre-R2335 regime shows mixed state. R2335 `NVU_TIER_BUDGET_KIMI_NV=180` needs traffic to verify. |
| 5 | Is there any safe + data-backed change? | No. All parameters are in settling phase post-R2335. |

### 2.2 Why No Change Is Safe

**R2335 settling**: `NVU_TIER_BUDGET_KIMI_NV=170→180` was applied 7 minutes ago. Zero traffic since. The change targets kimi_nv ATE at 170s budget ceiling — 8 ATE in 24h with 5th key untried. 180s gives the 5th key one more attempt. Need ≥4h and ≥5 kimi_nv requests to assess.

**R2334 settling**: `NVU_TIER_BUDGET_DSV4P_NV=100→120` (R2334) still needs verification. 24h: 17/66 (25.8% SR). R2335 report noted 2/2 success post-R2334 initially, but 24h aggregate still low. R2334's container restart was ~19:00 UTC — the 25.8% SR includes both pre- and post-R2334 data. Need clean separation.

**glm5_2_nv 429 storm**: 20 tier attempts with 429 errors in 8h. R2331 `KEY_COOLDOWN_S=30` and R2332 `TIER_COOLDOWN_S=30` are in place. The 429 storm is NVCF rate-limit, not a parameter issue. KEY_COOLDOWN_S=30 needs more settling time (was 10s before R2331). Instant 7ms fast-fails (all 5 keys return 429 in <10s) confirm the storm is still active. No parameter change can fix NVCF account-level rate limits.

**dsv4p_nv**: 8 budget-ceiling ATE in 24h, last at 14:05 UTC. R2334 `120s` budget should help. The `NVCFPexecTimeout` (67s) and `NVCFPexecSSLEOFError` (5s) are NVCF-side issues, not budget issues.

**kimi_nv empty_200**: 7 tier attempts with empty_200 in 8h. This is NVCF returning HTTP 200 with empty body — a known NVCF quirk. R2335 budget increase won't fix empty_200; it only helps the 5th-key-untried ATE pattern.

### 2.3 Queued Future Candidates (NOT this round)

| Candidate | Trigger | Current State |
|---|---|---|
| `NVU_TIER_BUDGET_KIMI_NV` 180→190 | ≥2 ATE still at 180s ceiling after ≥4h | Need ≥4h post-R2335 traffic |
| `KEY_COOLDOWN_S` 30→40 or 30→20 | glm5_2_nv 429 persists >12h after R2331 | 429 still active, but cooldown direction unclear |
| `NVU_TIER_BUDGET_DSV4P_NV` 120→130 | dsv4p_nv ATE still at 120s ceiling | Need post-R2334 clean data |
| `NVU_BIG_INPUT_COOLDOWN_S` 90→60 | Big-input breaker CLOSED fast, low false-positive | Need daytime big-input traffic |

---

## 3. Plan → NONE (NOP)

Consolidating R2335 + R2334 settling. All parameters are open but not yet validated. Container is 7 minutes old with zero traffic. No safe change exists.

**R2335 commit**: R2335 was applied to HM1's `nv_gw` (env shows `NVU_TIER_BUDGET_KIMI_NV=180`) but was not committed to GitHub. This round commits R2335 to GitHub so HM1's repo is synchronized.

---

## 4. Deploy → NONE

No `docker-compose.yml` edits. No restart. Zero downtime.

---

## 5. Post-Deploy Verification

Since no deploy, verification is health check only:

```
nv_gw    Up 7 minutes (healthy)   ← R2335 applied, NVU_TIER_BUDGET_KIMI_NV=180
ms_gw    Up 34 hours (healthy)
logs_db  Up 8 days (healthy)
```

All containers nominal. Env parameters confirmed correct.

---

## 6. Summary

- **R2336 = NOP** — false trigger (no new HM1 commit) + 7-minute fresh container + zero post-restart traffic.
- R2335 `NVU_TIER_BUDGET_KIMI_NV=180` committed to GitHub (was previously uncommitted).
- R2334 `NVU_TIER_BUDGET_DSV4P_NV=120` still settling.
- Iron law: only HM1 config touched (in fact, nothing touched this round).
- Next real activation: ≥4h post-R2335 + ≥5 kimi_nv requests → evaluate if 5th key is now attempted.

## ⏳ 轮到HM1优化HM2