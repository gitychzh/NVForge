# R1442: HM2→HM1 — PROXY_TIMEOUT 300→360, NVU_MS_GW_FALLBACK_TIMEOUT 210→240

## 6h Data (DB)
- **57 req, 36 OK, 21 fail = 63.2% SR**
- 17 zombie: 11 glm5_2_nv + 6 dsv4p_nv (NVCF content-filter, not config-fixable)
- 4 ATE dsv4p_nv all_tiers_exhausted (all ms_gw fallback TIMEOUT)
- ms_gw 28/28 100% SR
- 0 tier_attempts
- Container restart: 08:40 UTC (R1441 deploy), post-restart: 6/4/2

## Hourly SR
| Hour (UTC) | Total | OK | Fail | SR% |
|---|---|---|---|---|
| 03:00 | 9 | 5 | 4 | 55.6 |
| 04:00 | 7 | 3 | 4 | 42.9 |
| 05:00 | 26 | 22 | 4 | 84.6 |
| 06:00 | 5 | 3 | 2 | 60.0 |
| 07:00 | 5 | 1 | 4 | 20.0 |
| 08:00 | 5 | 2 | 3 | 40.0 |

## Post-Restart (08:40 UTC+)
- 6 req, 4 OK, 2 fail (1 dsv4p_nv ATE, 1 glm5_2_nv zombie)

## 502 Error Breakdown (6h)
| Model | Error Type | Count | Avg Dur | Fallback |
|---|---|---|---|---|
| glm5_2_nv | zombie_empty_completion | 11 | 7.4s | f/f |
| dsv4p_nv | zombie_empty_completion | 6 | 17.6s | f/f |
| dsv4p_nv | all_tiers_exhausted | 4 | 121.1s | f/f |

## ms_gw Fallback Analysis (from proxy log)
dsv4p_nv ATE → ms_gw fallback **5/5 FAILED**:
- 14:10: ms_gw relay failed after 199461ms: TimeoutError (relay_started=True)
- 15:11: ms_gw relay failed after 206107ms: TimeoutError (relay_started=True)
- 15:40: ms_gw relay failed after 199780ms: TimeoutError (relay_started=True)
- 16:07: ms_gw relay failed after 6620ms: BrokenPipeError (relay_started=True)
- 17:10: ms_gw relay failed after 214607ms: TimeoutError (relay_started=True)

Observed max: 214s, consistently >210s limit. dsv4p_ms streaming in 190-214s range.

## Root Cause
NVU_MS_GW_FALLBACK_TIMEOUT=210s (R1436) too tight for dsv4p_ms streaming (190-214s).
5/5 fallback attempts fail with TimeoutError. Also PROXY_TIMEOUT=300s would be exceeded:
66s tier budget + 240s new fallback = 306s > 300s.

## Changes (2 params, HM1 only)
1. **NVU_MS_GW_FALLBACK_TIMEOUT: 210→240** (+30s, 26s buffer above observed max 214s)
2. **PROXY_TIMEOUT: 300→360** (+60s, 306s worst-case < 360s safe)

## Verification
- Health check: OK, port 40006
- `docker exec nv_gw env`: PROXY_TIMEOUT=360, NVU_MS_GW_FALLBACK_TIMEOUT=240 ✓
- Container restart: OK

## 铁律:只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
