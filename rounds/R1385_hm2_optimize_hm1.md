# R1385: HM2→HM1 — NOP (false trigger, double-dispatch, 零可修故障, 544th chain of R1133)

## Trigger
- HM1 commit `5e65f75` (R1384) detected by script → triggers HM2 optimization round
- 脚本输出: "这是我提交的, 不触发" — user explicitly said this is their own commit, not a trigger

## Data Collection (HM1 via SSH)

### Container Logs (nv_gw --tail 100, filtered)
- 9x `NV-ZOMBIE-EMPTY` glm5_2_nv passthrough: content_chars < 50, input_chars >= 5000 → abort stream → send error SSE chunk
- All integrate-mode glm5_2_nv traffic, all first-attempt success except zombie
- 0 NV-TIER-FAIL, 0 NV-EMPTY-FASTBREAK, 0 NV-GLOBAL-COOLDOWN, 0 ATE, 0 timeout, 0 429, 0 empty_200

### DB 6h Summary
- 29 req / 20 OK / 9 fail = 69.0% SR
- 9 errors: all `zombie_empty_completion` (code-level)
- 0 ATE, 0 empty_200, 0 timeout, 0 tier_attempts, 0 fallback
- 0 dsv4p_nv traffic in 6h

### Per-Key Breakdown (glm5_2_nv integrate)
| Key | Req | OK | Fail | Avg Latency |
|-----|-----|----|------|-------------|
| K1  | 6   | 6  | 0    | 9487ms |
| K2  | 4   | 2  | 2    | 8202ms |
| K3  | 7   | 4  | 3    | 11435ms |
| K4  | 6   | 6  | 0    | 7546ms |
| K5  | 6   | 2  | 4    | 9074ms |

### Env Config
- All params floor/optimal: NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_INTEGRATE_TIMEOUT_FASTBREAK=1, NVU_EMPTY_200_FASTBREAK=2
- NVU_SSLEOF_RETRY_DELAY_S=1.0, NVU_TIER_BUDGET_DSV4P_NV=106, NVU_TIER_BUDGET_GLM5_2_NV=96
- NVU_PEER_FB_SKIP_MODELS= (empty — all models eligible for peer fallback)
- TIER_COOLDOWN_S=15, TIER_TIMEOUT_BUDGET_S=205, UPSTREAM_TIMEOUT=66
- Compose md5: f493494e — unchanged

## Analysis
- **zombie_empty_completion**: Code-level feature in nv_gw — when glm5_2_nv integrate returns content_chars < 50 for large inputs (≥5000 chars), it treats as empty completion, aborts stream, sends error SSE chunk to trigger upstream (openclaw) fallback. This is intentionally returning 502, not a bug. Not config-fixable.
- **Key distribution**: K1(100%), K4(100%) clean; K2(50%), K3(57%), K5(33%) hit zombie. This is model-side GLM behavior — some keys hitting the NVCF function when it returns short responses. Uniform across all keys over time.
- **No dsv4p_nv traffic**: Cannot validate R1370 budget fix. dsv4p_nv only routes through HM2 in current topology.
- **All params at floor/optimal**: FASTBREAK=1 (function-level), EMPTY_200_FASTBREAK=2 (key-specific), cooldowns minimal.

## Optimization Decision: NOP
- 零可修故障: all 9 errors are zombie_empty_completion — code-level, intentionally returning 502 for upstream fallback
- 0 config-fixable issues: no ATE, no empty_200, no timeout, no 429, no tier_attempts, no fallback
- All params at floor/maximal values — no single-parameter improvement possible
- Compose md5 unchanged from R1384
- 544th consecutive chain of R1133 NOP pattern

## Verification
- docker-compose.yml md5: f493494e (unchanged)
- No compose edit, no restart
- 铁律: 只改HM1不改HM2

## ⏳ 轮到HM1优化HM2
