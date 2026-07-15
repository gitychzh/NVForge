# R1428: HM2→HM1 — NOP (false trigger, double-dispatch, 584th chain of R1133)

**Timestamp**: 2026-07-15 13:45 UTC

## Data Collection (HM1)

### 6h Window: 58 req, 43 OK → 74.1% SR

| Model | Req | OK | Fail | SR% | Avg Dur |
|-------|-----|-----|------|-----|---------|
| glm5_2_nv | 44 | 36 | 8 | 81.8% | 12.0s |
| dsv4p_nv | 14 | 7 | 7 | 50.0% | 24.6s |

### Failure Breakdown

| Error Type | Count | Avg Dur |
|-----------|-------|---------|
| zombie_empty_completion | 14 | 11.7s |
| all_tiers_exhausted | 1 | 106.1s |

### Tier Attempts: 0 (clean)

### ms_gw: 23 total, 22 OK, 1 error (95.7% healthy)

### Compose md5: 59dc3c54 (unchanged from R1427)

### Hourly SR

| Hour (UTC) | Total | OK | Fail | SR% |
|-----------|-------|-----|------|------|
| 00:00 | 4 | 4 | 0 | 100.0% |
| 01:00 | 6 | 5 | 1 | 83.3% |
| 02:00 | 6 | 4 | 2 | 66.7% |
| 03:00 | 9 | 5 | 4 | 55.6% |
| 04:00 | 7 | 3 | 4 | 42.9% |
| 05:00 | 26 | 22 | 4 | 84.6% |

## Root Cause Analysis

### zombie_empty_completion (14): NVCF Content-Filter — NOT CONFIG-FIXABLE

- 6 dsv4p_nv pexec: NVCF returns `finish_reason=stop, content_chars=12 < 50` on large input (210K+ chars). Gateway correctly detects zombie and sends error chunk to trigger openclaw fallback.
- 8 glm5_2_nv integrate: Same NVCF content-filter pattern. Content returned is 12 chars (empty), gateway aborts stream and triggers fallback.
- **Detection**: `NV-ZOMBIE-EMPTY` + `NV-ZOMBIE-ERROR-CHUNK` in nv_gw logs. All zombies have `content_chars=12 < 50`.
- **Verdict**: NVCF server-side content filtering. No gateway parameter can fix this. The zombie detection and fallback mechanism is working correctly.

### all_tiers_exhausted (1): dsv4p_nv single anomaly

- 1 ATE at 02:06 UTC, 106s. Single transient anomaly, not a pattern.
- 0 tier_attempts confirms clean key cycling (no NVCFPexecTimeout, no SSLEOFError).

### glm5_2_nv ATE cluster (13 entries at 05:18-05:25): CONTEXT-LENGTH 400 — NOT GATEWAY FAILURE

- All 13 entries show `all_tiers_exhausted` with `upstream_type=NULL` and `status=200`.
- Logs confirm: `NV-INTEGRATE-NONCYCLE-ERR` → `resp.status=400` → `body={"message":"maximum context length is 202752 tokens. However, your messages resulted in X tokens."}`.
- Gateway correctly handles 400 as NONCYCLE (no key waste), falls back to ms_gw, ms_gw returns 200 OK. These are NOT real failures — they are context-length errors rescued by ms_gw.

### ms_gw: 95.7% healthy (22/23 OK)

- 1 error at 01:43 UTC, 29.3s duration. Single transient.

## Decision: NOP (No Optimization Possible)

**All parameters at floor/optimal:**

| Parameter | Value | Status |
|-----------|-------|--------|
| `NVU_PEXEC_TIMEOUT_FASTBREAK` | 1 | ✓ Floor (function-level) |
| `NVU_INTEGRATE_TIMEOUT_FASTBREAK` | 1 | ✓ Floor (function-level, R1010) |
| `NVU_EMPTY_200_FASTBREAK` | 2 | ✓ Key-specific (R1031) |
| `TIER_COOLDOWN_S` | 15 | ✓ R1103 revert |
| `UPSTREAM_TIMEOUT` | 66 | ✓ Optimal |
| `TIER_TIMEOUT_BUDGET_S` | 205 | ✓ Optimal |
| `NVU_TIER_BUDGET_DSV4P_NV` | 112 | ✓ |
| `NVU_TIER_BUDGET_GLM5_2_NV` | 96 | ✓ |
| `NVU_TIER_BUDGET_MINIMAX_M3_NV` | 100 | ✓ |
| `NVU_STREAM_TOTAL_DEADLINE_S` | 42 | ✓ |
| `NVU_STREAM_FIRST_BYTE_DEADLINE_S` | 20 | ✓ |
| `NVU_PEER_FB_SKIP_MODELS` | (empty) | ✓ All models enabled |
| `NVU_MS_GW_FALLBACK_TIMEOUT` | 195 | ✓ |
| `NVU_PEER_FALLBACK_TIMEOUT` | 66 | ✓ |
| `KEY_COOLDOWN_S` | 25 | ✓ |
| `MIN_OUTBOUND_INTERVAL_S` | 0 | ✓ |

**No config changes made.** The zombie_empty_completion is NVCF-side content filtering and cannot be addressed by gateway configuration. The single ATE is a transient anomaly. All parameters are at their proven floor values. This round is a false trigger (double-dispatch — HM2 pushed R1427, script detected as "HM1 submitted" and re-triggered HM2→HM1 cycle).

**Iron Law**: 只改HM1不改HM2. 改前必有数据, 改后必有验证.

## ⏳ 轮到HM1优化HM2
