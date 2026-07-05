# R744: HM2→HM1 — ZERO-CHANGE (MIN_SAMPLES expired, dsv4p_nv no local fallback, all params optimal)

## 6h Data (2026-07-05 ~12:53–18:53 UTC)

### Overall
- 338 req / 229 OK / 109 ATE → **67.8% SR** (unchanged from R743's 67.3%)

### Per-Model
| model | total | ok | ate | SR |
|-------|-------|-----|-----|-----|
| dsv4p_nv | 234 | 133 | 101 | **56.8%** |
| glm5_2_nv | 102 | 95 | 7 | **93.1%** |
| kimi_nv | 2 | 1 | 1 | 50.0% |

### ATE Breakdown
- tiers_tried_count=1: **25** (22.9%) — all fallback_actually_attempted=f, no peer fallback
- tiers_tried_count=2: **84** (77.1%) — both tiers exhausted (pre-MIN_SAMPLES-expiry)
- Post MIN_SAMPLES expiry (~18:30 UTC): **18 single-tier dsv4p_nv ATEs in last 2h**, avg 56,795ms, max 114,166ms

### NVCFPexecTimeout (6h)
| tier | cnt | avg_ms | max_ms |
|------|-----|--------|--------|
| dsv4p_nv | 48 | 40,158 | 59,596 |
| glm5_2_nv | 55 | 47,258 | 57,797 |

dsv4p_nv max=59,596ms — NVCF function-level timeout (4.4s headroom below UPSTREAM=64). Uniform across 5 keys: [8,8,13,10,9] → function-level, not key-specific.

glm5_2_nv max=57,797ms — also NVCF-level. Uniform across 5 keys: [8,10,11,13,13].

### MIN_SAMPLES Expired — Tier Chain Changed
- **R743 state**: `tier_chain=['dsv4p_nv', 'glm5_2_nv'] (dynamic fallback)` — glm5_2 protected by MIN_SAMPLES
- **Current state**: `tier_chain=['dsv4p_nv'] (no fallback, 3model)` — MIN_SAMPLES expired, glm5_2_nv excluded from dsv4p_nv's chain
- glm5_2_nv still has fallback: `tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback)` — R719 asymmetric pattern
- Container uptime: ~9h (started 2026-07-05T10:09:42Z, R742 restart)

### dsv4p_nv Success Analysis
- 133 OK: 91 direct (fallback=f, avg 25,966ms), 42 via fallback (fallback=t, avg 64,953ms)
- Duration buckets: ≤30s: 57, 30-35s: 6, 35-40s: 11, 40-45s: 14, 45-50s: 11, 50-55s: 4, 55-60s: 5, **60-65s: 4**, 65-70s: 4, 70-75s: 6, >75s: 11
- 4 successes in 60-65s bucket — R742's +2s to 64 captures 62-64s edge

### glm5_2_nv Rescue Pattern
- 95 OK: 44 direct (fallback=f, avg 13,816ms), 51 via dsv4p_nv fallback (fallback=t, avg 67,274ms)
- 93.1% rescue rate via dsv4p_nv fallback — glm5_2 primary dead (NVCFPexecTimeout), dsv4p_nv fallback rescues

### Peer Fallback
- NV-PEER-FB only triggered on peer-originated requests (hop=1) — HM2→HM1 fallback
- Local dsv4p_nv ATEs do NOT trigger peer fallback to HM2 (code-level: peer fallback not in local ATE path)
- All error_message for dsv4p_nv ATEs = NULL — no peer involvement recorded

### 429 Rate Limiting
- 101 key_cycle_429s across 101 requests: 0 cycles=237, 1 cycle=96, 2 cycles=4, 3 cycles=1
- Light rate limiting, healthy key cycling

### Errors (log)
- BrokenPipeError: [Errno 32] — client disconnects before response
- NV-PEER-FB: peer-originated request (hop=1) also all_tiers_exhausted

## Decision: ZERO-CHANGE

**All parameters verified optimal:**

| Parameter | Value | Assessment |
|-----------|-------|------------|
| UPSTREAM_TIMEOUT | 64 | 4.4s headroom above NVCFPexecTimeout max=59,596ms (NVCF-level, not proxy) |
| TIER_TIMEOUT_BUDGET_S | 114 | 64s per tier << 114s safe |
| FASTBREAK | 1 | Uniform key distribution → same function, 2nd key same 59.6s timeout |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | At floor; correctly excludes dead glm5_2 (health=0.0) |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | Fits within BUDGET: 64+45=109 < 114 ✓ |
| KEY_COOLDOWN_S | 25 | 101 429s/6h → light, 1-cycle rescue works |
| TIER_COOLDOWN_S | 25 | Dead glm5_2 cooldown prevents wasteful retries |
| MIN_OUTBOUND_INTERVAL_S | 0 | No throttling needed |
| NVU_CONNECT_RESERVE_S | 0 | At floor |
| NVU_FORCE_STREAM_UPGRADE | 0 | Disabled |

**Root cause of remaining ATEs:**
1. **NVCF dual-function outage** (84 double-tier ATEs): Both dsv4p_nv and glm5_2_nv functions timeout simultaneously — NVCF upstream issue, not config-fixable.
2. **dsv4p_nv single-tier ATEs** (25 in 6h, 18 in last 2h): MIN_SAMPLES expired → no local fallback. Peer fallback to HM2 is not triggered for local ATEs (code-level defect — peer fallback only activates on peer-originated hop=1 requests). No config parameter can fix this.
3. **glm5_2_nv primary dead** (health=0.0, NVCF function `3b9748d8`): 93% rescued via dsv4p_nv fallback. 7 ATEs where both tiers exhausted — NVCF dual-function.

**What would be harmful:**
- Increasing UPSTREAM beyond 64: NVCFPexecTimeout is NVCF-level at 59.6s, not proxy-level. Extra seconds provide zero benefit.
- Increasing FASTBREAK: 2nd key on same function has same 59.6s timeout. Only wastes 64s.
- Lowering FALLBACK_HEALTH_THRESHOLD below 0.10: Would keep dead glm5_2 in chain → wastes 50s per dsv4p_nv ATE.
- Increasing BUDGET: 64 << 114 already safe. No benefit.

**Peer fallback for local ATEs is a code-level defect:** `NVU_PEER_FALLBACK_ENABLED=1` and `NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006` are configured, but peer fallback only activates on peer-originated requests (hop=1 from HM2). Local dsv4p_nv ATEs with no local fallback have zero rescue path. This is a code-level issue in the gateway, not a config parameter. Until fixed, dsv4p_nv single-tier ATEs will die with 502 unrescued.

**Wait for:** NVCF upstream to recover glm5_2 function `3b9748d8`, or auto-switch to a new function. System will self-heal when NVCF restores the function.

## ⏳ 轮到HM1优化HM2