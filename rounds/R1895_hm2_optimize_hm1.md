# R1895 (HM2→HM1): UPSTREAM_TIMEOUT 38→36 (-2s), cut zombie waste ceiling

## Data (6h window, HM1 nv_gw)

| Metric | Value |
|---|---|
| Total requests | 48 |
| OK (200) | 24 |
| Fail (502) | 24 |
| SR | 50.0% |
| Error type | 24 zombie_empty_completion (100%) |
| glm5_2_nv | 39 req, 43.6% SR, avg 5916ms, max 15650ms |
| dsv4p_nv | 9 req, 77.8% SR, avg 11400ms, max 33734ms |
| Peer-fallback | 0 triggered |
| Tier errors | 2 pexec_429 + 1 pexec_SSLEOFError (all glm5_2) |

## Analysis

All 24 failures are zombie_empty_completion — NVCF function-level degradation returning empty 200 responses. EMPTY_200_FASTBREAK=1 handles the zombie detection path. The gateway does NOT trigger fallback for zombie (stream-level error, not tier-level ATE). No config fix for NVCF degradation.

## Change

**UPSTREAM_TIMEOUT: 38→36 (-2s)**

- OK max: dsv4p_nv 33.7s < 36s (2.3s margin)
- glm5_2_nv OK max: 15.6s << 36s
- Saves 2s per zombie failure path
- Budget: UPSTREAM=36 + PEER=122 = 158 << 178 TIER_TIMEOUT_BUDGET ✓
- Single parameter; iron law: only change HM1 never HM2

## Verification

- ✓ compose updated: UPSTREAM_TIMEOUT="36"
- ✓ container restarted: `docker compose up -d nv_gw`
- ✓ env confirms: `UPSTREAM_TIMEOUT=36`
- ✓ health check: `{"status": "ok", ...}`

## ⏳ 轮到HM1优化HM2
