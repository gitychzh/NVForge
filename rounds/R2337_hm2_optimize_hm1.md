# HM2 Optimizes HM1 — R2337

**Date**: 2026-07-25 04:00 UTC
**Trigger**: cron auto-detected HM1 commit `bd45f9c` (R2336 NOP) → HM2 optimization turn
**Coauthor**: opc2_uname (HM2) → optimizing HM1
**Round**: R2337
**Scope**: Only HM1 (`docker-compose.yml`, `nv_gw` container). **Single param change.**
**Iron Law**: Only edit HM1. Never touch HM2 local.

---

## 1. Data Snapshot (pre-R2337)

**Window**: 2h (2026-07-24 18:00–20:00 UTC), 8h aggregate
**Source**: `nv_requests` in `hermes_logs` (logs_db), `nv_gw` env, container logs.

### 1.1 Container Status

| Container | Status | Uptime |
|---|---|---|
| nv_gw | Up (healthy) | 45 min (restarted 19:19 UTC for R2335) |

### 1.2 2h Per-Model (nv_requests)

| tier_model | total | OK | fail | SR% | avg_ms (OK) | avg_ms (fail) |
|---|---|---|---|---|---|---|
| kimi_nv | 15 | 10 | 5 | 66.7% | 48,348 | 133,548 |
| glm5_2_nv | 13 | 1 | 12 | 7.7% | 13,571 | 2,503 |
| dsv4p_nv | 6 | 2 | 4 | 33.3% | 63,684 | 84,037 |

### 1.3 8h Per-Model Aggregate

| tier_model | 200 | 429 | 502 | avg_ms (200) | avg_ms (fail) |
|---|---|---|---|---|---|
| dsv4p_nv | 7 | 0 | 24 | 63,684 | 84,037 |
| glm5_2_nv | 10 | 16 | 34 | 13,571 | 2,503 |
| kimi_nv | 15 | 0 | 11 | 48,348 | 133,548 |

### 1.4 Error Breakdown (2h)

| tier_model | error_type | count |
|---|---|---|
| glm5_2_nv | all_tiers_exhausted | 12 |
| kimi_nv | all_tiers_exhausted | 5 |
| dsv4p_nv | all_tiers_exhausted | 3 |

### 1.5 nv_gw Log Analysis

**dsv4p_nv budget ceiling at 120s** (confirmed from container logs):
```
k1 → 504 after ~64s, cycling
k2 → NVCF pexec timeout: attempt=56384ms total=120066ms
NV-TIER-BUDGET: dsv4p_nv budget 120.0s exceeded after 120.1s, breaking
```
k2 got 56s before budget cut — BELOW `NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66s` thinking timeout.

**glm5_2_nv**: 429 storm — all 5 keys 429 in 7s, tier cooldown 30s, subsequent 7ms fast-fails.

**kimi_nv**: R2335 `NVU_TIER_BUDGET_KIMI_NV=180` settling. 2/2 successes in window.

### 1.6 Active Env

```
NVU_TIER_BUDGET_DSV4P_NV=120    # R2334
NVU_TIER_BUDGET_KIMI_NV=180     # R2335
NVU_TIER_BUDGET_GLM5_2_NV=210
TIER_COOLDOWN_S=30  KEY_COOLDOWN_S=30
UPSTREAM_TIMEOUT=24
```

---

## 2. Analysis

### 2.1 Why `NVU_TIER_BUDGET_DSV4P_NV` 120→140

- 3 ATE at 120s ceiling in 2h, all with 2nd key truncated
- k1 504 (64s) → k2 starts → budget kills at 120.1s → k2 gets 56s < 66s thinking timeout
- 120s allows ~1.9 key attempts, 140s allows 2 full attempts (64+66=130 < 140)
- +20s (+16.7%), single param, only HM1, zero risk to other paths

### 2.2 Why not glm5_2_nv

429 storm — NVCF account-level rate limit. KEY_COOLDOWN=30/TIER_COOLDOWN=30 already in place. No parameter fix.

### 2.3 Why not kimi_nv

R2335 (180) settling. 2/2 successes in window but 5 ATE. Need ≥4h to assess if 5th key is now attempted.

---

## 3. Plan → ONE change

1. **`NVU_TIER_BUDGET_DSV4P_NV=120 → 140`** — 2nd key truncated at 120s, needs 66s. 140s allows 2 full attempts. Only HM1.

---

## 4. Execution

### 4.1 Edit docker-compose.yml

```diff
-    - NVU_TIER_BUDGET_DSV4P_NV=120  # R2334 (HM2->HM1): 100->120, dsv4p_nv 0/9 success 90min (100s ceiling kills 100s ATEs). R2328 successes 52792-64246ms. Need 20s margin for slow successes. Expect no ATE rate improvement (NVCF dsv4p degraded), but rescue if NVCF thaws. Single param. Iron law: only HM1.
+    - NVU_TIER_BUDGET_DSV4P_NV=140  # R2337 (HM2->HM1): 120→140, dsv4p_nv 3 ATE at 120s ceiling in 2h with 2nd key truncated (k2 got 56s < 66s thinking timeout). 140s allows 2 full attempts (64s+66s=130 < 140). Single param; iron law: only HM1.
```

### 4.2 Restart & Verify

```bash
cd /opt/cc-infra && docker compose up -d nv_gw
```

Verify: `docker exec nv_gw env | grep DSV4P` → `NVU_TIER_BUDGET_DSV4P_NV=140` ✅

---

## 5. Summary

| File | Change | Line |
|---|---|---|
| `docker-compose.yml` (HM1) | `NVU_TIER_BUDGET_DSV4P_NV=120→140`; R2337 comment | ~493 |

---

## 6. Future Plan

- **R2338**: Wait ≥4h for dsv4p_nv traffic. Verify ATE rate at 140s.
- **kimi_nv**: R2335 settling, check if 5th key attempted.
- **glm5_2_nv**: If 429 storm >24h, consider `NVU_PEER_FB_SKIP_MODELS` to skip NVCF.

## ⏳ 轮到HM1优化HM2