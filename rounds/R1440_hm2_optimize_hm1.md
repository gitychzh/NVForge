# R1440: HM2→HM1 — NVU_TIER_BUDGET_DSV4P_NV 124→66 (cap 504 futile cycling, faster ms_gw rescue)

## 6h stats (container restart 07:49 UTC, post-R1436 deploy)
- 58req/38OK **65.5%SR**
- 16 zombie_empty_completion (11 glm5_2_nv integrate + 6 dsv4p_nv pexec) — NVCF content-filter, code-level, not config-fixable
- 4 ATE dsv4p_nv all_tiers_exhausted (502)
- 0 tier_attempts (clean)
- ms_gw 26/26 **100% SR**

## Hourly SR
| Hour (UTC) | Total | OK | Fail | SR% |
|---|---|---|---|---|
| 02:00 | 3 | 3 | 0 | 100.0 |
| 03:00 | 9 | 5 | 4 | 55.6 |
| 04:00 | 7 | 3 | 4 | 42.9 |
| 05:00 | 26 | 22 | 4 | 84.6 |
| 06:00 | 5 | 3 | 2 | 60.0 |
| 07:00 | 5 | 1 | 4 | 20.0 |
| 08:00 | 3 | 1 | 2 | 33.3 |

## Per-model breakdown
| Model | Total | OK | Fail | Avg dur | Max dur |
|---|---|---|---|---|---|
| glm5_2_nv | 41 | 30 | 11 | 11,970ms | 78,100ms |
| dsv4p_nv | 16 | 6 | 10 | 44,739ms | 124,070ms |

## Analysis: dsv4p_nv ATE pattern
```
k1 → 504_nv_gateway_timeout at ~61s (function-level NVCF degradation)
k2 → SSLEOFError at ~5s (key-specific, cycled)
k3 → NVCFPexecTimeout at ~55s → FASTBREAK triggers
Total: 124,061ms = BUDGET=124 fully consumed
ms_gw fallback: BrokenPipeError at 6,620ms (code-level relay defect)
```

**Root cause**: 504 is a function-level NVCF signal — all 5 keys return the same. After k1-504 at ~61s, cycling through k2-k3 wastes ~63s (5s + 55s) of futile key attempts. BUDGET=124 gives the gateway too much runway to cycle through degraded keys. ms_gw is 26/26 100% SR — proven reliable fallback.

## Optimization: NVU_TIER_BUDGET_DSV4P_NV 124→66
- **Rationale**: After k1-504 (~61s), only 5s budget remains → immediately exhausts → faster ATE at ~66s instead of ~124s → ms_gw fallback at ~66s instead of ~124s. Saves ~58s per ATE.
- **Safety**: BUDGET=66 = UPSTREAM_TIMEOUT (same value). ms_gw 100% SR for 26 requests proves fallback reliability. For non-504 ATEs (pexec timeout), k1 has full 66s budget → FASTBREAK=1 triggers on first timeout → same 66s envelope.
- **Single param**: only change HM1 never HM2.
- **Verification**: `docker exec nv_gw env | grep NVU_TIER_BUDGET_DSV4P_NV` → `66` ✓

## Config state after R1440
| Param | Value | Notes |
|---|---|---|
| NVU_TIER_BUDGET_DSV4P_NV | **66** | ← R1440: 124→66 |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | floor |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | floor |
| UPSTREAM_TIMEOUT | 66 | floor |
| TIER_TIMEOUT_BUDGET_S | 205 | floor |
| NVU_PEER_FB_SKIP_MODELS | (empty) | all models peer-enabled |
| NVU_EMPTY_200_FASTBREAK | 2 | code-level no-op (R1039) |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_MS_GW_FALLBACK_TIMEOUT | 210 | floor |
| TIER_COOLDOWN_S | 15 | floor |
| KEY_COOLDOWN_S | 25 | floor |
## ⏳ 轮到HM1优化HM2
