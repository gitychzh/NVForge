# R1441: HM2→HM1 — NOP (R1440 just deployed, zero post-restart traffic)

**Timestamp**: 2026-07-15 16:50 UTC
**Author**: opc2_uname (HM2)
**Rule**: 铁律:只改HM1不改HM2

## Round Type: NOP (No Operation)

R1440 (NVU_TIER_BUDGET_DSV4P_NV 124→66) was deployed at 08:40 UTC container restart.
Zero post-restart traffic — no validation data exists for R1440's BUDGET=66 config.
All 6h window data is pre-R1440. No config changes warranted.

## 6h Data (02:40–08:40 UTC, all pre-R1440)

### Overall
- 57 req, 36 OK, 21 fail → 63.2% SR
- ms_gw: 28/28 100% SR (reliable fallback)
- 0 tier_attempts (clean key pool)

### dsv4p_nv: 16 req, 6 OK → 37.5% SR
| Error | Count | Avg Dur |
|---|---|---|
| zombie_empty_completion | 6 | 17,574ms |
| all_tiers_exhausted | 4 | 121,060ms |

- 4 ATE @~124s: pre-R1440 (BUDGET=124). R1440 fixes this.
- 6 zombie: NVCF content-filter, not config-fixable.

### glm5_2_nv: 41 req, 30 OK → 73.2% SR
| Status | Error | Count | Avg Dur |
|---|---|---|---|
| 200 | (success) | 18 | 8,462ms |
| 200 | all_tiers_exhausted (tier-fb rescued) | 12 | 21,391ms |
| 502 | zombie_empty_completion | 11 | 7,432ms |

- 11 zombie: NVCF content-filter, not config-fixable (integrate path).
- 12 ATE→200: tier fallback chain rescued (glm5_2_nv integrate fails → pexec succeeds, or vice versa).
  All 12 have `fallback_occurred=t` — surviving via tier hierarchy.

### Hourly SR
| Hour (UTC) | Total | OK | Fail | SR% |
|---|---|---|---|---|
| 03:00 | 9 | 5 | 4 | 55.6 |
| 04:00 | 7 | 3 | 4 | 42.9 |
| 05:00 | 26 | 22 | 4 | 84.6 |
| 06:00 | 5 | 3 | 2 | 60.0 |
| 07:00 | 5 | 1 | 4 | 20.0 |
| 08:00 | 5 | 2 | 3 | 40.0 |

## Container State
- Restarted: 2026-07-15 08:40:46 UTC (R1440 deploy)
- Uptime: ~8h, zero traffic
- Memory: VmRSS=26MB, Threads=2
- Health: {"status":"ok"}

## Env Snapshot (post-R1440, confirmed)
```
NVU_TIER_BUDGET_DSV4P_NV=66      ← R1440
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
TIER_TIMEOUT_BUDGET_S=205
UPSTREAM_TIMEOUT=66
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_MS_GW_FALLBACK_TIMEOUT=210
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_PEER_FB_SKIP_MODELS=
NVU_STREAM_FIRST_BYTE_DEADLINE_S=20
NVU_STREAM_TOTAL_DEADLINE_S=42
TIER_COOLDOWN_S=15
KEY_COOLDOWN_S=25
MIN_OUTBOUND_INTERVAL_S=0
```

## Analysis
- **17 zombie_empty_completion**: NVCF returns HTTP 200 with Content-Length:0. NVCF content-filter, not config-fixable. Affects both dsv4p_nv (pexec) and glm5_2_nv (integrate). Gateway correctly detects and marks as zombie.
- **4 dsv4p_nv ATE @~124s**: Pre-R1440 (BUDGET=124). R1440 reduces BUDGET to 66, which should cut the futile k2-k3 cycling after k1-504 and get ms_gw rescue ~58s faster.
- **12 glm5_2_nv ATE→200**: Tier fallback chain working — glm5_2_nv integrate fails → pexec succeeds. All rescued internally. Good.
- **ms_gw 28/28 100% SR**: Proven reliable. R1440's BUDGET=66 floor pattern relies on this.
- **Zero post-R1440 traffic**: No validation possible. Need to wait for next data window.

## Decision: NOP
- R1440 just deployed, zero validation data.
- All current failures are pre-R1440 or NVCF content-filter.
- All config params at optimal/floor values.
- No parameter change warranted.

## ⏳ 轮到HM1优化HM2