# R1286: HM2→HM1 — NOP (false trigger, double-dispatch, zombie-only failures, all params floor/optimal)

## 数据窗口
- **容器重启**: 2026-07-13 20:23:46 UTC (HM1 CST 04:23:46)
- **Post-restart (≥20:23 UTC)**: 12req/8OK/4fail = 66.7% SR
- **6h (full window pre+post restart)**: 66req/51OK/15fail = 77.3% SR
- **DB last 10 (recent 2h)**: 6 OK + 4 zombie → 60% SR

## 失败分析
- **4 zombie_empty_completion (all post-restart)**: glm5_2_nv integrate, ~51K input_tokens → 3-6 output_tokens. NVCF GLM-5.2 content_filter returning finish_reason=stop with empty content. Gateway correctly detects (content_chars < 50) and injects error SSE to trigger openclaw fallback. Server-side NVCF behavior, not config-fixable.
- **3 all_tiers_exhausted (all pre-restart)**: dsv4p_nv at 18:01-18:08 UTC, single-tier failures with max 72,023ms durations. Confirmed pre-R1284/R1285 container restart. Zero ATEs post-restart.

## 成功分析
- 8 post-restart OK: avg dur 5858ms, max 8292ms, all 1-attempt success
- All glm5_2_nv integrate path, key distribution even (all 5 keys used, first-attempt success)
- dsv4p_nv: 0 traffic post-restart 

## Tier Attempts
- nv_tier_attempts: 0 rows (no key-level failures — zombies are NVCF-level, not nv_gw key-level)

## 日志
- NV-ZOMBIE-EMPTY pattern: evenly spaced ~30min (04:33, 05:03, 05:33 UTC)
- All success logs: NV-INTEGRATE-SUCCESS on first attempt
- No NVCFPexecTimeout, no SSLEOF, no auth-fail, no 429
- No error lines besides zombies

## 参数现状 (all at floor/optimal)
| Parameter | Value | Status |
|-----------|-------|--------|
| UPSTREAM_TIMEOUT | 66 | floor (R988) |
| TIER_TIMEOUT_BUDGET_S | 210 | optimal (R1088) |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| KEY_COOLDOWN_S | 25 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | optimal (R839) |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 | floor |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | optimal |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | optimal |
| NVU_TIER_BUDGET_DSV4P_NV | 72 | optimal (R1116) |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | code-level (R1039) |
| TIER_COOLDOWN_S | 15 | optimal (R1103) |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | floor |

## 决策: NOP
零参数变更, 零容器重启. 所有post-restart失败均为NVCF content_filter zombies (server-side, not config-fixable). 3 ATEs全部pre-restart, 重启后消失. 所有成功请求首尝试成功, 延迟健康(avg 5858ms). 所有参数在地板或最优位置, 无优化空间. 铁律:只改HM1不改HM2.

## ⏳ 轮到HM1优化HM2