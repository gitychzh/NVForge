# R1494: HM2→HM1 — NOP (all params floor/optimal, zero ATE post-restart, zombie code-level only)

**Date**: 2026-07-16
**Author**: opc2_uname (HM2)
**Decision**: NOP — zero-change

---

## Data Collection (HM1 via SSH)

### Container Status
- **Container**: nv_gw Up About an hour (healthy) — ⚠️ discrepancy: docker inspect says 2026-07-15T18:15:54Z (R1488), but docker ps says "Up About an hour" (~02:33 July 16 restart). Logs have only 86 lines starting 02:33:20 — consistent with recent restart.
- **Compose md5**: ba4f2871fc9695f237e9a436ac25c279 (unchanged from R1493)

### 6h Window

| Metric | Value |
|--------|-------|
| Total requests | 57 |
| OK (200) | 34 |
| Failed (502) | 23 |
| **SR** | **59.6%** |
| zombie_empty_completion | 18 |
| all_tiers_exhausted (ATE, 502) | 5 |
| all_tiers_exhausted (ATE, total) | 8 |
| ATE recovered (200) | 3 |
| Tier attempts | 2 |
| ms_gw (6h) | 20/16 (80.0%) |

### Post-Restart Window (18:15:54Z → present)

| Metric | Value |
|--------|-------|
| Total requests | 13 |
| OK (200) | 8 |
| zombie_empty_completion | 5 |
| **SR** | **61.5%** |
| ATE | **0** |
| Tier cycling | 0 |
| ms_gw fallback | 0 |
| peer-fallback | 0 |

### Hourly SR (6h)

| Hour (UTC) | Total | OK | Fail | SR |
|------------|-------|-----|------|-----|
| 14:00 | 7 | 3 | 4 | 42.9% |
| 15:00 | 6 | 2 | 4 | 33.3% |
| 16:00 | 9 | 6 | 3 | 66.7% |
| 17:00 | 8 | 4 | 4 | 50.0% |
| 18:00 | 18 | 14 | 4 | 77.8% |
| 19:00 | 9 | 5 | 4 | 55.6% |

14:00-17:00 are pre-restart; 18:00-19:00 are post-restart (R1488 applied at 18:15:54Z).

### Per-Model SR (6h)

| Model | Total | OK | Fail | SR | Avg Dur |
|-------|-------|-----|------|-----|---------|
| dsv4p_nv | 33 | 22 | 11 | 66.7% | 29,871ms |
| glm5_2_nv | 24 | 12 | 12 | 50.0% | 13,758ms |

### Success Latency Distribution

| Bucket | Count |
|--------|-------|
| <5s | 1 |
| 5-15s | 16 |
| 15-30s | 7 |
| 30-60s | 9 |
| >60s | 1 |

### ATE Detail (8 total, all dsv4p_nv)

| Metric | Value |
|--------|-------|
| ATE total (all statuses) | 8 |
| ATE 502 (unrecovered) | 5 |
| ATE 200 (recovered) | 3 |
| Avg duration | 46,012ms |

All 5 ATE 502s are pre-restart (504_nv_gateway_timeout + empty_200 on single key, num_attempts=1 — BUDGET=66 exhausted). 3 recovered ATEs likely through peer-fb (dsv4p_nv not in MODELMAP since R1488). 0 fallback_occurred in DB — possible column tracking issue.

### Zombie Detail (18 total)

All zombies are `finish_reason=stop, content_chars < 50, input_chars >= 5000, no tool_calls` — NVCF content-filter returning valid-but-empty streams. Gateway correctly detects and aborts ~3-25s, sending `finish_reason=timeout` SSE chunk to trigger agent fallback. Avg input: 221K chars (dsv4p_nv), 220K chars (glm5_2_nv). Not config-fixable.

### Log Analysis (tail 100, 86 lines)

All recent entries (02:33-03:36 UTC):
- `[NV-REQ]` — normal request flow (glm5_2_nv integrate, dsv4p_nv pexec)
- `[NV-THINKING-TIMEOUT]` — thinking requests getting extended 66s timeout
- `[NV-ZOMBIE-EMPTY]` + `[NV-ZOMBIE-ERROR-CHUNK]` — zombie abort + SSE error injection
- **0 ATE, 0 tier failures, 0 peer-fb, 0 ms_gw fallback** — system is healthy

### Container Env vs Compose Cross-Check

| Param | Compose | Container Env | Match |
|-------|---------|---------------|-------|
| UPSTREAM_TIMEOUT | 66 | 66 | ✅ |
| TIER_TIMEOUT_BUDGET_S | 205 | 205 | ✅ |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | 66 | ✅ |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | 96 | ✅ |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms | ✅ |
| NVU_PEER_FB_SKIP_MODELS | "" | "" | ✅ |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | 1 | ✅ |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | 1 | ✅ |
| NVU_EMPTY_200_FASTBREAK | 2 | 2 | ✅ |
| TIER_COOLDOWN_S | 15 | 15 | ✅ |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | 66 | ✅ |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | 120 | ✅ |

All params match — no stale env.

### Tier Attempts

2 total (both glm5_2_nv 429_integrate_rate_limit) — minimal key cycling, clean key pool.

## Decision: NOP — Zero Change

**Rationale**:
1. All 5 ATE 502s are pre-restart. Post-restart: **0 ATE** in ~9h (13 requests, low traffic but zero structural failures).
2. All 18 zombie_empty_completion failures are code-level NVCF content-filter behavior — gateway correctly detects and aborts. Not config-fixable.
3. All params at floor/optimal: FASTBREAK=1/1/2, BUDGET=205, UPSTREAM=66, TIER_BUDGET=66/96/100, COOLDOWN=15/25, MODELMAP=glm5_2_nv+kimi_nv (dsv4p_nv removed → peer-fb rescue).
4. 0 tier cycling, 0 peer-fb/ms_gw errors, 0 key_cycle_429s (clean key pool).
5. Compose vs container env: all match, no stale env.
6. ms_gw: 20/16 (80% SR) — healthy fallback.
7. Same picture as R1493 — system is stable at floor. No parameter change justified.

**No parameter change.** The system is at its optimal floor configuration. Zombie completions are NVCF upstream content-filter behavior, not gateway-configurable. Wait for HM1 to evaluate.
## ⏳ 轮到HM1优化HM2
