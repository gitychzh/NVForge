# R743: HM2→HM1 — ZERO-CHANGE (glm5_2_nv NVCF function dead, all params optimal)

## 6h Data (2026-07-05 ~12:30–18:30 UTC)

### Overall
- 333 req / 224 OK / 109 ATE → **67.3% SR** (unchanged from R742's 67.3%)

### Per-Model
| model | total | ok | ate | SR |
|-------|-------|-----|-----|-----|
| dsv4p_nv | 232 | 131 | 101 | **56.5%** |
| glm5_2_nv | 100 | 93 | 7 | **93.0%** |
| kimi_nv | 1 | 0 | 1 | 0.0% |

### ATE Breakdown
- tiers_tried_count=1: **23** (21.1%) — all fallback_actually_attempted=f
- tiers_tried_count=2: **86** (78.9%) — both tiers exhausted (NVCF dual-function)
- Pre-restart: 103 ATEs (82 double, 21 single)
- Post-restart (R742, ~17:56 UTC): 7 ATEs (5 double, 2 single) — 33 min window

### NVCFPexecTimeout
| tier | cnt | avg_ms | max_ms |
|------|-----|--------|--------|
| dsv4p_nv | 51 | 39,582 | 59,596 |
| glm5_2_nv | 52 | 47,085 | 57,797 |

dsv4p_nv max=59,596ms — NVCF function-level timeout, NOT UPSTREAM binding (64s has 4s headroom). Uniform across 5 keys: [8,10,14,10,9] → function-level. Post-restart: **zero dsv4p_nv NVCFPexecTimeout** — dsv4p_nv succeeding directly.

glm5_2_nv max=57,797ms — also NVCF-level. Post-restart: 7 NVCFPexecTimeout all at avg 50,262ms, max 50,281ms — dead function internal timeout.

### Success Duration Buckets (dsv4p_nv, status=200)
- ≤30s: 55, 30-35s: 6, 35-40s: 11, 40-45s: 15, 45-50s: 11, 50-55s: 4, 55-60s: 5, **60-65s: 5**, 65-70s: 4, 70-75s: 6, >75s: 9
- 5 successes in 60-65s bucket (down from 6 in R742) — R742's +2s to 64 captures 62-64s

### Fallback Health
- Log: `tier_chain=['dsv4p_nv', 'glm5_2_nv'] (dynamic fallback, health={'3b9748d8': 0.0, '74f02205': 0.75-0.875})`
- glm5_2 function `3b9748d8` health=**0.0** (dead NVCF function, consistent across all requests)
- dsv4p_nv function `74f02205` health=0.75-0.875 (healthy, declining slightly from 1.0)
- MIN_SAMPLES=5 temporarily protects glm5_2 in tier_chain (container 19min old)
- Once MIN_SAMPLES expires → FALLBACK_HEALTH_THRESHOLD=0.10 will kill glm5_2 from chain → dsv4p_nv loses local fallback
- Peer fallback to HM2: `NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006`, timeout=45s, enabled

### NV-FALLBACK Activity (post-restart)
- glm5_2→dsv4p fallback: **working** (NV-FALLBACK-SUCCESS seen)
- dsv4p→glm5_2 fallback: triggers but glm5_2 dead → peer fallback to HM2
- NV-PEER-FB: hop=1 all_tiers_exhausted (HM2 couldn't rescue either) — normal behavior

### 429 Rate Limiting
- 106 total key_cycle_429s across 99 requests (6h)
- Distribution: 0 cycles=237, 1 cycle=93, 2 cycles=4, 3 cycles=1
- Light rate limiting, healthy key cycling behavior

### Errors (log)
- BrokenPipeError: [Errno 32] — client disconnects before response, not config-fixable
- NVCFPexecgaierror: 1 instance on glm5_2_nv (DNS transient)

## Decision: ZERO-CHANGE

**All parameters verified optimal:**

| Parameter | Value | Assessment |
|-----------|-------|------------|
| UPSTREAM_TIMEOUT | 64 | 4s headroom above NVCFPexecTimeout max=59,596ms (NVCF-level, not proxy) |
| TIER_TIMEOUT_BUDGET_S | 114 | dsv4p(64s) + peer fallback(45s) = 109s < 114s ✓ |
| FASTBREAK | 1 | Correct: dsv4p_nv healthy, 2nd key on same function wasteful |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | At floor; correctly excludes dead glm5_2 (saves 50s/ATE) |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | Fits within BUDGET: 64+45=109 < 114 ✓ |
| KEY_COOLDOWN_S | 25 | 106 429s/6h → light, 1-cycle rescue works |
| TIER_COOLDOWN_S | 25 | Dead glm5_2 cooldown prevents wasteful retries |
| MIN_OUTBOUND_INTERVAL_S | 0 | No throttling needed |
| NVU_CONNECT_RESERVE_S | 0 | At floor |
| NVU_FORCE_STREAM_UPGRADE | 0 | Disabled (timeout=50 irrelevant) |

**Root cause: glm5_2_nv function `3b9748d8` dead on HM1 (NVCF upstream).** Every glm5_2 request fails primary (~50s NVCFPexecTimeout), then falls back to dsv4p_nv (93% rescue rate). dsv4p_nv healthy but loses local fallback when MIN_SAMPLES expires — peer fallback to HM2 is the only rescue path. No config parameter can fix a dead NVCF function. This is the R717 pattern: dead function, no auto-switch → zero-change.

**What would be harmful:** Increasing FALLBACK_HEALTH_THRESHOLD to 0.00 would keep dead glm5_2 in chain → wastes 50s per dsv4p_nv ATE before peer fallback. Increasing FASTBREAK to 2 would waste 64s on 2nd dsv4p_nv key before fallback (BUDGET=114-64=50 → tight for peer). Increasing UPSTREAM beyond 64 provides zero benefit (NVCFPexecTimeout is NVCF-level at 59.6s, not proxy-level).

**Wait for:** NVCF upstream to recover glm5_2 function `3b9748d8`, or auto-switch to a new function (R717 pattern). System will self-heal when NVCF restores the function.

## ⏳ 轮到HM1优化HM2