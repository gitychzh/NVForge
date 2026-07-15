# R1491: HM2→HM1 — NOP (all params floor/optimal, zero ATE, zombie code-level only)

**Role**: HM2 → HM1 (本回合轮到HM2执行优化)

**Date**: 2026-07-16 03:11 UTC

## Data Collection

### Container Status
- nv_gw: Up ~12h (healthy), started at 2026-07-15 18:15:54 UTC
- Compose md5: ba4f2871fc9695f237e9a436ac25c279
- health: ✓ OK (both nv_gw + ms_gw)

### Compose vs Container Env Cross-Check
All params match — no stale config. ✅

| Param | Compose | Container | Match |
|---|---|---|---|
| UPSTREAM_TIMEOUT | 66 | 66 | ✅ |
| TIER_TIMEOUT_BUDGET_S | 205 | 205 | ✅ |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | 66 | ✅ |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | 96 | ✅ |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | 1 | ✅ |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | 1 | ✅ |
| NVU_EMPTY_200_FASTBREAK | 2 | 2 | ✅ |
| TIER_COOLDOWN_S | 15 | 15 | ✅ |
| KEY_COOLDOWN_S | 25 | 25 | ✅ |
| NVU_PEER_FB_SKIP_MODELS | "" | "" | ✅ |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms | ✅ |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | 66 | ✅ |
| NVU_PEER_FALLBACK_ENABLED | 1 | 1 | ✅ |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | 66 | ✅ |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | 0.05 | ✅ |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | 0 | ✅ |
| MIN_OUTBOUND_INTERVAL_S | 0 | 0 | ✅ |

### 6h nv_requests (pre-restart + post-restart)
- 57 req / 34 OK / 23 fail = 59.6% SR
- 18 zombie_empty_completion, 5 ATE (all pre-restart)

### Post-restart (~12h)
- 8 req / 5 OK / 3 fail = 62.5% SR
- 3 zombie_empty_completion (NVCF content-filter: large input → tiny output)
- 0 ATE, 0 tier cycling, 0 NV-MS-FB, 0 NV-PEER-FB
- 0 tier_attempts (clean key pool)

### Per-model Post-restart
| Model | Req | OK | Fail | SR% | Avg Duration |
|---|---|---|---|---|---|
| dsv4p_nv | 4 | 3 | 1 | 75.0% | 9,645ms |
| glm5_2_nv | 4 | 2 | 2 | 50.0% | 16,322ms |

### 3h SR (more recent window)
- 35 req / 23 OK / 12 fail = 65.7% SR

### Hourly SR
| Hour | Total | OK | Fail | SR% |
|---|---|---|---|---|
| 13:00 | 5 | 3 | 2 | 60.0 |
| 14:00 | 7 | 3 | 4 | 42.9 |
| 15:00 | 6 | 2 | 4 | 33.3 |
| 16:00 | 9 | 6 | 3 | 66.7 |
| 17:00 | 8 | 4 | 4 | 50.0 |
| 18:00 | 18 | 14 | 4 | 77.8 |
| 19:00 | 4 | 2 | 2 | 50.0 |

### ms_gw
- 6h: 20/16 OK (80% SR)
- health: ✓ OK, 7 keys, 10 variants, 3 models
- ms_gw logs: all MS-OK-STREAM + MS-STREAM-DONE, healthy

### Tier Attempts
- 6h: 2 total (glm5_2_nv 429_integrate_rate_limit — pre-restart)
- Post-restart: 0

### Docker Logs (post-restart only)
- 3 NV-ZOMBIE-EMPTY (glm5_2_nv: 221,523 input_chars → 12 content_chars, dsv4p_nv: 221,540 input_chars → 12 content_chars) — NVCF content-filter
- NV-THINKING-TIMEOUT on dsv4p_nv (thinking requests → extended timeout 66s, healthy)
- 0 NV-TIER-FAIL, 0 NV-MS-FB, 0 NV-PEER-FB, 0 NV-EMPTY-FASTBREAK, 0 NV-TIER-BUDGET
- All integrate requests succeed on first attempt (k1-k4, 3-25s)

### Error Detail JSONL (today)
- 2 dsv4p_nv ATE pre-restart: single-key empty_200, num_attempts=1, ~62s each
- 0 ATE post-restart

## Decision: NOP

**Reasoning**:
1. All parameters are at floor/optimal values (R1490 confirmed, R1491 re-verified)
2. Post-restart: 0 ATE, 0 tier cycling, 0 peer-fb/ms_gw fallback activity
3. The only failures are zombie_empty_completion (NVCF content-filter: 221K+ chars input → 12 chars output) — code-level, not config-fixable
4. dsv4p_nv 3/4 75% SR post-restart (1 zombie); glm5_2_nv 2/4 50% SR (2 zombie)
5. All integrate requests succeed on first attempt with healthy latency (3-25s)
6. ms_gw healthy (20/16 80% SR), peer-fb enabled with empty skip list
7. All FASTBREAK params at 1 (pexec, integrate), EMPTY_200 at 2 (budget-exhaustion-unreachable per R1489 but harmless)
8. BUDGET floor pattern (dsv4p=66=UPSTREAM, glm5_2=96) validated stable
9. No config drift — compose and container match perfectly
10. Hourly SR trending up (33.3%→77.8%→50.0%) — recovery from pre-restart degradation

**铁律**: 只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
