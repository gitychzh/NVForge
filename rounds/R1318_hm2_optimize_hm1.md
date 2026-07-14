# R1318: HM2→HM1 — NOP (false trigger, double-dispatch, 32nd consecutive post-R1286)

**Trigger**: HM1 commit "这是我提交的, 不触发" → HM1 bot's own commit, not a genuine config change.

## HM1 Data (6h)

| Metric | Value |
|--------|-------|
| Total requests | 58 |
| OK (200) | 51 |
| Fail (502) | 7 |
| SR | 87.9% |
| Error type | 7 zombie_empty_completion |
| Tier attempts | 0 |
| ATE | 0 |
| IncompleteRead | 0 |
| Fallback | 0 |
| ms_gw SR | 13/13 100% |

## Hourly SR

| Hour (UTC) | Total | OK | Fail | SR |
|------------|-------|-----|------|------|
| 22:00 | 7 | 5 | 2 | 71.4% |
| 23:00 | 6 | 5 | 1 | 83.3% |
| 00:00 | 6 | 5 | 1 | 83.3% |
| 01:00 | 29 | 28 | 1 | 96.6% |
| 02:00 | 5 | 5 | 0 | 100.0% |
| 03:00 | 5 | 3 | 2 | 60.0% |

## Log Analysis

All traffic: glm5_2_nv integrate only. All integrate attempts succeed on first key (no tier cycling). 3 NV-ZOMBIE-EMPTY events detected in docker logs tail (content_chars=12/46 < 50, input_chars=175K+, NVCF content-filter). Gateway correctly aborts zombie streams. Zero errors/warnings besides zombie-empty.

## Config State

All params at floor/optimal — no tuning headroom:

| Param | Value | Status |
|-------|-------|--------|
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | optimal |
| TIER_COOLDOWN_S | 15 | floor |
| UPSTREAM_TIMEOUT | 66 | optimal |
| TIER_TIMEOUT_BUDGET_S | 205 | safe |
| NVU_PEER_FB_SKIP_MODELS | "" | all enabled |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| KEY_COOLDOWN_S | 25 | optimal |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | optimal |
| NVU_TIER_BUDGET_DSV4P_NV | 72 | safe |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | safe |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | safe |
| NVU_MS_GW_FALLBACK_TIMEOUT | 195 | safe |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | optimal |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | safe |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 | safe |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | safe |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | optimal |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| NVU_FORCE_STREAM_UPGRADE | 0 | disabled |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | aligned |

## Decision: NOP

All 7 failures are zombie_empty_completion — NVCF content-filter returning near-empty completions (content_chars < 50), not config-fixable. All params are at floor/optimal. No config change needed. Compose md5 6e1b58bc stable.

铁律:只改HM1不改HM2

## ⏳ 轮到HM1优化HM2