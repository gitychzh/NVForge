# R1412: HM2→HM1 — NOP (false trigger, double-dispatch, 571st chain of R1133)

## 📊 6h Data (HM1 nv_requests DB)

| Metric | Value |
|--------|-------|
| Window | last 6 hours |
| Total req | 16 |
| OK (200) | 13 |
| Fail (502) | 3 |
| SR | 81.3% |
| tier_attempts | 0 |

## 🔴 Per-Error Breakdown

| Model | Error Type | Count | Avg Duration | Config-Fixable? |
|-------|-----------|-------|-------------|-----------------|
| glm5_2_nv | zombie_empty_completion | 2 | 7624ms | ❌ code-level NVCF content-filter |
| dsv4p_nv | all_tiers_exhausted | 1 | 106052ms | ❌ NVCF-side function degradation |

## 🔍 Detailed Analysis

### zombie_empty_completion (2x glm5_2_nv)
- Content-filtered by NVCF: finish_reason=stop but content_chars < 50, input_chars >= 5000
- R1405 zombie fix active → finish_reason=timeout sent to openclaw → triggers fallback
- NVCF content-filter behavior, not config-fixable on gateway side

### dsv4p_nv ATE (1x)
- Request: 172msgs, stream=True, thinking=True, effort=high, caller=openclaw
- k4 → 504 (504_nv_gateway_timeout) 65.7s
- k5 → NVCFPexecTimeout 40.3s → FASTBREAK=1 saves remaining keys
- Total: 106s → ALL-TIERS-FAIL → ABORT-NO-FALLBACK
- ms_gw fallback: relay_started=True but TimeoutError at 198814ms
- R1103 BUDGET=106 correctly caps key cycling, but peer-fb not triggered because BUDGET consumed by 504+timeout
- 504 bypasses FASTBREAK (R1078), consumes ~66s per key → exhausts BUDGET before peer-fb can fire

### ms_gw side
- 5 req, 4 ok, 1 fail (80.0%)
- Failure: VARIANT-EXHAUSTED all 10 variants for req 1e83158e — modelscope API issue, not config-fixable

## 📋 HM1 Env (nv_gw container)

| Parameter | Value | Status |
|-----------|-------|--------|
| UPSTREAM_TIMEOUT | 66 | floor |
| TIER_TIMEOUT_BUDGET_S | 205 | oversize |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | optimal |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | optimal |
| NVU_EMPTY_200_FASTBREAK | 2 | optimal |
| NVU_TIER_BUDGET_DSV4P_NV | 106 | floor |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | floor |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | floor |
| TIER_COOLDOWN_S | 15 | floor |
| KEY_COOLDOWN_S | 25 | optimal |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_PEER_FB_SKIP_MODELS | (empty) | optimal |
| NVU_MS_GW_FALLBACK_TIMEOUT | 195 | optimal |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | optimal |
| NVU_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| NVU_FORCE_STREAM_UPGRADE | 0 | optimal |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 | optimal |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | optimal |

## 🎯 Decision: NOP

**Reason**: All three failures are non-config-fixable:

1. **zombie_empty_completion** (×2): NVCF content-filter at code level. R1405 fix is active (finish_reason=timeout). No gateway config parameter can prevent NVCF from returning content-filtered empty completions.

2. **dsv4p_nv ATE** (×1): NVCF-side function degradation. 504 gateway timeout (NVCF internal) → NVCFPexecTimeout (NVCF internal). No FASTBREAK tweak helps (504 bypasses FASTBREAK per R1078). BUDGET=106 is already at floor. ms_gw fallback timed out at 198s for a large thinking request (172msgs, thinking=True) — ms_gw timeout is inherent to ms_gw's own processing of large requests, not configurable on nv_gw side.

3. **0 tier_attempts**: No key-level errors, no cooldown cycling — proof that the key pool is healthy.

**All params at floor/optimal.** Compose md5 `f493494e` unchanged. No parameter to adjust.

**铁律: 只改HM1不改HM2** ✅ No changes to HM2.

## ⚠️ 触发分析
cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = opc2_uname (HM2)
- R1411 刚由 HM2 提交，无 HM1 新提交
- 数据与 R1411 完全一致 (16req/13OK 81.3% SR, 2 zombie + 1 ATE)
- 双派遣 (double-dispatch, R884+ pattern)
- HM1 git log 停留在 R1206 (206 rounds behind as of R1412)
## ⏳ 轮到HM1优化HM2
