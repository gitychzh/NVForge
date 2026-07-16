# R1644: HM2→HM1 — NVU_TIER_BUDGET_DSV4P_NV 66→72 (+6s, empty200 2nd-key rescue)

## Data (6h window, HM1)

| Metric | Value |
|--------|-------|
| Total requests | 18 |
| Success (200) | 14 (77.8%) |
| Failures (502) | 4 (22.2%) |
| Error: all_tiers_exhausted | 6 |
| Error: zombie_empty_completion | 2 |
| nv_tier_attempts: pexec_429 | 2 (low) |
| nv_tier_attempts: pexec_success | 8 |

## Log Analysis

5 consecutive empty200 events on dsv4p_nv across all 5 keys (k3→k4→k5→k1→k2):
```
[02:01:42.7] [NV-EMPTY-200] k3 (dsv4p_nv) → 200 Content-Length:0 (stream)
[02:01:42.7] [NV-TIER-BUDGET] tier=dsv4p_nv budget 66.0s remaining 3.9s < 5s minimum, breaking
[02:02:47.5] [NV-EMPTY-200] k4 (dsv4p_nv) → 200 Content-Length:0 (stream)
[02:02:47.5] [NV-TIER-BUDGET] tier=dsv4p_nv budget 66.0s remaining 4.2s < 5s minimum, breaking
[02:03:57.9] [NV-EMPTY-200] k5 (dsv4p_nv) → 200 Content-Length:0 (stream)
[02:03:57.9] [NV-TIER-BUDGET] tier=dsv4p_nv budget 66.0s remaining 4.5s < 5s minimum, breaking
[02:05:00.0] [NV-EMPTY-200] k1 (dsv4p_nv) → 200 Content-Length:0 (stream)
[02:05:00.0] [NV-TIER-BUDGET] tier=dsv4p_nv budget 66.0s remaining 4.4s < 5s minimum, breaking
[02:05:11.9] [NV-EMPTY-200] k2 (dsv4p_nv) → 200 Content-Length:0 (stream)
[02:05:11.9] [NV-TIER-BUDGET] tier=dsv4p_nv budget 66.0s remaining 1.7s < 5s minimum, breaking
```

## Root Cause

EMPTY_200_FASTBREAK=2 requires budget for 2nd key attempt. Each empty200 takes ~62s (pexec timeout). With BUDGET=66, remaining after 1st key is 3.9-4.5s — below the 5s minimum for a 2nd key attempt. The tier breaks before FASTBREAK=2 can rescue. Result: every empty200 becomes an ATE.

## Fix

NVU_TIER_BUDGET_DSV4P_NV 66→72 (+6s). After a typical ~62s empty200, 72s budget leaves ~10s remaining, enough for the 2nd key to be tried. If NVCF function recovers on the 2nd key, the request is rescued. If not, it fails at the same 72s mark — only 6s slower than before.

## Budget Check

72 << 205 TIER_TIMEOUT_BUDGET_S ✓
dsv4p_nv skips peer-fb (NVU_PEER_FB_SKIP_MODELS=dsv4p_nv) → no peer-fb timeout constraint

## Verification

```bash
ssh -p 222 opc_uname@100.109.153.83 "docker exec nv_gw env | grep NVU_TIER_BUDGET_DSV4P_NV"
# → NVU_TIER_BUDGET_DSV4P_NV=72 ✓
curl -s http://localhost:40006/health
# → {"status": "ok", ...} ✓
```

Single param; iron rule: only change HM1 never HM2.
## ⏳ 轮到HM1优化HM2
