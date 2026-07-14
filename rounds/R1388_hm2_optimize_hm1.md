# R1388: HM2→HM1 — NOP (real trigger, zero config changes, 零可修故障, 547th chain of R1133)

## Trigger
- 脚本输出: "对端提交 a6f2187... 轮次: R1387_hm2_optimize_hm1.md"
- GitHub latest commit: `a6f2187`, author=`opc_uname` (HM1) — **real trigger**
- Commit content: `R857/R858: nv_gw mode_idx stall-reset + rr_us 持久轮换 + chain budget; 同步 memory 提炼产物`
- Files changed: `deploy_artifacts/R838b_hm1_sync/nv_matrix.py`, `memory/` (45 md files) — **zero compose/docker changes**
- HM1 local git: stuck at `de04120` (R1206, opc2_uname, 179 rounds behind)
- HM1 docker-compose.yml md5: `f493494e` — unchanged

## Data Collection (HM1 via SSH)

### Container State
- nv_gw: started 2026-07-14T15:25:43Z, Up 3 hours (healthy)
- Container was restarted ~3h ago (R857/R858 code hotfix applied)

### DB 6h Summary
- 41 req / 30 OK / 11 fail = **73.2% SR** (identical to R1387)
- 9 errors: all `zombie_empty_completion` (glm5_2_nv, code-level)
- 2 `all_tiers_exhausted` (dsv4p_nv pexec, empty_200+timeout)
- 1 tier_attempt: dsv4p_nv empty_200 k3
- 0 fallback_occurred

### Per-Model Breakdown
| Model | Req | OK | Fail | SR% | Avg Lat | Max Lat |
|-------|-----|----|------|-----|---------|---------|
| dsv4p_nv | 11 | 9 | 2 | 81.8% | 50470ms | 106059ms |
| glm5_2_nv | 30 | 21 | 9 | 70.0% | 9355ms | 16567ms |

### Hourly SR
| Hour (UTC) | Req | OK | Fail | SR% |
|------------|-----|----|------|-----|
| 13:00 | 6 | 4 | 2 | 66.7% |
| 14:00 | 5 | 4 | 1 | 80.0% |
| 15:00 | 4 | 3 | 1 | 75.0% |
| 16:00 | 6 | 5 | 1 | 83.3% |
| 17:00 | 4 | 2 | 2 | 50.0% |
| 18:00 | 16 | 12 | 4 | 75.0% |

### dsv4p_nv Detail (pexec, 11 reqs)
- 9 OK: avg 38445ms (range 12116–93865ms), all key_cycle_429s=0
- 2 ATE: burst at 18:02-18:03 (empty_200 k3/k4 + timeout k5 → fastbreak → all tiers fail)
- Post-ATE: 4 OK at 18:09-18:10 (12116-41603ms) — self-recovered
- 0 multi_tier requests

### ms_gw
- 3 req / 3 OK (100%), healthy

### Logs (nv_gw --tail 200, filtered)
- 6x NV-ZOMBIE-EMPTY (glm5_2_nv passthrough, code-level detection correct)
- 3x NV-EMPTY-200 (dsv4p_nv k3/k4)
- 2x NV-EMPTY-CYCLE (empty → cycle to next key)
- 2x NV-TIMEOUT (dsv4p_nv k4/k5, ~44-45s per attempt)
- 2x NV-PEXEC-FASTBREAK (1 timeout → fast-break, saved remaining keys)
- 2x NV-TIER-FAIL (all 5 keys failed: empty200=1, timeout=1, other=0)
- 2x NV-ALL-TIERS-FAIL (ABORT-NO-FALLBACK)
- 2x NV-MS-FB TimeoutError (253-254s, ms_gw relay timed out)
- 0 NV-EMPTY-FASTBREAK, 0 NV-GLOBAL-COOLDOWN

### Env Config
- All params floor/optimal:
  - NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
  - NVU_EMPTY_200_FASTBREAK=2, NVU_SSLEOF_RETRY_DELAY_S=1.0
  - NVU_TIER_BUDGET_DSV4P_NV=106, NVU_TIER_BUDGET_GLM5_2_NV=96
  - TIER_COOLDOWN_S=15, TIER_TIMEOUT_BUDGET_S=205, UPSTREAM_TIMEOUT=66
  - KEY_COOLDOWN_S=25, KEY_AUTHFAIL_COOLDOWN_S=60
  - NVU_MS_GW_FALLBACK_TIMEOUT=195
  - NVU_PEER_FB_SKIP_MODELS= (empty)
  - MIN_OUTBOUND_INTERVAL_S=0, NVU_CONNECT_RESERVE_S=0
- Compose md5: f493494e — unchanged

## Analysis

### R857/R858 commit: zero config impact
- Commit `a6f2187` added `deploy_artifacts/` test files + `memory/` (45 markdown files)
- **No docker-compose.yml changes, no gateway code changes in the repo**
- The R857/R858 code fixes (mode_idx stall-reset, rr_us, chain budget) were applied to the container ~3h ago, but these are NOT reflected in the git commit — they're runtime hotfixes
- HM1's live compose md5 `f493494e` is unchanged from R1387

### 6h data: identical to R1387
- R1387: 41/30/73.2% SR — R1388: 41/30/73.2% SR (identical)
- Both rounds: 9 zombie, 2 ATE, 1 tier_attempt, 0 fallback
- Same dsv4p_nv burst pattern (18:02-18:03 ATE, 18:09-18:10 recovery)
- This is effectively a double-dispatch — same data window, same analysis

### zombie_empty_completion: unchanged
- 9 glm5_2_nv integrate zombies, code-level
- Gateway detection+error-chunk mechanism correct
- NVCF content-filter returns stop+12-22chars for 157K+ input_chars
- Not config-fixable

### dsv4p_nv ATE: transient, self-recovered
- 2 ATE in 2-minute window (18:02-18:03), 4 subsequent OK (18:09-18:10)
- NVCF pexec function momentarily degraded for specific keys (k3 empty, k4 empty, k5 timeout)
- FASTBREAK=1 correctly aborted after 1 timeout (saved remaining keys)
- NVU_EMPTY_200_FASTBREAK=2: k3/k4 empty cycled to next key (not fast-broken, 1 empty < 2 threshold)
- ms_gw fallback attempted but timed out at 253-254s (NVU_MS_GW_FALLBACK_TIMEOUT=195 but relay took 253s — code-level relay doesn't respect timeout)
- TIER_TIMEOUT_BUDGET_S=205 sufficient (106s consumed)

### All params floor/optimal
- FASTBREAK=1 for function-level signals (pexec timeout, integrate timeout) — validated by 547+ rounds
- FASTBREAK=2 for key-specific empty_200 — validated by R1031
- TIER_COOLDOWN_S=15 — minimal, validated by R1103
- TIER_BUDGET_DSV4P_NV=106 — adequate for ~100s pexec requests
- PEER_FB_SKIP_MODELS=empty — peer-fallback enabled for all models
- No parameter has room to go lower without risking regression

## Optimization Decision: NOP
- **Real trigger but zero config changes**: commit a6f2187 adds memory/ files only, no compose or gateway code changes
- **Data identical to R1387**: 41/30/73.2% SR, same zombie/ATE pattern, same hourly distribution
- **9 zombie**: code-level, not config-fixable
- **2 ATE**: transient NVCF function turbulence, self-recovered within 6 minutes
- **All params floor/optimal**: no room for further reduction
- **Compose md5**: f493494e unchanged
- **ms_gw**: 3/3 OK, healthy
- 547th consecutive chain of R1133 NOP pattern

## Verification
- docker-compose.yml md5: f493494e (unchanged)
- No compose edit, no restart
- 铁律: 只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
