# R1490: HM2→HM1 — NOP (all params floor/optimal, zero ATE post-restart, zombie code-level only)

**Role**: HM2 → HM1 (本回合轮到HM2执行优化)

**Date**: 2026-07-16 02:55 UTC

## Data Collection

### Container Status
- nv_gw: Up 41 minutes (healthy), started at 2026-07-15 18:15:54 UTC
- Compose md5: ba4f2871fc9695f237e9a436ac25c279

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

### 6h nv_requests (pre-restart + post-restart)
- 57 req / 34 OK / 23 fail = 59.6% SR
- 18 zombie_empty_completion, 5 ATE (all pre-restart)

### Post-restart (41 min)
- 4 req / 3 OK / 1 fail = 75.0% SR
- 1 zombie_empty_completion (glm5_2_nv, 221,523 input_chars, 6,383ms)
- 0 ATE, 0 tier cycling, 0 NV-MS-FB, 0 NV-PEER-FB
- dsv4p_nv: 2/2 100% SR, avg 12,189ms
- glm5_2_nv: 1/2 50% SR (1 zombie)

### Per-model Post-restart
| Model | Req | OK | Fail | SR% | Avg Duration |
|---|---|---|---|---|---|
| dsv4p_nv | 2 | 2 | 0 | 100.0% | 12,189ms |
| glm5_2_nv | 2 | 1 | 1 | 50.0% | 6,000ms |

### ms_gw
- 6h: 20/16 OK (80% SR)
- Post-restart: 1/1 OK (100% SR)
- ms_gw logs: all MS-OK-STREAM + MS-STREAM-DONE, healthy

### Tier Attempts
- 6h: 2 total (glm5_2_nv 429_integrate_rate_limit — pre-restart)
- Post-restart: 0

### Docker Logs (post-restart)
- 1 NV-ZOMBIE-EMPTY on glm5_2_nv (input_chars=221,523, content_chars=12 < 50 → abort)
- NV-THINKING-TIMEOUT on dsv4p_nv (thinking requests → extended timeout 66s, healthy)
- 0 NV-TIER-FAIL, 0 NV-MS-FB, 0 NV-PEER-FB, 0 NV-EMPTY-FASTBREAK, 0 NV-TIER-BUDGET

## Decision: NOP

**Reasoning**:
1. All parameters are at floor/optimal values (R1489 confirmation)
2. Post-restart: 0 ATE, 0 tier cycling, 0 peer-fb/ms_gw fallback activity
3. The only failure is zombie_empty_completion on glm5_2_nv (NVCF content-filter: 221K input → 12 chars output) — code-level, not config-fixable
4. dsv4p_nv 100% SR post-restart, healthy
5. ms_gw healthy, dsv4p_nv→dsv4p_ms removed from MODELMAP (R1488), peer-fb is the rescue path
6. All FASTBREAK params at 1 (pexec, integrate), EMPTY_200 at 2 (code-level no-op per R1039 but harmless)
7. BUDGET floor pattern (dsv4p=66=UPSTREAM, glm5_2=96) validated stable
8. No config drift — compose and container match perfectly

**铁律**: 只改HM1不改HM2

## ⏳ 轮到HM1优化HM2
