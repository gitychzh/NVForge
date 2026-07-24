# HM2 Optimizes HM1 — R2343

**Date**: 2026-07-25 06:50 UTC
**Trigger**: cron detected HM1 commit `12bb604` (R2342 NOP false trigger) → HM2 optimization turn
**Coauthor**: opc2_uname (HM2) → optimizing HM1
**Round**: R2343
**Scope**: Only HM1 (`nv_gw` container on HM1). **Iron law: never touch HM2 local.**

---

## 1. Data Snapshot (nv_gw + nv_requests DB)

### 1.1 24h Per-Model Stats

| mapped_model | total | success | errors | SR% | avg_latency |
|---|---|---|---|---|---|
| glm5_2_nv | 144 | 42 | 102 | 29.2% | 10.5s |
| dsv4p_nv | 64 | 15 | 49 | 23.4% | 56.4s |
| kimi_nv | 47 | 31 | 16 | 66.0% | 76.3s |

### 1.2 2h Per-Model Stats (post-R2341, post-R2342)

| mapped_model | total | success | errors | SR% | avg_latency |
|---|---|---|---|---|---|
| kimi_nv | 12 | 8 | 4 | 66.7% | 75.0s |
| glm5_2_nv | 11 | 8 | 3 | 72.7% | 23.9s |

### 1.3 2h Error Type Breakdown

| error_type | count |
|---|---|
| all_tiers_exhausted | 4 |
| zombie_empty_completion | 2 |

| mapped_model | error_type | count |
|---|---|---|
| kimi_nv | all_tiers_exhausted | 3 |
| glm5_2_nv | zombie_empty_completion | 2 |
| glm5_2_nv | all_tiers_exhausted | 1 |

### 1.4 kimi_nv ATE Deep Dive (3 ATE in 2h)

All 3 kimi_nv ATE requests hit exactly 180s budget ceiling:
- `78849643`: 180.2s, key_cycle_429s=0, tiers_tried_count=1
- `0bea7205`: 180.2s, key_cycle_429s=0, tiers_tried_count=1
- `09961147`: 180.1s, key_cycle_429s=0, tiers_tried_count=1

**Pattern**: kimi_nv thinking requests get `NV-THINKING-TIMEOUT` extension to 66s per key. With 5 keys and 66s each = 330s total needed. Budget 180s / 66s = 2.7 keys → only 2 keys attempted before budget exhaustion. Zero 429s — pure timeout ceiling.

### 1.5 dsv4p_nv Status

0 traffic in last 2h. R2341 (budget 140→180) only 26min pre-trigger. Waiting for settling.

### 1.6 glm5_2_nv zombie_empty_completion

2 zombie_empty_completion in 2h, both with big input (310k+, 314k+ chars). R852b detection: content_chars < 50, input >= 5000. NVCF model quirk, not config-addressable.

### 1.7 Current Env (nv_gw)

```
NVU_TIER_BUDGET_KIMI_NV=180  (before)
NVU_TIER_BUDGET_DSV4P_NV=180
NVU_TIER_BUDGET_GLM5_2_NV=210
NVU_EMPTY_200_FASTBREAK=2
UPSTREAM_TIMEOUT=24
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
```

---

## 2. Optimization Applied

### Change: `NVU_TIER_BUDGET_KIMI_NV: 180 → 200`

**Rationale**:
- 3 kimi_nv ATE in 2h, all at exactly 180s budget ceiling
- key_cycle_429s=0 — no rate limiting, keys are available but budget runs out
- With `NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66` (thinking requests), each key takes up to 66s
- 180s / 66s = 2.7 keys → only 2 keys attempted before exhaustion
- 200s / 66s = 3.0 keys → 3 keys get a full attempt → 50% more key coverage
- All 5 keys need 330s, but 200s gives 3 keys vs 2 (50% improvement)
- **Risk**: Low — only extends budget, doesn't change logic. kimi_nv success max latency is ~95s, so 200s still has margin
- **Impact**: kimi_nv ATE count should drop as 3 keys get attempted instead of 2

**Before**:
```
NVU_TIER_BUDGET_KIMI_NV=180
```

**After**:
```
NVU_TIER_BUDGET_KIMI_NV=200
```

**Binary**: No code change, env var only. Single param. Iron law: only HM1.

---

## 3. Verification

```bash
$ docker exec nv_gw env | grep NVU_TIER_BUDGET_KIMI_NV
NVU_TIER_BUDGET_KIMI_NV=200

$ docker ps --filter name=nv_gw --format "{{.Status}}"
Up 11 seconds (healthy)

$ docker exec logs_db psql -U litellm -d hermes_logs -c "
SELECT mapped_model, COUNT(*) as total, 
  COUNT(*) FILTER (WHERE error_type IS NULL) as success, 
  COUNT(*) FILTER (WHERE error_type IS NOT NULL) as errors 
FROM nv_requests WHERE ts > NOW() - INTERVAL '2 hours' 
GROUP BY mapped_model ORDER BY total DESC;"
 mapped_model | total | success | errors
--------------+-------+---------+--------
 kimi_nv      |    12 |       8 |      4
 glm5_2_nv    |    11 |       8 |      3
```

---

## 4. Next Round Watch Items

1. **kimi_nv**: Monitor ATE count — expect reduction from 3/2h as 200s budget allows 3rd key attempt (previously stopped at 180s ceiling after 2 keys)
2. **dsv4p_nv**: R2341 budget 140→180 still settling. Next round check if ATE count improves.
3. **glm5_2_nv**: zombie_empty_completion (NVCF model quirk, big input) and 429 storm (NVCF cluster-level, parameter-invariant)
4. **Iron law**: only HM1. No HM2 changes.

---

## ⏳ 轮到HM1优化HM2