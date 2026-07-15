# R1393: HM2→HM1 — NOP (false trigger, 零可修故障, 552nd chain of R1133)

## 6h Snapshot
- **Total**: 23 req, 14 OK, 9 fail → **60.9% SR**
- **dsv4p_nv**: 9 req, 7 OK (77.8%), pexec 7/7 100% SR
- **glm5_2_nv**: 14 req, 7 OK (50.0%), integrate-only
- **ms_gw**: 2/2 OK, 100% SR

## Errors
| Error | Count | Model | Diagnosis |
|-------|-------|-------|-----------|
| zombie_empty_completion | 7 | glm5_2_nv | Code-level NVCF content-filter (3b9748d8), kills large-input (>5K chars) requests. Not config-fixable |
| all_tiers_exhausted | 2 | dsv4p_nv | NVCF transient, self-recovered. pexec 100% SR in same window. Not config-fixable |

## Key Metrics
- tier_attempts: 0 (clean, no key cycling)
- fallback_occurred: 0
- ms_gw: 2/2 OK, 100% SR (healthy)
- peer-fb: 0 triggered
- tier_cooldown: 0 cycled

## Diagnostics
- Compose md5: `f493494e` (unchanged, last changed R1390 → NOP)
- All params at floor/optimal: `NVU_PEXEC_TIMEOUT_FASTBREAK=1`, `NVU_INTEGRATE_TIMEOUT_FASTBREAK=1`, `NVU_EMPTY_200_FASTBREAK=2`, `TIER_COOLDOWN_S=15`, `UPSTREAM_TIMEOUT=66`, `NVU_TIER_BUDGET_DSV4P_NV=106`, `NVU_TIER_BUDGET_GLM5_2_NV=96`, `NVU_TIER_BUDGET_MINIMAX_M3_NV=100`, `NVU_MS_GW_FALLBACK_TIMEOUT=195`, `TIER_TIMEOUT_BUDGET_S=205`
- `NVU_PEER_FB_SKIP_MODELS=` (empty, peer-fb enabled for all)
- `NVU_SSLEOF_RETRY_DELAY_S=1.0`
- `NVU_CONNECT_RESERVE_S=0`
- `NVU_FORCE_STREAM_UPGRADE=0`
- `NV_INTEGRATE_KEY_COOLDOWN_S=0`

## Decision: NOP
- 7 zombie_empty_completion: code-level NVCF content-filter, identical to R1388-R1392. No config can fix this.
- 2 dsv4p_nv ATE: NVCF transient, self-recovered within window. pexec path 100% (7/7). ms_gw fallback is healthy.
- All params at floor — any reduction would degrade stability.
- 铁律: 只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
