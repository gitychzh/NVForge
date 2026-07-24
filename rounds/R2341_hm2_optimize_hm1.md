# HM2 Optimizes HM1 — R2341

**Date**: 2026-07-25 06:15 UTC
**Trigger**: cron detected HM1 commit `596eab1` (R2340 NVU_EMPTY_200_FASTBREAK 3→2) → HM2 optimization turn
**Coauthor**: opc2_uname (HM2) → optimizing HM1
**Round**: R2341
**Scope**: Only HM1 (`nv_gw` container on HM1). **Iron law: never touch HM2 local.**

---

## 1. Data Snapshot (24h, nv_requests)

**Source**: `nv_error_detail` logs, `nv_requests` DB, `nv_gw` env.

### 1.1 Per-Model 24h Stats

| tier_model | total | OK | fail | SR% | Primary Failure |
|---|---|---|---|---|---|
| glm5_2_nv | 143 | 42 | 101 | 29.4% | 429_nv_rate_limit (cluster-level) |
| dsv4p_nv | 66 | 16 | 50 | 24.2% | all_tiers_exhausted (504+timeout) |
| kimi_nv | 42 | 26 | 16 | 61.9% | all_tiers_exhausted (empty_200+RemoteDisconnected) |

### 1.2 Per-Model 3h Stats (post-R2340 FASTBREAK=2)

| tier_model | total | OK | fail | SR% | Notes |
|---|---|---|---|---|---|
| glm5_2_nv | 11 | 6 | 5 | 54.5% | Improved from 29.4% (small sample) |
| dsv4p_nv | 2 | 2 | 0 | 100% | Small sample, no ATE observed |
| kimi_nv | 13 | 8 | 5 | 61.5% | Stable |

### 1.3 Error Type Breakdown (24h, nv_tier_attempts)

| tier | error_type | count | notes |
|---|---|---|---|
| glm5_2_nv | 429_nv_rate_limit | 31 | All 5 keys, cluster-level rate limit |
| kimi_nv | empty_200 | 13 | Content-Length:0, always failure |
| dsv4p_nv | NVCFPexecRemoteDisconnected | 3 | |
| kimi_nv | NVCFPexecRemoteDisconnected | 3 | |
| glm5_2_nv | NVCFPexecRemoteDisconnected | 1 | |
| glm5_2_nv | NVCFPexecTimeout | 1 | |
| dsv4p_nv | NVCFPexecSSLEOFError | 1 | |
| dsv4p_nv | NVCFPexecTimeout | 1 | |

### 1.4 dsv4p_nv ATE Pattern (error_detail logs)

Consistent pattern: 504_nv_gateway_timeout (~64s) + NVCFPexecTimeout (~56s) = ~120s, then ATE.
- `5a82460c`: k4 504 (64s), k0 timeout (56s) → 100s ATE, only 2 of 5 keys attempted
- `992d563c`: k1 504, k2 timeout → 120s ATE
- `78020e9c`: k0 504, k1 timeout → 120s ATE
- `6db697e0`: k4 504, k0 timeout → 100s ATE
- `f28df1f3`: k1 504, k2 timeout → 120s ATE
- `6395a462`: k0 504, k1 timeout → 120s ATE

**Pattern**: With `NVU_TIER_BUDGET_DSV4P_NV=140`, dsv4p_nv consistently hits the budget ceiling after 2 keys (120s), leaving 3 keys untouched. Budget exhaustion is the primary failure mode, not individual key failures.

### 1.5 glm5_2_nv 429 Storm

Parameter-invariant. All 5 keys get 429 simultaneously. `KEY_COOLDOWN_S=30` already applied. No change to glm5_2_nv in this round.

### 1.6 kimi_nv empty_200

R2340 changed `NVU_EMPTY_200_FASTBREAK=3→2`. 3h stats show stable 61.5% SR. Empty_200 count in 3h: 4 (down from 13 in 24h). Trend looks good but needs more data.

---

## 2. Optimization Applied

### Change: `NVU_TIER_BUDGET_DSV4P_NV: 140 → 180`

**Rationale**:
- dsv4p_nv = 66 total, 16 ok (24.2% SR) — worst performer
- Error logs show consistent pattern: 504+timeout = ~120s, then budget exhausted at 140s
- Only 2 of 5 keys attempted per ATE; 3 keys never tried
- 140s budget: 2 keys = 120s → 20s remaining (not enough for 3rd key)
- 180s budget: 2 keys = 120s → 60s remaining → allows 3rd key attempt (64s 504 or 56s timeout)
- **Impact**: dsv4p_nv can attempt 3rd key instead of giving up at 140s ceiling
- **Risk**: Low — only extends budget, doesn't change logic. Timeout per key still ~25s (UPSTREAM_TIMEOUT=24)

**Before**:
```
NVU_TIER_BUDGET_DSV4P_NV=140
```

**After**:
```
NVU_TIER_BUDGET_DSV4P_NV=180
```

**Binary**: No code change, env var only. Single param. Iron law: only HM1.

---

## 3. Verification

```bash
$ docker exec nv_gw env | grep NVU_TIER_BUDGET_DSV4P_NV
NVU_TIER_BUDGET_DSV4P_NV=180

$ docker ps --filter name=nv_gw --format "{{.Status}}"
Up 15 seconds (healthy)

$ docker exec -e PGPASSWORD=litellm_pg_2026 logs_db psql -U litellm -d hermes_logs -c "SELECT COUNT(*) as total, COUNT(*) FILTER (WHERE status=200) as ok, tier_model FROM nv_requests WHERE created_at > NOW() - INTERVAL '2 hours' GROUP BY tier_model ORDER BY total DESC;"
 total | ok | tier_model
-------+----+------------
    13 |  8 | kimi_nv
    11 |  6 | glm5_2_nv
     2 |  2 | dsv4p_nv
```

---

## 4. Next Round Watch Items

1. **dsv4p_nv**: Monitor ATE count — expect reduction as 180s budget allows 3rd key attempt (previously stopped at 140s)
2. **glm5_2_nv**: 429 storm continues, parameter-invariant. NVCF cluster-level rate limit.
3. **kimi_nv**: FASTBREAK=2 effect — monitor empty_200 reduction over next 24h
4. **Iron law**: only HM1. Not touched this round.

---

## ⏳ 轮到HM1优化HM2
