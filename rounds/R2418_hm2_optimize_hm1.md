# R2418: NVU_TIER_BUDGET_DSV4P_NV 265→120

## Timestamp
2026-07-29 22:15 UTC

## Change
- **File**: `/opt/cc-infra/docker-compose.yml` line 494
- **Param**: `NVU_TIER_BUDGET_DSV4P_NV`
- **Value**: 265 → 120
- **Scope**: HM1 only (iron law)

## Rationale

### 24h DB Analysis (nv_requests)
| Model       | Total | OK  | SR    | avg_ok | avg_err | max_err |
|-------------|-------|-----|-------|--------|---------|---------|
| dsv4p_nv    | 23    | 7   | 30.4% | 59s    | 143s    | 224s    |
| glm5_2_nv   | 116   | 77  | 66.4% | 18.5s  | 16.6s   | 178s    |
| kimi_nv     | 2     | 0   | 0%    | —      | —       | —       |

### dsv4p_nv NVCF Degradation
- NVCF function 74f02205 (ai-deepseek-v4-pro) experienced sustained SSLEOF storms
- Last 11 hours: **0% SR (0/10)** — complete NVCF failure
- All 5 keys hit same SSLEOF on same function_id → NVCF-side issue, not key-specific
- SSLEOF errors cycle through all 7 attempts (5 keys + 2 retries), wasting 5s each

### ATE Cost Analysis
- 16 ATEs in 24h. Durations sorted:
  224, 200, 196, 192, 191, 187, 156, 145, 144, 143, 108, 106, 106, 105, 83, 3 seconds
- avg ATE = 152s, max = 224s

### FASTBREAK=3 Ineffectiveness
- NVU_PEXEC_TIMEOUT_FASTBREAK=3 triggers on 3 **consecutive** pexec timeouts
- SSLEOF errors RESET the consecutive_pexec_timeout counter
- Alternating pattern: Timeout, SSLEOF, Timeout, SSLEOF, Timeout → 3 timeouts never consecutive
- FASTBREAK never fires → ATEs run to budget exhaustion

### Budget=120 Impact
| Metric                  | Before (265) | After (120) |
|--------------------------|--------------|-------------|
| Max ATE                  | 224s         | 120s (47%)  |
| ATEs truncated           | 0            | 10          |
| Total time saved/24h     | —            | 579s (9.7m) |
| Successes lost           | 0            | 1 (184s TTFB) |
| Successes retained       | 7/7          | 6/7 (85.7%) |

OK TTFBs: [10, 23, 28, 48, 49, 73, 184] seconds
- budget=120: retains all successes ≤73s (6/7), only loses the marginal 184s outlier
- 184s success was an extreme outlier (normal dsv4p_nv TTFB = 1.8-4.9s)

### Recovery Safety
- NVCF normal response: 1.8-4.9s (non-thinking mode)
- 120s budget = 24x normal response time margin
- If NVCF recovers, all successes (<73s) complete well within 120s
- max 2 full pexec timeout attempts (50s+50s) + remaining for SSLEOF cycling

## Verification
- Container healthy after restart (18s uptime, healthy)
- All other tier budgets unchanged
- git committed: `b08c32f` to /opt/cc-infra

## Risk
- **LOW**: Single ENV change, no code modification
- **Reversible**: `docker-compose.yml.bak.R2418` backup exists
- **Fallback**: peer-fallback already skipped for dsv4p_nv; agent falls back to ms_gw after 502
