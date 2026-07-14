# HM2 Optimize HM1 — Round R1306

**Date**: 2026-07-14 01:26 UTC
**Trigger**: False trigger (double-dispatch, 20th consecutive post-R1286)
**Pre-run script output**: `"这是我提交的, 不触发"` — HM2 self-commit, cron mis-dispatch
**HM1 git**: R1206 (100 rounds behind HM2)
**Author**: opc2_uname (HM2)

## 触发分析

Cron dispatched with contradictory signals: script output says `"这是我提交的, 不触发"` but dispatch message claims "HM1提交了新commit". Cross-reference confirms false trigger:
- HM2 latest commit `3d1cdbf` = R1305 NOP (pre-run script self-committed)
- HM1 git log stuck at R1206 (100 rounds behind)
- Symlink `RN_hm2_optimize_hm1.md` → `rounds/R1305_hm2_optimize_hm1.md` (already correct)
- R1305 round file already committed and pushed by pre-run script
→ Double-dispatch: agent creates R1306 as continuation NOP

## 数据收集 (改前必有数据)

### Container Status
- nv_gw: `Up 3 hours (healthy)`, restarted `2026-07-13T22:14:51Z`
- Compose md5: `6e1b58bc70eca49e500e3034b08376d9` (stable since R1286 container restart)

### nv_gw Env (HM1 live)
```
UPSTREAM_TIMEOUT=66
TIER_COOLDOWN_S=15
KEY_COOLDOWN_S=25
KEY_AUTHFAIL_COOLDOWN_S=60
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_TIER_BUDGET_DSV4P_NV=72
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_MS_GW_FALLBACK_TIMEOUT=195
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_PEER_FB_SKIP_MODELS=
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms
```
All params at floor/optimal. Zero config change space.

### nv_gw Logs (tail 100 grep error/warn/zombie/TIER-FAIL)
```
0 NV-ZOMBIE (log grep: 0)
0 NV-TIER-FAIL
0 NV-EMPTY-FASTBREAK
0 NV-MS-FB
All NV-REQ: glm5_2_nv integrate, no fallback, healthy streaming
```

### DB — 6h Overall (nv_requests)
| total | ok | err | sr_pct |
|-------|----|-----|--------|
| 60    | 51 | 9   | 85.0%  |

### DB — Post-Restart Segmentation (restart=2026-07-13 22:14 UTC)
| period | total | ok | fail | sr_pct |
|--------|-------|----|------|--------|
| post-restart | 42 | 39 | 3 | **92.9%** |
| pre-restart | 18 | 12 | 6 | 66.7% |

### DB — Post-Restart Hourly SR
| hour | total | ok | fail | sr_pct |
|------|-------|----|------|--------|
| 22:00 | 4 | 3 | 1 | 75.0% |
| 23:00 | 6 | 5 | 1 | 83.3% |
| 00:00 | 6 | 5 | 1 | 83.3% |
| 01:00 | 26 | 26 | 0 | **100.0%** |

### DB — Error Type (6h)
| error_type | cnt |
|------------|-----|
| zombie_empty_completion | 9 |

All 9 zombie = glm5_2_nv integrate, NVCF content-filter stop. Avg input 217K chars, avg detection ~4.9s. 3 post-restart (22:33, 23:33, 00:03 UTC), 6 pre-restart.

### DB — Tier Attempts (6h)
0 rows. Zero tier-level errors, zero key cycling, zero 429s.

### DB — Fallback (6h)
0 fallback triggers. All 60 requests glm5_2_nv integrate direct.

### DB — ms_gw Signal (6h)
| total | ok |
|-------|----|
| 13    | 13 | **100% SR**

### ms_gw Logs
All MS-OK-STREAM + MS-STREAM-DONE, ZHIPUAI/GLM-5.2 backend healthy, no errors.

### DB — Last Hour (01:00 UTC)
| total | ok | sr_pct |
|-------|----|--------|
| 29    | 29 | **100.0%** |

### Recent 10 Requests
All glm5_2_nv integrate 200 OK, ttfb 5-51s, duration 7.5-50.5s, input 150K-173K chars. No errors, no fallback, 0 key_cycle_429s.

## 优化决策: NOP

**Zombie-only failure pattern (9/9 zombie_empty_completion):**
- All failures = NVCF content-filter → empty response + forced stop → gateway detects zombie → returns 502 in ~3-5s
- NOT config-fixable — NVCF-side content moderation, gateway detection is correct
- Post-restart: only 3 zombies in 3 hours, last hour **100% SR (29/29)**
- 0 ATE (all_tiers_exhausted), 0 IncompleteRead, 0 tier_attempts, 0 key_cycle_429s
- 0 fallback triggers, ms_gw 100% SR (13/13) healthy standby
- All nv_gw params at floor/optimal — no further reduction possible

**No parameter changes.** Every parameter is at its validated floor:
- UPSTREAM_TIMEOUT=66 (floor)
- TIER_COOLDOWN_S=15 (R1103 revert, floor)
- KEY_COOLDOWN_S=25 (floor)
- FASTBREAK triple: 1/1/2 (all at optimal — function-level signals=1, empty_200 key-specific tolerance=2)
- Per-tier budgets: dsv4p=72, glm5_2=96, minimax=100 (all validated)
- ms_gw fallback timeout=195 (optimal), health threshold=0.05 (floor)

**Zombie_empty_completion is NVCF content-filter — no config change can reduce it.** The gateway correctly detects forced-stop+empty-chunk and returns 502 quickly (~3-5s) vs old 96s hang.

## ⚠️ 铁律: 只改HM1不改HM2

本回合未修改任何配置 — NOP.
## ⏳ 轮到HM1优化HM2
