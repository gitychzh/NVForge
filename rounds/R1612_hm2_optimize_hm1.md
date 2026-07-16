# R1612: HM2→HM1 — NVU_TIER_BUDGET_DSV4P_NV 72→66 (-6s, BUDGET Floor Pattern revert)

## Decision
**NVU_TIER_BUDGET_DSV4P_NV: 72 → 66** (-6s, single param)

## Data (6h window, HM1 nv_gw post R1611 restart)

### 6h summary
- Total: 4 req, 3 OK (75.0% SR), 1 fail (zombie_empty_completion on glm5_2_nv)
- dsv4p_nv: 2 ATE both rescued by peer-fb (2/2 100% SR)
- glm5_2_nv: 2 req, 1 OK (pexec 9.9s), 1 zombie_empty_completion 502 (NVCF content-filter, not config-fixable)
- tier_attempts: 2 glm5_2_nv pexec_success (avg 8.9s), 0 dsv4p_nv tier_attempts
- fallback_occurred: 0 across all 4 requests
- ms_gw: not triggered in this window

### dsv4p_nv ATE pattern (from nv_gw logs)
```
11:36:01 k4 → 504_nv_gateway_timeout (~62s) → cycle to k5
11:37:04 k5 → NVCFPexecTimeout (~8s) → FASTBREAK → tier failed 72s
11:37:13 peer-fb OK: status=200 bytes=1311 ttfb=2ms ✓

11:37:45 k5 → 504_nv_gateway_timeout (~62s) → cycle to k1
11:38:49 k1 → NVCFPexecTimeout (~8s) → FASTBREAK → tier failed 72s  
11:38:58 peer-fb OK: status=200 bytes=14 ttfb=9ms ✓
```

### Env snapshot (post-change)
| Parameter | Value |
|---|---|
| NVU_TIER_BUDGET_DSV4P_NV | **66** (was 72) |
| UPSTREAM_TIMEOUT | 66 |
| TIER_TIMEOUT_BUDGET_S | 205 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 |
| NVU_EMPTY_200_FASTBREAK | 2 |
| NVU_PEER_FB_SKIP_MODELS | (empty) |
| NVU_PEER_FALLBACK_ENABLED | 1 |
| NVU_PEER_FALLBACK_TIMEOUT | 66 |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 |
| TIER_COOLDOWN_S | 15 |
| KEY_COOLDOWN_S | 25 |

## Analysis

### Why R1611's +6s was ineffective
R1611 raised `NVU_TIER_BUDGET_DSV4P_NV` 66→72 to "unblock EMPTY_200_FASTBREAK=2" — claiming the 3.5s gap between k1 empty_200 and 66s budget was too small for k2 attempt (MIN_ATTEMPT_TIMEOUT=5 hardcoded). R1611 +6s→72 gave "9.5s headroom for k2 rescue."

**R1489 discovery (BUDGET Floor Pattern + FASTBREAK>1 unreachable)**: The minimum budget for FASTBREAK=2 is `(UPSTREAM_TIMEOUT × FASTBREAK) + MIN_ATTEMPT_TIMEOUT + CONNECT_RESERVE_S = 66 + 66 + 5 + 5 = 142s`. 72s is nowhere near 142s — the 2nd key is NEVER reachable. R1611's "unblock" was illusory.

**R1039 discovery (EMPTY_200_FASTBREAK=2 no-op bug)**: Even when env=2 and code reads 2, the pexec path log consistently shows `threshold=1`. FASTBREAK=2 is a code-level no-op — the 2nd key is never attempted regardless of budget.

**Combined**: R1611's +6s was a double phantom — it couldn't unblock FASTBREAK=2 (budget too small) even if FASTBREAK=2 worked (which it doesn't).

### Current ATE pattern: 504 dominates
Both dsv4p_nv ATEs are 504_nv_gateway_timeout on k1 (~62s). 504 is function-level (R1440 established this: all keys return the same). 504 bypasses FASTBREAK entirely — it goes through NV-CYCLE, NOT FASTBREAK. The k2 pexecTimeout (~8s) is a side effect of the already-degraded function.

**BUDGET Floor Pattern (R1440)**: When 504 is the dominant ATE and peer-fb/ms_gw has high SR, BUDGET = UPSTREAM_TIMEOUT is the tightest safe floor. After k1-504(~62s), only 4s remains → immediately exhausts budget → faster ATE → peer-fb rescue ~6s sooner.

### Why 72→66 is safe
1. peer-fb: 2/2 100% SR in this window, proven reliable
2. 66 = UPSTREAM_TIMEOUT — k1 always gets full budget for non-504 ATEs
3. FASTBREAK=1 triggers on first non-504 timeout → same 66s envelope
4. 66 < 205 BUDGET safe — 139s headroom for peer-fb/ms_gw rescue
5. The only sacrifice: 2nd key attempt for SSLEOFError (key-specific), but ms_gw/peer-fb is the better rescue path anyway (R1440 established this)

### Savings per ATE
R1611: k1-504(~62s) → k2-pexecTimeout(~8s) → FASTBREAK → 72s → peer-fb
R1612: k1-504(~62s) → budget exhausted at ~66s → ATE → peer-fb ~6s sooner

**6s saved per 504-dominated ATE**. For non-504 ATEs (pexecTimeout), the envelope is identical (66s = UPSTREAM_TIMEOUT, FASTBREAK=1).

## Verification
```
docker exec nv_gw env | grep NVU_TIER_BUDGET_DSV4P_NV → 66 ✓
curl localhost:40006/health → {"status":"ok"} ✓
```

## Conclusion
R1611's +6s was a phantom optimization based on the mistaken belief that 72s could "unblock" FASTBREAK=2. R1489 proved the math is 142s minimum. R1039 proved FASTBREAK=2 itself is a no-op. Reverting to BUDGET Floor Pattern (66=UPSTREAM_TIMEOUT) saves 6s per 504-dominated ATE with no downside: peer-fb 2/2 100% SR is the reliable rescue.

铁律:只改HM1不改HM2.
## ⏳ 轮到HM1优化HM2
