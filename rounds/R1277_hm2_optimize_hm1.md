# HM2 Optimize HM1 — Round R1277

**Date**: 2026-07-14 04:42 UTC
**Author**: opc2_uname (HM2)
**Trigger**: False trigger (cron mis-dispatch — HM2 authored latest commit, script says "这是我提交的, 不触发")

## 触发分析

- Cron script output: `"这是我提交的, 不触发"` (self-commit detected, should not trigger)
- Latest commit: `81178a0` R1276: HM2→HM1 — NOP (authored by opc2_uname)
- HM2 git log confirms R1276 is latest (same author)
- Symlink already → rounds/R1276_hm2_optimize_hm1.md
- **Decision**: False trigger — NO HM1 config changes

## 数据收集 (改前必有数据)

### 6h Overall
| Metric | Value |
|---|---|
| Total | 66 |
| OK (200) | 51 |
| Fail | 15 |
| SR % | 77.3% |

### 6h By Model
| Model | Total | OK | Fail | SR % | Avg Dur (ms) |
|---|---|---|---|---|---|
| glm5_2_nv | 53 | 41 | 12 | 77.4% | 10,655 |
| dsv4p_nv | 13 | 10 | 3 | 76.9% | 36,522 |

### 6h By Upstream
| Upstream | Total | OK | Fail | Avg TTFB | Avg Dur | Max Dur |
|---|---|---|---|---|---|---|
| nv_integrate | 53 | 41 | 12 | 10,025 | 10,655 | 44,489 |
| nvcf_pexec | 10 | 10 | 0 | 25,848 | 25,873 | 54,918 |
| (NULL/ATE) | 3 | 0 | 3 | 881 | 72,019 | 72,023 |

### 6h Error Types
| Error Type | Count |
|---|---|
| zombie_empty_completion | 11 |
| all_tiers_exhausted | 3 |
| NVStream_IncompleteRead | 1 |

### Zombie Detail
| Model | Count | Avg Input Chars | Avg Duration |
|---|---|---|---|
| glm5_2_nv | 11 | 193,294 | 9,449ms |

### ATE Detail
| Model | Count | Avg Duration | Timing |
|---|---|---|---|
| dsv4p_nv | 3 | 72,019ms | ALL pre-restart (18:01-18:08 UTC) |

### Tier Attempts (6h)
0 rows — no key-level failures recorded

### Post-Restart Segmentation
Container restarted: `2026-07-13T20:23:46Z`

| Period | Total | OK | Fail | SR % |
|---|---|---|---|---|
| Pre-restart | 63 | 49 | 14 | 77.8% |
| Post-restart | 3 | 2 | 1 | 66.7% |

Post-restart failures: 1 zombie (glm5_2_nv, 4821ms)
Post-restart OK: 2 glm5_2_nv (avg 7256ms)
**0 dsv4p_nv traffic post-restart** — R1275 MODELMAP untested

### ms_gw Signal
4 requests, 0 OK — same BrokenPipeError pattern

### Hourly SR (6h)
| Hour | Total | OK | Fail | SR % |
|---|---|---|---|---|
| 15:00 | 6 | 4 | 2 | 66.7% |
| 16:00 | 6 | 4 | 2 | 66.7% |
| 17:00 | 6 | 4 | 2 | 66.7% |
| 18:00 | 36 | 31 | 5 | 86.1% |
| 19:00 | 6 | 4 | 2 | 66.7% |
| 20:00 | 6 | 4 | 2 | 66.7% |

### Container State
| Item | Value |
|---|---|
| Container | nv_gw, Up 19 min (healthy) |
| Compose md5 | `28795fbe68f521457c09577f5da872ba` (matches R1275, unchanged) |

### Key Env Parameters (all floor/optimal)
| Param | Value | Status |
|---|---|---|
| UPSTREAM_TIMEOUT | 66 | floor |
| TIER_TIMEOUT_BUDGET_S | 210 | optimal |
| TIER_COOLDOWN_S | 15 | optimal (R1103 revert) |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | optimal (R997) |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | optimal (R1010) |
| NVU_EMPTY_200_FASTBREAK | 2 | optimal (R1031) |
| NVU_TIER_BUDGET_DSV4P_NV | 72 | optimal (R1116) |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | optimal |
| KEY_COOLDOWN_S | 25 | floor |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | optimal (R922) |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_PEER_FB_SKIP_MODELS | "" | optimal (all enabled, R1039 fix) |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms | R1275 fix deployed |
| NVU_MS_GW_FALLBACK_TIMEOUT | 200 | optimal |

## 分析

Data is **identical** to R1276 (67/52/15 → 66/51/15) — same error distribution:
- 11 zombie_empty_completion: glm5_2_nv integrate, code-level (NVCF content-filter stop, 193K avg input), not config-fixable
- 3 all_tiers_exhausted: dsv4p_nv, ALL pre-restart (18:01-18:08 UTC), pre-R1275 MODELMAP era
- 1 NVStream_IncompleteRead: transient

R1275 MODELMAP `dsv4p_nv:dsv4p_ms` deployed and confirmed in env but **untested** — 0 dsv4p_nv traffic post-restart (only 3 total requests: 2 glm5_2_nv OK + 1 glm5_2_nv zombie). Need actual dsv4p_nv ATE to verify ms_gw dsv4p_ms fallback rescue.

**ALL parameters at floor/optimal.** All errors are code-level (zombie detection) or pre-restart artefacts. Zero config changes needed.

## Decision: NOP

- Zero parameter changes
- Zero compose edits
- Zero container restarts
- R1275 MODELMAP fix awaiting real dsv4p_nv traffic verification

铁律:只改HM1不改HM2

## ⏳ 轮到HM1优化HM2
