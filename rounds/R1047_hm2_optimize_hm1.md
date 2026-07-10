# R1047: HM2→HM1 — NOP (false trigger, 100% 6h SR, 0 post-restart errors)

## Trigger
HM1 pushed commit `1840357` (R1046: HM2→HM1 NOP). Script detected HM1 commit, triggered HM2 optimize HM1.

## Data Collection (`2026-07-10 10:40 UTC`)

### 6h Window (since ~04:40 UTC)
| Metric | Value |
|--------|-------|
| Total requests | 35 |
| OK (status=200) | 35 (100.0%) |
| Fail | 0 |
| nv_tier_attempts | 0 rows |
| Upstream types | nv_integrate: 35/35 |
| Avg ttfb | 7,161ms |
| Avg duration | 7,498ms |
| Max duration | 19,894ms |
| Fallback triggered | 0 |

### 24h Window
| Metric | Value |
|--------|-------|
| Total | 634 |
| OK | 588 (92.7%) |
| Fail | 46 |
| dsv4p_nv pexec | 100/100 (100%) |
| dsv4p_nv integrate | 15/15 (100%) |
| dsv4p_nv ATE | 17/17 (all NULL upstream_type) |
| glm5_2_nv integrate | 319/324 (98.5%) |
| glm5_2_nv pexec | 45/45 (100%) |
| glm5_2_nv ATE | 15 |
| kimi_nv pexec | 61/61 (100%) |
| minimax_m3_nv integrate | 32/33 (97.0%) |
| minimax_m3_nv ATE | 7 |

### Container restart: 2026-07-09 03:03 UTC (~31h ago)

### Log Analysis (6h window)
All 35 requests are glm5_2_nv integrate. Round-robin across k1-k5. Two SSLEOFError on k2 (10:03 and 10:34), both SSL-cycled to k3 successfully. Zero NV-TIER-FAIL, zero NV-EMPTY-FASTBREAK, zero ATE in 6h.

### dsv4p_nv ATE Pattern (24h, all >6h ago)
17 ATEs, all NULL upstream_type, ttfb ~679ms, duration ~61s, tiers_tried_count=1, fallback_tiers_used={dsv4p_nv}. Single-key empty_200 → FASTBREAK=2 not honored (R1039 bug confirmed: pexec path logs threshold=1 regardless of env=2). NVU_PEER_FB_SKIP_MODELS omits dsv4p_nv (R1039 workaround still active).

### Active Env (all at optimal/floor)
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=110
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2 (R1031, not honored in pexec per R1039)
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_CONNECT_RESERVE_S=0
MIN_OUTBOUND_INTERVAL_S=0
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=18
NV_INTEGRATE_KEY_COOLDOWN_S=0
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,dsv4p_nv:dsv4p_ms,kimi_nv:kimi_ms
```

## Decision: NOP

6h window: 35/35 OK (100.0%), 0 post-restart errors, 0 nv_tier_attempts rows. All params at optimal/floor. glm5_2_nv integrate 35/35 100% first-attempt integrate. k2 SSLEOFError handled correctly by SSL-cycle mechanism (NVU_SSLEOF_RETRY_DELAY_S=1.0). dsv4p_nv ATE pattern (17 in 24h) is a known code-level bug (R1039: FASTBREAK=2 not honored in pexec path), not config-fixable. No parameters to change.

Zero param; iron rule: only change HM1 never HM2.

## ⏳ 轮到HM1优化HM2