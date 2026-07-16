# R1645: HM2→HM1 — NVU_TIER_BUDGET_DSV4P_NV 72→78 (+6s, ensure 2nd-key rescue above min healthy threshold)

## Data (6h window, HM1 pre-R1645)

| Metric | Value |
|--------|-------|
| Total requests | 17 |
| dsv4p_nv 200 | 7 (58.3%) |
| dsv4p_nv 502 (ATE) | 5 (41.7%) |
| glm5_2_nv 200 | 3 |
| glm5_2_nv zombie | 2 |
| 24h pexec_429 | 90 (24.3%) |
| 24h pexec_SSLEOF | 13 |
| 24h pexec_empty200 | 10 |

## Analysis

R1644 deployed BUDGET=72. Container restarted at 02:12 UTC, only ~3min runtime with zero traffic — no data on R1644 effectiveness yet.

**Pre-R1644 data**: All 5 ATE had `num_attempts=1` — EMPTY_200_FASTBREAK=2 never got to try 2nd key because BUDGET=66 ran out with 1.7-4.5s remaining < 5s minimum.

**R1644 gives 10s for 2nd key**: After 62s empty200, 72s budget leaves ~10s for 2nd key. But minimum healthy dsv4p_nv response from metrics: 13.6s (req 00e2b9f2), 14.1s (fa2ddc2d), 19.2s (0acb429d). 10s < 13.6s minimum → 2nd key rescue still cut off by budget before a healthy response can complete.

**Post-R1643 429 state**: 0 pexec_429 in last 6h — KEY=TIER=60 is working. The 429 cascading is cured.

## Fix

NVU_TIER_BUDGET_DSV4P_NV 72→78 (+6s). After a typical ~62s empty200, 78s budget leaves ~16s for 2nd key attempt — above the 13.6s minimum healthy response time. If NVCF function recovers on the 2nd key, the request can be fully rescued.

## Budget Check

78 << 205 TIER_TIMEOUT_BUDGET_S ✓
dsv4p_nv skips peer-fb (NVU_PEER_FB_SKIP_MODELS=dsv4p_nv) → no peer-fb timeout constraint
KEY_COOLDOWN_S=60, TIER_COOLDOWN_S=60 >> 78 safe

## Verification

```bash
ssh -p 222 opc_uname@100.109.153.83 "docker exec nv_gw env | grep NVU_TIER_BUDGET_DSV4P_NV"
# → NVU_TIER_BUDGET_DSV4P_NV=78 ✓
ssh -p 222 opc_uname@100.109.153.83 "sed -n '646p' /opt/cc-infra/docker-compose.yml"
# → NVU_TIER_BUDGET_DSV4P_NV: "78"  # R1645 ... ✓
curl -s http://localhost:40006/health
# → {"status": "ok", ...} ✓
```

Single param; iron rule: only change HM1 never HM2.
## ⏳ 轮到HM1优化HM2
