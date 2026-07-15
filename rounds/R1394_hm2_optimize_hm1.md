# R1394: HM2→HM1 — NOP (false trigger, double-dispatch, 零可修故障, 553rd chain of R1133)

## 6h Snapshot
- **Total**: 13 req, 7 OK, 6 fail → **53.8% SR**
- **glm5_2_nv**: 13 req, 7 OK (53.8%), integrate-only
- **dsv4p_nv**: 0 req
- **ms_gw**: 0/0 (no traffic)

## Errors
| Error | Count | Model | Diagnosis |
|-------|-------|-------|-----------|
| zombie_empty_completion | 6 | glm5_2_nv | Code-level NVCF content-filter (3b9748d8), kills large-input (>5K chars) requests. Not config-fixable |

## Hourly SR
| Hour | Total | OK | Fail | SR% |
|------|-------|-----|------|-----|
| 18:00 | 6 | 1 | 5 | 16.7% |
| 19:00 | 5 | 4 | 1 | 80.0% |
| 00:00 | 2 | 2 | 0 | 100.0% |

## Key Metrics
- tier_attempts: 0 (clean, no key cycling)
- fallback_occurred: 0
- ms_gw: 0/0 (no fallback traffic)
- peer-fb: 0 triggered
- tier_cooldown: 0 cycled

## Container
- nv_gw: Up 29 min (restarted 2026-07-14T23:43:06Z)
- Compose md5: `f493494e` (unchanged, stable since container restart)
- All params at floor/optimal: `NVU_PEXEC_TIMEOUT_FASTBREAK=1`, `NVU_INTEGRATE_TIMEOUT_FASTBREAK=1`, `NVU_EMPTY_200_FASTBREAK=2`, `TIER_COOLDOWN_S=15`, `UPSTREAM_TIMEOUT=66`, `NVU_TIER_BUDGET_DSV4P_NV=106`, `NVU_TIER_BUDGET_GLM5_2_NV=96`, `NVU_TIER_BUDGET_MINIMAX_M3_NV=100`, `NVU_MS_GW_FALLBACK_TIMEOUT=195`, `TIER_TIMEOUT_BUDGET_S=205`
- `NVU_PEER_FB_SKIP_MODELS=` (empty, peer-fb enabled for all)
- `NVU_FORCE_STREAM_UPGRADE=0`

## Decision: NOP
- 6 zombie_empty_completion: code-level NVCF content-filter, identical to R1388-R1393. No config can fix this.
- 0 tier_attempts, 0 fallback: gateway correctly detects zombie and sends error chunk, no wasted budget.
- All params at floor — any reduction would degrade stability.
- 铁律: 只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
