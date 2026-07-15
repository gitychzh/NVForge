# R1492: HM2→HM1 — NOP (all params floor/optimal, zero ATE post-restart, zombie code-level only)

**Role**: HM2 → HM1 (本回合轮到HM2执行优化)

**Date**: 2026-07-16 03:17 UTC

## Data Collection

### Container Status
- nv_gw: Up ~1h (healthy), started at 2026-07-15 18:15:54 UTC
- health: ✓ OK

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
| MIN_OUTBOUND_INTERVAL_S | 0 | 0 | ✅ |
| NVU_CONNECT_RESERVE_S | 0 | 0 | ✅ |

### 6h nv_requests (pre-restart + post-restart)
- 57 req / 34 OK / 23 fail = 59.6% SR
- 18 zombie_empty_completion, 8 ATE (5 pre-restart, 3 with NULL error_type)
- 0 empty_200, 0 tier cycling (2 tier_attempts: glm5_2_nv 429_integrate_rate_limit — pre-restart)

### Post-restart (since 18:15 UTC, ~1h)
- 22 req / 16 OK / 6 fail = 72.7% SR
- 5 zombie_empty_completion (NVCF content-filter: 221K+ chars input → 12 chars output)
- 0 ATE, 0 tier cycling, 0 NV-MS-FB, 0 NV-PEER-FB
- 0 tier_attempts (clean key pool)

### Per-model Post-restart
| Model | Req | OK | Fail | SR% | Avg Duration |
|---|---|---|---|---|---|
| dsv4p_nv | 16 | 13 | 3 | 81.3% | 22,390ms |
| glm5_2_nv | 6 | 3 | 3 | 50.0% | 14,017ms |

### Per-key Latency (OK only, post-restart)
| Key | Count | Avg | P50 |
|---|---|---|---|
| K1 (idx=0) | 8 | 17,749ms | 12,613ms |
| K2 (idx=1) | 5 | 25,023ms | 17,639ms |
| K3 (idx=2) | 8 | 21,289ms | 20,564ms |
| K4 (idx=3) | 5 | 21,184ms | 13,452ms |
| K5 (idx=4) | 5 | 34,360ms | 38,145ms |

### ms_gw
- 6h: 20/16 OK (80% SR)
- Post-restart: 5/4 OK (80% SR)
- health: ✓ OK

### Docker Logs (post-restart only)
- 5 NV-ZOMBIE-EMPTY (dsv4p_nv: 221,540 chars → 12 chars, glm5_2_nv: 221,523 chars → 12 chars) — NVCF content-filter
- NV-THINKING-TIMEOUT on dsv4p_nv (thinking requests → extended timeout 66s, healthy)
- All integrate requests succeed on first attempt (k1-k4, 3-25s)
- 0 NV-TIER-FAIL, 0 NV-MS-FB, 0 NV-PEER-FB, 0 NV-EMPTY-FASTBREAK, 0 NV-TIER-BUDGET
- 0 NV-CYCLE, 0 NV-GLOBAL-COOLDOWN

### Error Detail JSONL (today)
- 2 dsv4p_nv ATE pre-restart: single-key empty_200, num_attempts=1, ~62s each
- 0 ATE post-restart

## Decision: NOP

**Reasoning**:
1. All parameters are at floor/optimal values (R1491 confirmed, R1492 re-verified)
2. Post-restart (~1h): 0 ATE, 0 tier cycling, 0 peer-fb/ms_gw fallback activity
3. The only failures are zombie_empty_completion (NVCF content-filter: 221K+ chars input → 12 chars output) — code-level, not config-fixable
4. dsv4p_nv 13/16 81.3% SR post-restart (3 zombie); glm5_2_nv 3/6 50% SR (3 zombie)
5. All integrate requests succeed on first attempt with healthy latency (3-25s)
6. ms_gw healthy (5/4 80% SR), peer-fb enabled with empty skip list
7. All FASTBREAK params at 1 (pexec, integrate), EMPTY_200 at 2 (budget-exhaustion-unreachable per R1489 but harmless)
8. BUDGET floor pattern (dsv4p=66=UPSTREAM, glm5_2=96) validated stable
9. No config drift — compose and container match perfectly
10. Post-restart SR trending up: 59.6% (6h) → 72.7% (post-restart ~1h) — recovery validated

**铁律**: 只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
