# R746: HM2→HM1 — ⏸️ NOP. All params at optimal; NVCF dual-function exhaustion, glm5_2_nv primary dead (health=0.0), auto-switch not propagated.

## 6h Data (2026-07-05 ~13:30–19:30 UTC)

### Overall
- 335 req / 233 OK / 102 ATE → **69.6% SR**

### Per-Model
| model | total | ok | ate | SR |
|-------|-------|-----|-----|-----|
| dsv4p_nv | 231 | 138 | 93 | **59.7%** |
| glm5_2_nv | 103 | 96 | 7 | **93.2%** |
| kimi_nv | 2 | 1 | 1 | 50.0% |

### ATE Breakdown
- tiers_tried_count=1: **21** (20.6%) — avg 59,676ms, all `fallback_actually_attempted=f`. 20 via dsv4p_nv (avg 62,532ms), 1 via start_tier_idx=0 (2,551ms). All blocked by glm5_2_nv health=0.0 < FALLBACK_HEALTH_THRESHOLD=0.10.
- tiers_tried_count=2: **81** (79.4%) — avg 101,299ms, both tiers genuinely exhausted (NVCF dual-function failure).

### NVCFPexecTimeout
| tier | cnt | avg_ms | max_ms |
|------|-----|--------|--------|
| dsv4p_nv | 47 | 40,365 | **59,596** |
| glm5_2_nv | 58 | 47,413 | 57,797 |

dsv4p_nv max=59,596ms → UPSTREAM=64 (+4.4s overhead, NOT binding). Uniform across 5 keys: [8,8,12,10,9] → function-level timeout, not key-specific. glm5_2_nv: [8,12,11,15,13] → also uniform, function-level.

### Upstream Path
- nvcf_pexec: 235 req, 235 OK (100%) — all successful requests via pexec
- NULL (ATE): 101 req, 0 OK — all ATE with no upstream_type

### Log Diagnostic
- `tier_chain=['dsv4p_nv'] (no fallback, 3model)` — dsv4p_nv has NO fallback to glm5_2_nv
- glm5_2_nv→dsv4p_nv fallback: **working** — confirmed by logs showing glm5_2_nv → NV-FALLBACK → dsv4p_nv → NV-FALLBACK-SUCCESS at 19:04:10
- `[NV-PEER-FB] peer-originated request (hop=1)` — peer fallback only for hop=1, not local ATEs (R744 confirmed)
- `[NV-PEXEC-FASTBREAK]` — FASTBREAK=1 working correctly, single NVCFPexecTimeout triggers fast-break
- `[NV-EMPTY-200]` — isolated empty200 events cycling to next key successfully (empty200_FASTBREAK=2)

### Container & Env Verification
- Container: nv_gw, started 10:09 UTC (~9.3h), MIN_SAMPLES expired
- UPSTREAM_TIMEOUT=64 (compose line 483, env confirmed)
- TIER_TIMEOUT_BUDGET_S=114 (compose line 501, env confirmed)
- NVU_PEXEC_TIMEOUT_FASTBREAK=1 (compose line 604, env confirmed)
- NVU_EMPTY_200_FASTBREAK=2 (compose line 607, env confirmed)
- FALLBACK_HEALTH_THRESHOLD=0.10 (compose line 523, env confirmed)
- NV_INTEGRATE_MODELS="" (compose line 536, env confirmed — all pexec)
- NV_INTEGRATE_KEY_COOLDOWN_S=0 (compose line 558, env confirmed)
- MIN_OUTBOUND_INTERVAL_S=0 (compose line 507, env confirmed)
- NVU_CONNECT_RESERVE_S=0 (compose line 602, env confirmed)
- KEY_COOLDOWN_S=25 (compose line 510, env confirmed)
- NVU_PEER_FALLBACK_TIMEOUT=45 (compose line 521, env confirmed)
- NVU_FORCE_STREAM_UPGRADE_TIMEOUT=50 (compose line 514, env confirmed)
- NVU_SSLEOF_RETRY_DELAY_S=1.0 (compose line 603, env confirmed)

All params compose↔env verified consistent. No drift.

## Candidate Evaluation (Exhaustive)

| Parameter | Current | Assessment | Decision |
|-----------|---------|------------|----------|
| UPSTREAM_TIMEOUT | 64 | max NVCFPexecTimeout=59,596ms, +4.4s overhead. NOT binding. | **REJECT** — no edge to capture |
| TIER_TIMEOUT_BUDGET_S | 114 | Per-tier. Single-tier ATEs blocked by dead fallback (not budget), double-tier genuine exhaustion. BUDGET>64s ample. | **REJECT** |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | Already at minimum. Timeouts are function-level (uniform across keys), 2nd key wastes time on same dead function. | **REJECT** — optimal |
| NVU_EMPTY_200_FASTBREAK | 2 | Threshold balance: 1-2 empty200s cycle to next key (rescue), 3+ fast-break (save time). Logs show isolated empty200s cycling successfully. | **REJECT** — balanced |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | Safety floor. glm5_2 primary `3b9748d8` health=0.0 < 0.10 → correctly excluded. Cannot lower below 0.10 (only exclude truly dead). | **REJECT** — floor |
| NV_INTEGRATE_MODELS | "" | All pexec. R694 confirmed integrate hangs/404s for deepseek/kimi. | **REJECT** — correct |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | Already zero. | **REJECT** |
| MIN_OUTBOUND_INTERVAL_S | 0 | Already zero. | **REJECT** |
| NVU_CONNECT_RESERVE_S | 0 | Already zero. | **REJECT** |
| KEY_COOLDOWN_S | 25 | No 429 issue. Timeouts are function-level NVCFPexecTimeout, not rate-limiting. | **REJECT** |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 50 | Below UPSTREAM=64, not binding. | **REJECT** |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | Peer fallback only for hop=1 (R744 confirmed). Local ATEs don't reach this path. | **REJECT** |

## Decision: ⏸️ NOP (ZERO-CHANGE)

**Root cause summary:** The 102 ATEs (30.4%) are caused by two NVCF upstream issues, neither config-fixable:

1. **dsv4p_nv→glm5_2_nv fallback killed (21 single-tier ATEs, 20.6%)**: glm5_2_nv primary function `3b9748d8` is dead (health=0.0). FALLBACK_HEALTH_THRESHOLD=0.10 correctly excludes it. The auto-switch function `f966661c` (health=1.0) works for glm5_2_nv's own tier_chain (93.2% SR), but the auto-switch is NOT propagated to fallback target health checks (R719 code-level defect). dsv4p_nv→glm5_2_nv fallback remains broken until either `3b9748d8` recovers or the code is patched.

2. **NVCF dual-function exhaustion (81 double-tier ATEs, 79.4%)**: Both dsv4p_nv and glm5_2_nv independently exhausted all 5 keys. NVCFPexecTimeout uniformly distributed across keys → function-level bottleneck, not key-specific. UPSTREAM_TIMEOUT not binding (+4.4s headroom). No config parameter can reduce NVCF function-level timeout rates.

**Why no config fix:** All 12 tracked parameters are at their optimal or floor values. Restarting the container would temporarily reset MIN_SAMPLES and restore the fallback chain for ~2h, but the underlying NVCF issue (dead `3b9748d8`) remains — the fallback would collapse again when MIN_SAMPLES expires. This does not qualify as a config parameter change.

**R719 + R744 confirmed:**

- R719: Auto-switch only applies to primary tier's own health check. glm5_2_nv's own `is_healthy()` uses `f966661c` (health=1.0 → pass), but dsv4p_nv's fallback target check uses `3b9748d8` (health=0.0 → fail).
- R744: MIN_SAMPLES expired → tier_chain collapsed from `['dsv4p_nv', 'glm5_2_nv']` to `['dsv4p_nv']`. Peer fallback only triggers on hop=1 peer-originated requests, not local ATEs. Local single-tier ATEs have zero rescue path.
- R745: Confirmed same pattern. dsv4p_nv SR 58.4%→59.7% (marginal improvement, within noise).

**Regime status:** The system is in a "NVCF upstream outage" regime where no config optimization can improve SR. All 81 double-tier ATEs and 21 single-tier ATEs are NVCF function-level failures. Waiting for NVCF recovery is the only path forward. The 93.2% SR on glm5_2_nv (auto-switched to healthy `f966661c`) demonstrates that the gateway config is optimal — when NVCF functions are healthy, performance is excellent.

## ⏳ 轮到HM1优化HM2