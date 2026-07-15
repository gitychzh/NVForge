# R1432: HM2→HM1 — NOP (false trigger, double-dispatch, 586th chain of R1133)

**Timestamp**: 2026-07-15 14:46 UTC

## Data Collection (HM1)

### 6h Window: 59 req, 42 OK → 71.2% SR

| Model | Req | OK | Fail | SR% | Avg Dur |
|-------|-----|-----|------|-----|---------|
| glm5_2_nv | 44 | 35 | 9 | 79.5% | 11.6s |
| dsv4p_nv | 15 | 7 | 8 | 46.7% | 30.4s |

### Failure Breakdown

| Error Type | Count | Avg Dur |
|-----------|-------|---------|
| zombie_empty_completion | 15 | 11.3s |
| all_tiers_exhausted | 2 | 109.1s |

### Tier Attempts: 0 (clean)

### ms_gw: 25 total, 24 OK, 1 error (96.0% SR)

### Compose md5: 3863a7c1 (R1431 deployed — BUDGET=124 confirmed in env)

### nv_gw: Up 8 minutes (healthy, just restarted for R1431)

### Hourly SR

| Hour (UTC) | Total | OK | Fail | SR% |
|-----------|-------|-----|------|------|
| 01:00 | 6 | 5 | 1 | 83.3% |
| 02:00 | 6 | 4 | 2 | 66.7% |
| 03:00 | 9 | 5 | 4 | 55.6% |
| 04:00 | 7 | 3 | 4 | 42.9% |
| 05:00 | 26 | 22 | 4 | 84.6% |
| 06:00 | 5 | 3 | 2 | 60.0% |

## Root Cause Analysis

### zombie_empty_completion (15): NVCF Content-Filter — NOT CONFIG-FIXABLE

- 9 glm5_2_nv integrate: NVCF content_filter stop, content_chars=12 < 50, avg input 210K chars, avg 7.1s
- 6 dsv4p_nv pexec: NVCF content_filter stop, content_chars=12 < 50, avg input 210K chars, avg 17.6s
- **Detection**: `NV-ZOMBIE-EMPTY` + `NV-ZOMBIE-ERROR-CHUNK` in nv_gw logs. Gateway correctly detects and triggers fallback.
- **Verdict**: NVCF server-side content filtering. No gateway parameter can fix this.

### all_tiers_exhausted (2): dsv4p_nv — BOTH PRE-R1431

- 02:06 UTC: 106,052ms, single tier, no fallback. **Pre-R1431** (BUDGET=118 at that time).
- 06:05 UTC: 112,049ms, single tier, no fallback. **Pre-R1431** (BUDGET=118 at that time).
- Both ATEs occurred before R1431 container restart at 14:38 UTC. **Zero post-R1431 ATE data**.
- 0 tier_attempts confirms clean key cycling (no 504/SSLEOFError/429).

### glm5_2_nv ATE cluster (12 entries, 05:17-05:25): CONTEXT-LENGTH 400 — NOT GATEWAY FAILURE

- All 12 entries show `all_tiers_exhausted` with `status=200` and `fallback_occurred=t`.
- Logs: `NV-INTEGRATE-NONCYCLE-ERR` → `resp.status=400` → context-length exceeded. Gateway correctly handles as NONCYCLE (no key waste), falls back to ms_gw which returns 200 OK.
- These are NOT real failures — they are context-length errors rescued by ms_gw.

### ms_gw: 96.0% healthy (24/25 OK)

- 1 error (single transient). MS-STREAM-DONE normal.

## Decision: NOP (No Optimization Possible)

**False trigger — double-dispatch.** R1431 was deployed 8 minutes ago (container restarted at 14:38 UTC). All data in the 6h window is pre-R1431. Zero post-R1431 data to evaluate.

**All parameters at floor/optimal:**

| Parameter | Value | Status |
|-----------|-------|--------|
| `NVU_PEXEC_TIMEOUT_FASTBREAK` | 1 | ✓ Floor (function-level) |
| `NVU_INTEGRATE_TIMEOUT_FASTBREAK` | 1 | ✓ Floor (function-level, R1010) |
| `NVU_EMPTY_200_FASTBREAK` | 2 | ✓ Key-specific (R1031) |
| `TIER_COOLDOWN_S` | 15 | ✓ R1103 revert |
| `UPSTREAM_TIMEOUT` | 66 | ✓ Optimal |
| `TIER_TIMEOUT_BUDGET_S` | 205 | ✓ Optimal |
| `NVU_TIER_BUDGET_DSV4P_NV` | 124 | ✓ R1431 (+6s from 118) |
| `NVU_TIER_BUDGET_GLM5_2_NV` | 96 | ✓ |
| `NVU_TIER_BUDGET_MINIMAX_M3_NV` | 100 | ✓ |
| `NVU_STREAM_TOTAL_DEADLINE_S` | 42 | ✓ |
| `NVU_STREAM_FIRST_BYTE_DEADLINE_S` | 20 | ✓ |
| `NVU_PEER_FB_SKIP_MODELS` | (empty) | ✓ All models enabled |
| `NVU_MS_GW_FALLBACK_TIMEOUT` | 195 | ✓ |
| `NVU_PEER_FALLBACK_TIMEOUT` | 66 | ✓ |
| `KEY_COOLDOWN_S` | 25 | ✓ |
| `MIN_OUTBOUND_INTERVAL_S` | 0 | ✓ |

**No config changes made.** The zombie_empty_completion is NVCF-side content filtering. Both ATEs are pre-R1431. All parameters are at their proven floor/optimal values. This round is a false trigger (double-dispatch — HM2 pushed R1431, script detected as "HM1 submitted" and re-triggered HM2→HM1 cycle).

**Iron Law**: 只改HM1不改HM2. 改前必有数据, 改后必有验证.
## ⏳ 轮到HM1优化HM2
