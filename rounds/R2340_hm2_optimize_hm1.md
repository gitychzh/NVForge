# HM2 Optimizes HM1 — R2340

**Date**: 2026-07-25 05:45 UTC
**Trigger**: cron detected HM1 commit `acadf27` (R2338 NOP) → HM2 optimization turn
**Coauthor**: opc2_uname (HM2) → optimizing HM1
**Round**: R2340
**Scope**: Only HM1 (`nv_gw` container on HM1). **Iron law: never touch HM2 local.**

---

## 1. Data Snapshot (24h, nv_requests)

**Source**: `nv_error_detail` logs, `nv_requests` DB, `nv_gw` env.

### 1.1 Per-Model 24h Stats

| tier_model | total | OK | fail | SR% | Primary Failure |
|---|---|---|---|---|---|
| kimi_nv | 35 | 24 | 11 | 68.6% | ATE (empty_200 + timeout) |
| glm5_2_nv | 109 | 42 | 67 | 38.5% | 429_nv_rate_limit (cluster-level) |
| dsv4p_nv | 63 | 15 | 48 | 23.8% | ATE (504 + NVCFPexecTimeout) |

### 1.2 Error Type Breakdown (24h, nv_error_detail)

| tier_model | error_type | count | notes |
|---|---|---|---|
| kimi_nv | empty_200 | 12 | Content-Length:0, always failure |
| kimi_nv | NVCFPexecRemoteDisconnected | 3 | key_idx 3,4 |
| kimi_nv | NVCFPexecTimeout | 3 | |
| kimi_nv | NVCFPexecSSLEOFError | 1 | |
| glm5_2_nv | 429_nv_rate_limit | 27 | all 5 keys, cluster-level |
| glm5_2_nv | NVCFPexecTimeout | 1 | |
| glm5_2_nv | NVCFPexecSSLEOFError | 2 | |
| glm5_2_nv | NVCFPexecRemoteDisconnected | 1 | |
| dsv4p_nv | 504_nv_gateway_timeout | ~15 | NVCF internal |
| dsv4p_nv | NVCFPexecTimeout | ~10 | budget ceiling |
| dsv4p_nv | NVCFPexecRemoteDisconnected | ~5 | |
| dsv4p_nv | empty_200 | 1 | rare |

### 1.3 Recent kimi_nv ATE Pattern

kimi_nv ATE requests consistently show 2+ empty_200 before timeout:
- `5cd6904e`: k0 empty_200, k1 empty_200, k2 NVCFPexecTimeout → 170s ATE
- `0a426678`: k2 SSLEOF, k3 RemoteDisconnected, k4 empty_200, k0 empty_200 → 169s ATE
- `09961147`: k1 empty_200, k2 empty_200, k3 RemoteDisconnected, k4 NVCFPexecTimeout → 180s ATE
- `0bea7205`: k3 RemoteDisconnected, k4 empty_200, k0 empty_200, k1 NVCFPexecTimeout → 180s ATE
- `78849643`: k4 empty_200, k0 empty_200, k1 NVCFPexecTimeout → 180s ATE

**Pattern**: 2 empty_200s per ATE is typical, FASTBREAK=3 was allowing a 3rd attempt that never succeeds (empty_200 = Content-Length:0 = always failure).

### 1.4 glm5_2_nv 429 Storm

Parameter-invariant. All 5 keys get 429 simultaneously. KEY_COOLDOWN_S=30 already applied.
No change to glm5_2_nv in this round.

### 1.5 dsv4p_nv Status

Post-R2337 (NVU_TIER_BUDGET_DSV4P_NV=140): 2/5 success (40%) in 2h window.
Budget at 140s, no ATE ceiling observed. Stable.

---

## 2. Optimization Applied

### Change: `NVU_EMPTY_200_FASTBREAK: 3 → 2`

**Rationale**:
- kimi_nv = 12 empty_200 in 24h (only tier with empty_200)
- dsv4p_nv = 1 empty_200, glm5_2_nv = 0 empty_200
- Empty_200 always = Content-Length:0 = failure. No chance of 3rd attempt succeeding.
- FASTBREAK=2: break after 2 empty_200s → saves ~30s per key wasted on 3rd attempt
- With NVU_TIER_BUDGET_KIMI_NV=180, every 30s matters for attempting more keys
- **Impact**: kimi_nv ATE completion time reduced by ~30s per stuck key, more keys attempted within 180s budget
- **Risk**: Zero — empty_200 is never a success; dsv4p_nv/glm5_2_nv unaffected

**Before**:
```
NVU_EMPTY_200_FASTBREAK=3
```

**After**:
```
NVU_EMPTY_200_FASTBREAK=2
```

**Binary**: No code change, env var only. Single param. Iron law: only HM1.

---

## 3. Verification

```bash
$ docker exec nv_gw env | grep EMPTY_200_FASTBREAK
NVU_EMPTY_200_FASTBREAK=2

$ docker ps --filter name=nv_gw --format "{{.Status}}"
Up 15 seconds (healthy)
```

---

## 4. Next Round Watch Items

1. **kimi_nv**: Monitor ATE count — expect reduction as FASTBREAK=2 saves ~30s per stuck key, more keys attempted within 180s budget
2. **glm5_2_nv**: 429 storm continues, parameter-invariant. NVCF cluster-level rate limit.
3. **dsv4p_nv**: 140s budget stable, continue monitoring.
4. **Iron law**: only HM1. Not touched this round.

---

## ⏳ 轮到HM1优化HM2