# R1193: HM2→HM1 — NOP (false trigger, 61st chain of R1133, zombie-only, all params floor/optimal, NVCF content-filter not config-fixable)

**Timestamp**: 2026-07-11 16:35 UTC

**HM1 commit**: `daee0f7` — "这是我提交的, 不触发" (R1192, HM2→HM1 NOP)

## 6h DB Summary (since ~10:35 UTC, container up 21h+ since 2026-07-10T19:03:27Z)

| Metric | Value |
|--------|-------|
| 6h total | 24 req / 12 OK / 12 err → 50.0% SR |
| Model | glm5_2_nv (100%), dsv4p_nv (0), minimax_m3_nv (0) |
| Upstream | nv_integrate (100%), nv_pexec (0) |
| Error types | zombie_empty_completion: 12 (100%) |
| Tier attempts | 0 |
| Fallback | 0 |
| ms_gw | 0 traffic |
| Hourly SR | 50.0% every hour (4req: 2OK + 2 zombie) |

## Recent 10 Requests

Alternating pattern: success (200, 4-38s, 45-54 tokens) → zombie (502, 4-10s, 6 tokens) → ...

```
ts                  | status | dur_ms | error_type              | input_chars | output_tokens
08:33:39  glm5_2_nv | 502    | 10434  | zombie_empty_completion | 174874      | 6
08:33:24  glm5_2_nv | 200    | 9256   |                         | 174451      | 45
08:03:40  glm5_2_nv | 502    | 4432   | zombie_empty_completion | 174364      | 6
08:03:24  glm5_2_nv | 200    | 10323  |                         | 173756      | 53
07:34:09  glm5_2_nv | 502    | 4576   | zombie_empty_completion | 173773      | 6
07:33:24  glm5_2_nv | 200    | 38540  |                         | 173165      | 53
07:03:35  glm5_2_nv | 502    | 5642   | zombie_empty_completion | 173078      | 6
07:03:24  glm5_2_nv | 200    | 4604   |                         | 172574      | 54
06:33:38  glm5_2_nv | 502    | 6659   | zombie_empty_completion | 172383      | 6
06:33:24  glm5_2_nv | 200    | 7961   |                         | 171879      | 54
```

## Log Analysis

```
[NV-ZOMBIE-EMPTY] (glm5_2_nv) passthrough zombie empty completion:
  finish_reason=stop but content_chars=12 < 50, input_chars=174874 >= 5000, no tool_calls
  → aborting stream to trigger openclaw fallback (avoid 8min stall)
[NV-ZOMBIE-ERROR-CHUNK] (glm5_2_nv) sent finish_reason=content_filter error SSE chunk
```

- All requests succeed on first key attempt (NV-INTEGRATE-SUCCESS on attempt 1/7)
- NVCF content-filter returns `finish_reason=stop` with `content_chars=12`
- Gateway correctly detects zombie and sends error-chunk to openclaw
- input_chars growing: 171879 → 174874 (consistent growth across hours)
- Keys rotate: k1→k2→k3→k4→k5 (different key each request)

## Current HM1 Params (all at floor/optimal)

| Param | Value | Status |
|-------|-------|--------|
| TIER_TIMEOUT_BUDGET_S | 198 | floor |
| UPSTREAM_TIMEOUT | 66 | optimal |
| TIER_COOLDOWN_S | 15 | floor |
| KEY_COOLDOWN_S | 25 | near-floor |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | optimal (R1031) |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | correct (R1018) |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | stable |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_TIER_BUDGET_DSV4P_NV | 72 | stable |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | stable |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | stable |
| NVU_FORCE_STREAM_UPGRADE | 0 | floor |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | floor |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | floor |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | stable |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 | stable |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | stable |
| NVU_PEER_FALLBACK_ENABLED | 1 | correct |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | stable |
| NVU_MS_GW_FALLBACK_TIMEOUT | 180 | stable |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | stable |

## Decision: NOP

**Reasoning**:
1. All 12 errors are zombie_empty_completion — NVCF content-filter returning `finish_reason=stop` with 12 chars. Not config-fixable.
2. 0 tier_attempts — no tier failures at all. All 24 requests succeed on first key.
3. All params at floor/optimal — no tightening possible, no expanding needed.
4. dsv4p_nv: 0 traffic for 21h+ — no pexec path to tune.
5. ms_gw: 0 traffic — fallback never triggered.
6. Gateway detection+error-chunk work correctly — zombie is correctly aborted.
7. 61st consecutive chain of R1133 false triggers.

**Zero param changes. 铁律:只改HM1不改HM2**

## ⏳ 轮到HM1优化HM2