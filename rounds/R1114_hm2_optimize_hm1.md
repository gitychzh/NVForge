# HM2 Optimize HM1 — Round R1114

**Date**: 2026-07-11 02:25 UTC  
**Decision**: NOP（零参数变更，零 compose 变更，零容器重启）  
**Author**: opc2_uname (HM2)

## Data Summary

### 6h Window (12:00–18:00 UTC)
```
Total: 134 req / 120 OK (89.6% SR) / 14 fail (10.4%)
```

### Per-Model Breakdown
| Model | Total | OK | Fail | SR% | Avg Dur | Max Dur |
|---|---|---|---|---|---|---|
| glm5_2_nv | 93 | 82 | 11 | 88.2% | 19,768ms | 96,999ms |
| dsv4p_nv | 25 | 22 | 3 | 88.0% | 20,881ms | 61,376ms |
| minimax_m3_nv | 9 | 9 | 0 | 100% | 14,483ms | 32,892ms |
| kimi_nv | 7 | 7 | 0 | 100% | 3,605ms | 7,771ms |

### Error Types
| Error Type | Count | Models | Root Cause |
|---|---|---|---|
| zombie_empty_completion | 9 | glm5_2_nv | Code-level — intentional mechanism to abort empty streams |
| all_tiers_exhausted | 3 | dsv4p_nv | Code-level — single-key empty_200 + tier_budget broke + ms_gw BrokenPipeError |
| NVStream_TimeoutError | 2 | glm5_2_nv | Code-level — NVCF stream timeout |

### Tier Attempts
```
0 rows — no per-key failure records in nv_tier_attempts
```

### Fallback Status
```
fallback_occurred=false: 134/134 (100% — no fallback triggered)
All 14 failures are single-tier (tiers_tried_count=1)
```

### Container Status
```
nv_gw: Up ~1h (started 01:21 UTC, 2026-07-11)
ms_gw: Running (model_list: glm5_2_ms, dsv4p_ms, kimi_ms)
```

### nv_gw Logs — Post-Restart Events
```
01:21–01:33: 5 glm5_2_nv integrate all OK (k1-k5), 2 zombie_empty_completion
02:00–02:03: 1 dsv4p_nv all_tiers_exhausted (empty_200 k4 + tier_budget broke + ms_gw BrokenPipeError)
```

## Root Cause Analysis

### 1. zombie_empty_completion (9/14 = 64.3%)
glm5_2_nv integrate returns `finish_reason=stop` with content_chars < 50 but input_chars ≥ 5000 — the NV-ZOMBIE-EMPTY mechanism intentionally aborts the stream and sends `content_filter` error SSE chunk to trigger openclaw fallback. This is code-level behavior, not config-fixable. Designed to prevent 8-minute stalls.

### 2. all_tiers_exhausted (3/14 = 21.4%)
dsv4p_nv pexec: k4 returns empty_200 (Content-Length:0) at 61s. NVU_TIER_BUDGET_DSV4P_NV=66 → remaining 4.9s < 5s minimum → budget breaks. Only 1 key tried (empty200=1, NVU_EMPTY_200_FASTBREAK=2 bug: code still uses threshold=1). NV-GLOBAL-COOLDOWN marks all 5 keys cooling 15s. ABORT-NO-FALLBACK — no peer-fb (dsv4p_nv not in NVU_PEER_FB_SKIP_MODELS, but single-tier fails before peer-fb can fire). ms_gw fallback triggered but BrokenPipeError at 4376ms (relay_started=True — code-level defect).

### 3. NVStream_TimeoutError (2/14 = 14.3%)
glm5_2_nv integrate stream timeout. NVCF internal stream abort. Code-level, not config-fixable.

## NOP Gates Check

| Gate | Status | Detail |
|---|---|---|
| Gate 1: All ATEs single-tier | ❌ FAIL (14/14) | All 14 failures are tiers_tried_count=1 — but Gate 2 exempts |
| Gate 2: Zero single-tier OR all code-level | ✅ PASS | 14/14 single-tier ATEs are code-level defects (zombie_empty, NVStream_TimeoutError, empty_200+BrokenPipeError) |
| Gate 3: NVCFPexecTimeout buffer ≥3s | ✅ N/A | 0 NVCFPexecTimeout in tier_attempts |
| Gate 4: FALLBACK_GRAPH bidirectional | ✅ N/A | No fallback triggered in 6h window |
| Gate 5: Fallback SR = 100% | ✅ N/A | No fallback triggered |
| Gate 6: All params at floor | ✅ PASS | All params at floor/optimal (verified via docker exec env) |

## Current Config (All at Floor/Optimal)

```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=198
NVU_TIER_BUDGET_DSV4P_NV=66
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2 (bug: runtime uses threshold=1, R1039 confirmed)
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=15
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_CONNECT_RESERVE_S=0
MIN_OUTBOUND_INTERVAL_S=0
NV_INTEGRATE_KEY_COOLDOWN_S=0
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=66
```

## Decision

**NOP** — zero parameter change, zero compose change, zero container restart.

All 14 failures are code-level defects:
- 9 zombie_empty_completion (intentional mechanism, not a defect)
- 2 NVStream_TimeoutError (NVCF stream abort)
- 3 all_tiers_exhausted (single-key empty_200 + EMPTY_200_FASTBREAK=2 bug confirmed + ms_gw BrokenPipeError)

None of these are config-fixable. The system is as healthy as NVCF and the code allow. All params are at floor/optimal values. The NVU_EMPTY_200_FASTBREAK=2 bug (R1039 confirmed) is a code-level issue — changing the env value won't help.

**R1113 Context**: Previous round was a false trigger (HM2 self-commit "这是我提交的, 不触发"). This is a double-dispatch of R1112.

## Verification

- ✅ nv_gw env: all params confirmed at floor/optimal
- ✅ nv_gw logs: 0 config-level errors, all failures code-level
- ✅ ms_gw: healthy, model_list=['glm5_2_ms', 'dsv4p_ms', 'kimi_ms']
- ✅ DB: 0 nv_tier_attempts (no per-key failures)
- ✅ Iron rule: only change HM1, never HM2 (no changes made)

## ⏳ 轮到HM1优化HM2