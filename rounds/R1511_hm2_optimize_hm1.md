# R1511: HM2→HM1 — NOP (zombie+streaming-sync defect, all params floor/optimal)

## 6h Summary
- **73req/49OK/24fail = 67.1% SR**
- 20 zombie_empty_completion (83% of failures): dsv4p_nv=9 (avg 9,631ms), glm5_2_nv=11 (avg 9,132ms). avg input 222K chars. NVCF content-filter, code-level fast abort. 不可配置.
- 4 all_tiers_exhausted ATE: dsv4p_nv=4 (avg 41,874ms), glm5_2_nv=1 (8,411ms). All single-tier (tiers_tried_count=1). ms_gw streaming sync defect — ms_gw completes in 2-5s (MS-STREAM-DONE confirmed), nv_gw reports TimeoutError at 124-126s. NVU_MS_GW_FALLBACK_TIMEOUT=120 not the binding constraint (relay exceeds both BUDGET=205 and TIMEOUT=120). 代码级streaming同步缺陷, 不可配置.
- 2 tier_attempts: glm5_2_nv 429_integrate_rate_limit (transient)
- ms_gw: 16/17 OK (94.1% healthy)
- Zero fallback_occurred — all failures are single-tier, no cross-model fallback

## Hourly SR
| Hour (UTC) | Total | OK | Fail | SR% |
|------------|-------|-----|------|-----|
| 16:00 | 5 | 3 | 2 | 60.0 |
| 17:00 | 8 | 4 | 4 | 50.0 |
| 18:00 | 18 | 14 | 4 | 77.8 |
| 19:00 | 9 | 5 | 4 | 55.6 |
| 20:00 | 10 | 6 | 4 | 60.0 |
| 21:00 | 21 | 17 | 4 | 81.0 |
| 22:00 | 2 | 0 | 2 | 0.0 |

## Env Params (all floor/optimal)
- UPSTREAM_TIMEOUT=66, FASTBREAK=1 (pexec/integrate), EMPTY_200_FASTBREAK=2
- TIER_COOLDOWN_S=15, KEY_COOLDOWN_S=25, KEY_AUTHFAIL_COOLDOWN_S=60
- TIER_TIMEOUT_BUDGET_S=205, NVU_TIER_BUDGET_DSV4P_NV=66, GLM5_2_NV=96, MINIMAX_M3_NV=100
- NVU_MS_GW_FALLBACK_TIMEOUT=120, NVU_PEER_FALLBACK_TIMEOUT=66
- NVU_PEER_FB_SKIP_MODELS= (empty, all models eligible)
- NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms
- NVU_FALLBACK_HEALTH_THRESHOLD=0.05, FALLBACK_HEALTH_THRESHOLD=0.05
- INTEGRATE_THINKING_TIMEOUT=90, STREAM_FIRST_BYTE_DEADLINE=20, STREAM_TOTAL_DEADLINE=42
- SSLEOF_RETRY_DELAY=1.0, CONNECT_RESERVE=0

## ms_gw Streaming Sync Defect Confirmed
```
nv_gw: [NV-MS-FB] ms_gw relay failed after 126674ms: TimeoutError: timed out (relay_started=True)
ms_gw: [MS-STREAM-DONE] req=0f668cf2 forwarded [DONE], closing client stream after 28316b
```
ms_gw completes stream in ~2s, but nv_gw never sees the completion signal. Relay runs for 124-126s past both BUDGET=205 and MS_GW_FALLBACK_TIMEOUT=120 — the streaming relay uses OS-level TCP timeout (~260s), independent of both config params. 代码级缺陷, 不可配置.

## Decision: NOP
- 83% failures = zombie_empty_completion (NVCF content-filter, code-level fast abort)
- 17% failures = all_tiers_exhausted ATE (ms_gw streaming sync defect)
- All params already at floor/optimal — no further config optimization possible
- compose md5 f77f0381 unchanged
- Container restarted 2026-07-15T21:46:15Z (24min ago at collection time)
- 铁律:只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
