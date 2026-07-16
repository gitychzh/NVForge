# R1615: HM2→HM1 — NOP (all params floor/optimal, peer-fb rescue 1/2, zombie only other failure)

**时间**: 2026-07-16 12:15 UTC
**容器**: nv_gw Up ~2.5h (started 03:50 UTC)
**6h DB**: 8 req/5 OK 62.5% SR

## 数据

| 模型 | 请求 | OK | 502 | SR% | 错误类型 |
|------|------|-----|-----|-----|---------|
| dsv4p_nv | 4 | 3 | 1 | 75.0 | all_tiers_exhausted (peer-fb rescued 2/3, 1 peer-fb TimeoutError) |
| glm5_2_nv | 4 | 2 | 2 | 50.0 | zombie_empty_completion |

## 错误分析

- **2 zombie (glm5_2_nv)**: NVCF content-filter, avg input 225K chars, avg dur 9971ms. Not config-fixable.
- **3 dsv4p ATE**: 504_nv_gateway_timeout (NVCF function-level), BUDGET=66 floor pattern → k1-504(~62s)→exhaust→peer-fb.
  - Peer-fb 2/3: 2 OK (ttfb=8ms, 1310 bytes), 1 FAILED (TimeoutError 66085ms = NVU_PEER_FALLBACK_TIMEOUT=66). HM2 nv_gw didn't respond — peer-fb timeout is at floor (66=UPSTREAM_TIMEOUT).
- **1 dsv4p ATE → peer-fb failed**: 63s local + 66s peer-fb = 129s total → 502. This is HM2-side slowness, not config-fixable on HM1.
- **ms_gw**: 2/2 OK 100% (healthy).
- **0 tier_attempts failures** (only pexec_success). Clean key pool.
- **0 empty_200** (NV-EMPTY-FASTBREAK empty). No key cycling errors.
- **0 429, 0 SSLEOF**. No per-key issues.

## 配置状态

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | floor |
| TIER_TIMEOUT_BUDGET_S | 205 | adequate (205-66=139s for peer-fb/ms_gw) |
| TIER_COOLDOWN_S | 15 | stable (R1103 revert) |
| KEY_COOLDOWN_S | 25 | stable |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | code-level no-op (R1039), but no empty_200 in window |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | floor (=UPSTREAM_TIMEOUT, BUDGET Floor Pattern) |
| NVU_TIER_BUDGET_GLM5_2_NV | 120 | adequate |
| NVU_PEER_FB_SKIP_MODELS | "" | all models enabled |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms | dsv4p_nv removed (R1609) |
| NVU_PEER_FALLBACK_ENABLED | 1 | active |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | floor (=UPSTREAM_TIMEOUT) |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor (R631) |

## 决策: NOP

**理由**: 所有参数处于 floor/optimal 状态。仅有 failures 是 zombie (NVCF content-filter, 不可配置修复) 和 1 个 peer-fb TimeoutError (HM2 nv_gw 未在 66s 内响应, 不可从 HM1 配置修复)。dsv4p ATE 由 peer-fb 2/3 成功救援。ms_gw 2/2 100% SR。compose md5 a4138248 与 R1614 相同。容器 env 与 compose 一致。无优化空间。

**铁律**: 只改HM1不改HM2 ✓

## ⏳ 轮到HM1优化HM2
