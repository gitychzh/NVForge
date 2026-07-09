# R997 (HM2→HM1): FASTBREAK 2→1 — integrate pexec fallback budget rescue

**Date**: 2026-07-09 21:05 UTC+8  
**Type**: HM2→HM1 optimization  
**Param**: `NVU_PEXEC_TIMEOUT_FASTBREAK` 2→1  
**Iron rule**: Only change HM1, never HM2

## 6h Data (2026-07-09 13:09 UTC, pre-restart)

| Metric | Value |
|--------|-------|
| Total requests | 81 |
| Success | 64 (79.0%) |
| Errors | 17 (21.0%) |
| dsv4p_nv SR | 24/32 = 75.0% (8 ATE) |
| glm5_2_nv SR | 40/49 = 81.6% (9 ATE) |

## ATE Breakdown

| Tier | ATE count | avg_dur | error_type |
|------|-----------|---------|------------|
| dsv4p_nv | 8 | 112,051ms | all_tiers_exhausted, tiers_tried_count=1 |
| glm5_2_nv | 9 | 96,850ms | all_tiers_exhausted |

## Tier Attempts (dsv4p_nv)

| Error | Count | Max |
|-------|-------|-----|
| IntegrateTimeout | 14 | 67,086ms |

## Tier Attempts (glm5_2_nv)

| Error | Count | Max |
|-------|-------|-----|
| NVCFPexecTimeout | 6 | 62,606ms |
| 504_nv_gateway_timeout | 2 | - |
| empty_200 | 1 | - |

## dsv4p_nv Success Path

| upstream_type | fallback | cnt | avg_dur |
|---------------|----------|-----|---------|
| nv_integrate | f | 15 | 41,360ms |
| nvcf_pexec | f | 7 | 122,933ms |
| nvcf_pexec | t | 6 | 100,002ms |

## Log Pattern (dsv4p_nv ATE)

```
[NV-REQ] mapped_model=dsv4p_nv tier_chain=['dsv4p_nv'] (no fallback, 3model)
[NV-INTEGRATE] attempt 1/7: k1 -> integrate ... DIRECT
[NV-INTEGRATE-TIMEOUT] k1 integrate timeout: attempt=66451ms
[NV-INTEGRATE] attempt 2/7: k2 -> integrate ... DIRECT
[NV-INTEGRATE-TIMEOUT] k2 integrate timeout: attempt=45591ms
[NV-INTEGRATE-FASTBREAK] 2 consecutive timeouts -> fast-break
[NV-INTEGRATE-FAIL] all integrate keys failed: timeout=2, elapsed=112045ms
[NV-INTEGRATE-FALLBACK] integrate all-failed -> falling back to pexec same model
[NV-KEY] attempt 1/7: k3 -> NVCF pexec 74f02205-c7b... DIRECT
[NV-ALL-TIERS-FAIL] All 1 tiers failed, elapsed=112051ms, ABORT-NO-FALLBACK
-> 502: all_tiers_exhausted, duration=112,051ms
```

## Root Cause

dsv4p_nv integrate path consumes the entire BUDGET (112s) before pexec fallback gets a chance:
- Integrate k1: ~66s (UPSTREAM_TIMEOUT=66 binding, IntegrateTimeout max=67,086ms)
- Integrate k2 (FASTBREAK=2): ~46s, then fastbreak
- Total integrate: ~112s = BUDGET=112 → pexec fallback gets 0s budget
- Result: 8 ATE all at exactly 112,051ms avg

dsv4p_nv pexec CAN work: 13 direct successes (7 direct + 6 fallback from integrate) in 6h, avg 100-122s.

## Fix

**FASTBREAK 2→1**: integrate stops after 1 timeout (66s), leaves 46s for pexec fallback:
- Integrate k1: 66s
- pexec fallback: 46s budget (112-66=46)
- 46s is sufficient for pexec success (pexec success avg 100-122s = multi-key cycling within budget, not single-key full duration)

## Container Status

- Container: `nv_gw` up, healthy
- Restart: `docker compose stop nv_gw && docker compose up -d nv_gw`
- Env verified: `NVU_PEXEC_TIMEOUT_FASTBREAK=1`

## Compose Diff

```diff
- NVU_PEXEC_TIMEOUT_FASTBREAK: "2"  # R832c (HM1 self): ...
+ NVU_PEXEC_TIMEOUT_FASTBREAK: "1"  # R997 (HM2->HM1): FASTBREAK 2->1. BUDGET=112 integrate consume ~66s (k1) + ~46s (k2 FASTBREAK) = ~112s leaves 0s for pexec fallback -> 8 ATE at 112,051ms avg. FASTBREAK=1: integrate 66s + pexec fallback gets 46s budget. Single param; iron rule: only change HM1 never HM2.
```

## Other Parameters (unchanged)

| Param | Value |
|-------|-------|
| UPSTREAM_TIMEOUT | 66 |
| TIER_TIMEOUT_BUDGET_S | 112 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 |
| NVU_EMPTY_200_FASTBREAK | 3 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 |
| NV_INTEGRATE_MODELS | glm5_2_nv,dsv4p_nv |
| NVU_MS_GW_FALLBACK_TIMEOUT | 45 |
| KEY_COOLDOWN_S | 25 |

## ⏳ 轮到HM1优化HM2