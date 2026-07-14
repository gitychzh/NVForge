# R1386: HM2→HM1 — NOP (false trigger, double-dispatch, dsv4p_nv traffic restored, 2 ATE instantaneous, 545th chain of R1133)

## Trigger
- 脚本输出: "这是我提交的, 不触发" — user explicitly said this is their own commit, not a trigger
- GitHub latest commit author: `opc2_uname` (HM2 self-commit `7bedb0e`)
- HM1 git: stuck at R1206 (179 rounds behind), last HM1-authored commit `7625e14` (R818)
- ⚠️ Despite false trigger, data shows significant change: dsv4p_nv traffic restored on HM1 — must analyze

## Data Collection (HM1 via SSH)

### Container Logs (nv_gw --tail 100, filtered)
- 6x `NV-ZOMBIE-EMPTY` glm5_2_nv passthrough: content_chars < 50, input_chars >= 5K → abort stream → error SSE chunk
- **NEW**: dsv4p_nv pexec traffic! 2x ATE observed:
  - `[NV-EMPTY-200]` k4 dsv4p_nv → empty_cycle → cycling to k5
  - `[NV-TIMEOUT]` tier=dsv4p_nv k4 NVCF pexec timeout: attempt=44473ms total=106029ms → pexec fastbreak
  - `[NV-ALL-TIERS-FAIL]` dsv4p_nv all 5 keys failed: 429=0, empty200=1, timeout=1, other=0 → ABORT-NO-FALLBACK
  - 2nd ATE pattern identical (k5 timeout, fastbreak)
- `[NV-MS-FB]` ms_gw same-model fallback attempted for dsv4p_ms, timed out after 253491ms
- `[NV-THINKING-TIMEOUT]` dsv4p_nv thinking request stream=True → extended timeout 66s
- 0 NV-EMPTY-FASTBREAK, 0 NV-GLOBAL-COOLDOWN

### DB 6h Summary
- 35 req / 26 OK / 9 fail = **74.3% SR** (↑ from R1385: 29/20/69.0%)
- 9 errors: all `zombie_empty_completion` (glm5_2_nv, code-level)
- 2 `all_tiers_exhausted` (dsv4p_nv pexec, empty_200+timeout)
- 1 tier_attempt: dsv4p_nv empty_200 k4
- 0 fallback_occurred, 0 empty_200 (in DB), 0 timeout (in DB error_type)

### Per-Model Breakdown
| Model | Req | OK | Fail | SR% | Avg Lat |
|-------|-----|----|------|-----|---------|
| glm5_2_nv | 30 | 21 | 9 | 70.0% | 9196ms |
| dsv4p_nv | 11 | 9 | 2 | 81.8% | 44176ms |

### Per-Key Breakdown (glm5_2_nv integrate)
| Key | Req | OK | Fail | Avg Lat | Zombie |
|-----|-----|----|------|---------|--------|
| K0 | 7 | 7 | 0 | 14542ms | 0 |
| K1 | 5 | 3 | 2 | 14892ms | 2 |
| K2 | 9 | 6 | 3 | 12325ms | 3 |
| K3 | 6 | 6 | 0 | 7790ms | 0 |
| K4 | 8 | 4 | 4 | 20356ms | 4 |

### dsv4p_nv Detail (pexec, all 11 reqs)
- 9 OK: avg 38445ms (range 12116–93865ms), all key_cycle_429s=0
- 1 ATE: k4 empty_200 → k5 timeout → all tiers fail (106039ms)
- 1 ATE: k5 timeout → all tiers fail (106059ms)
- After ATE burst (18:02-18:03): 3 more OK at 18:09-18:10 (34710ms, 12116ms, 33757ms) — instantaneous recovery

### ms_gw
- 3 req / 3 OK (100%), healthy
- DeepSeek-v4-pro + GLM-5.2 traffic, normal

### Env Config
- All params floor/optimal: NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_INTEGRATE_TIMEOUT_FASTBREAK=1, NVU_EMPTY_200_FASTBREAK=2
- NVU_SSLEOF_RETRY_DELAY_S=1.0, NVU_TIER_BUDGET_DSV4P_NV=106, NVU_TIER_BUDGET_GLM5_2_NV=96
- TIER_COOLDOWN_S=15, TIER_TIMEOUT_BUDGET_S=205, UPSTREAM_TIMEOUT=66
- KEY_COOLDOWN_S=25, KEY_AUTHFAIL_COOLDOWN_S=60
- NVU_PEER_FB_SKIP_MODELS= (empty)
- Compose md5: f493494e — unchanged

## Analysis

### Positive: dsv4p_nv traffic restored
- Previously 0 traffic for 15h+ (R1380-R1385), now 11 req in 6h
- 9/11 OK (81.8%), avg 38s latency — functional
- ms_gw fallback for dsv4p_ms exists but timed out on this specific request (253s)

### 2 ATE: instantaneous NVCF function turbulence
- Both ATE in the same 2-minute window (18:02-18:03), same pattern: empty_200 + timeout
- 3 subsequent requests (18:09-18:10) all OK — self-recovered
- FASTBREAK=1 working correctly (1 timeout → fastbreak, saved remaining keys)
- TIER_TIMEOUT_BUDGET_S=205 sufficient (106s consumed < 205s budget)
- NVU_EMPTY_200_FASTBREAK=2: k4 empty_200 triggered cycle (not fastbreak since only 1 empty), k5 timeout → fastbreak
- Not systematic — NVCF function-level transient, not config-fixable

### zombie_empty_completion: unchanged
- 9 glm5_2_nv integrate zombies, same as R1385
- Code-level feature: content_chars < 50 for large inputs → abort stream → error SSE chunk
- 0 dsv4p_nv zombies, 0 kimi_nv zombies

### ms_gw: healthy
- 3/3 OK, no optimization needed

## Optimization Decision: NOP
- **False trigger confirmed**: latest commit = opc2_uname (HM2 self), HM1 git at R1206
- **dsv4p_nv traffic restored**: positive development, 81.8% SR
- **2 ATE**: instantaneous NVCF turbulence, self-recovered within 6 minutes, not config-fixable
- **zombie**: 9 code-level, unchanged
- **All params floor/optimal**: FASTBREAK=1, EMPTY_200_FASTBREAK=2, cooldowns minimal
- **Compose md5**: f493494e unchanged
- **ms_gw**: healthy, no optimization space
- 545th consecutive chain of R1133 NOP pattern

## Verification
- docker-compose.yml md5: f493494e (unchanged)
- No compose edit, no restart
- 铁律: 只改HM1不改HM2

## ⏳ 轮到HM1优化HM2
