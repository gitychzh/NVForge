# R745: HM2→HM1 — ZERO-CHANGE. MIN_SAMPLES expired, glm5_2_nv primary 3b9748d8 dead (health=0.0), auto-switch f966661c not propagated to fallback target health check.

## 6h Data (2026-07-05 ~13:15–19:15 UTC)

### Overall
- 335 req / 231 OK / 104 ATE → **69.0% SR**

### Per-Model
| model | total | ok | ate | SR |
|-------|-------|-----|-----|-----|
| dsv4p_nv | 231 | 135 | 96 | **58.4%** |
| glm5_2_nv | 102 | 95 | 7 | **93.1%** |
| kimi_nv | 2 | 1 | 1 | 50.0% |

### ATE Breakdown
- tiers_tried_count=1: **20** (19.2%) — all dsv4p_nv, fallback NOT attempted (glm5_2 health=0.0 < 0.10 threshold, MIN_SAMPLES expired at 18:33 UTC)
- tiers_tried_count=2: **84** (80.8%) — both tiers exhausted (NVCF dual-function outage)

### NVCFPexecTimeout Binding
| tier | cnt | avg_ms | max_ms |
|------|-----|--------|--------|
| dsv4p_nv | 47 | 40,170 | **59,596** |
| glm5_2_nv | 56 | 47,477 | 57,797 |

dsv4p_nv max=59,596ms → UPSTREAM=64 (+4.4s overhead, NOT binding). Uniform across 5 keys: [8,8,12,10,9] → function-level timeout, not key-specific.

### NVCF Health
- dsv4p_nv primary `74f02205`: 0.75-0.875 (healthy, declining from 1.0)
- glm5_2_nv primary `3b9748d8`: 0.0 (dead, NVCF upstream)
- glm5_2_nv auto-switch `f966661c`: 1.0 (working for glm5_2_nv's own tier_chain)
- FALLBACK_GRAPH dsv4p_nv→glm5_2_nv: **broken** — glm5_2 excluded because health check uses primary `3b9748d8` (0.0), not auto-switched `f966661c` (1.0)
- FALLBACK_GRAPH glm5_2_nv→dsv4p_nv: **working** — dsv4p_nv health=0.75 > 0.10

### Timeline (Container uptime: 10:09 UTC → ~9h)
- 10:09–18:33 UTC: MIN_SAMPLES protects glm5_2 in tier_chain despite health=0.0 → `tier_chain=['dsv4p_nv', 'glm5_2_nv']`
- 18:33 UTC: MIN_SAMPLES expired → `tier_chain=['dsv4p_nv'] (no fallback, 3model)`
- 19:03 UTC: glm5_2_nv auto-switch `f966661c` appears in own health check (health=1.0), but NOT used for dsv4p_nv→glm5_2_nv fallback target check

### Peer Fallback
- `[NV-PEER-FB]` only for hop=1 → peer fallback does NOT trigger for local ATEs (code-level defect, R744 confirmed)
- 20 single-tier ATEs with zero rescue path (no local fallback, no peer fallback)

### Config Verification
| Param | Value | Assessment |
|-------|-------|------------|
| UPSTREAM_TIMEOUT | 64 | +4.4s above NVCFPexecTimeout max=59,596 → NOT binding |
| TIER_TIMEOUT_BUDGET_S | 114 | Per-tier: 64s << 114s → safe |
| FASTBREAK | 1 | Single key per tier, 64s max → fine |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | Floor. 3b9748d8=0.0 < 0.10 → correctly excluded |
| NVU_PEER_FALLBACK_ENABLED | 1 | Set but not in local ATE code path |

## Decision: ZERO-CHANGE

**Root cause:** NVCF function `3b9748d8` (glm5_2_nv primary) is dead (health=0.0). The auto-switch function `f966661c` (health=1.0) works for glm5_2_nv's own tier_chain (93.1% SR), but the fallback target health check in dsv4p_nv→glm5_2_nv still uses the primary function ID `3b9748d8`, not the auto-switched `f966661c`. This is the R719 auto-switch-not-propagated code-level defect.

**Why no config fix:** No config parameter can fix a dead NVCF function or the auto-switch propagation gap. All params verified optimal. Restarting the container would temporarily reset MIN_SAMPLES but doesn't fix the underlying issue.

**R719 confirmed:** Auto-switch only applies to the primary tier's own health check. When dsv4p_nv checks glm5_2_nv as a fallback target, it uses `is_healthy(3b9748d8)` → False (0.0 < 0.10), not `is_healthy(f966661c)` → True (1.0 > 0.10). The dsv4p_nv→glm5_2_nv fallback remains broken until either `3b9748d8` recovers or the code is fixed to propagate auto-switch to fallback target health checks.

## ⏳ 轮到HM1优化HM2