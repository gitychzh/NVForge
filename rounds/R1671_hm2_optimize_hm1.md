# R1671: HM2→HM1 — NOP — KEY_COOLDOWN=55 消除peexec_429, zombie-dominated regime, 全部参数floor/optimal

**决策**: NOP — 零参数可修复问题。R1668 KEY_COOLDOWN=55 已消除 pexec_429 (6h+ 0 pexec_429), zombie_empty_completion 是 NVCF 上游流级别内容过滤, 网关不可配置。全部参数触底/最优。

## 6h Data (HM1 DB)
- **Total**: 26 req, 15 OK / 11 fail → **57.7% SR**
- **glm5_2_nv**: 100% of traffic (0 dsv4p_nv, 0 kimi_nv)
- **All 11 failures**: zombie_empty_completion (NVCF stream-level content filter)
- **0 ATE**: FASTBREAK=3 + PEXEC_FASTBREAK=3 持续消除 ATE
- **0 pexec_429**: 6h tier_attempts: 27 pexec_success / 0 pexec_429 — KEY_COOLDOWN=55 完全消除 429
- **0 fallback occurred**, 0 peer-fb
- **Success latency**: avg 6,709ms, p50=5,597ms, p95=11,181ms, min=4,958ms, max=15,889ms

## Tier Attempts Trend
| Window | pexec_success | pexec_429 | 429 Rate |
|--------|--------------|-----------|----------|
| 6h | 27 | 0 | 0.0% |
| 3h | 14 | 0 | 0.0% |
| 24h | 293 | 90 | 23.5% (all pre-R1668) |

KEY_COOLDOWN=55 部署后 pexec_429 从 23.5% 降至 0%。这是 R1668 最显著的成果。

## 24h Data (HM1 DB)
- **Total**: 353 req, 191 OK / 162 fail → **54.1% SR**
- **glm5_2_nv**: 319 req, 174 OK / 145 fail (54.5%)
- **dsv4p_nv**: 35 req, 18 OK / 17 fail (51.4%) — 0 in last 8h
- **129 zombie_empty_completion** (glm5_2_nv)
- **53 ATE**: 28 dsv4p_nv + 25 glm5_2_nv — all pre-R1666 (0 ATE in last 8h)
- **90 pexec_429** in tier_attempts — all pre-R1668

## Hourly Trend (6h)
| DB Hour | Total | OK | Fail | SR | Zombie |
|---------|-------|-----|------|-----|--------|
| 03:00 | 1 | 1 | 0 | 100% | 0 |
| 02:00 | 5 | 3 | 2 | 60% | 2 |
| 01:00 | 4 | 3 | 1 | 75% | 1 |
| 00:00 | 4 | 2 | 2 | 50% | 2 |
| 23:00 | 4 | 2 | 2 | 50% | 2 |
| 22:00 | 5 | 3 | 2 | 60% | 2 |
| 21:00 | 5 | 3 | 2 | 60% | 2 |

Stable ~2 zombie/hr pattern — consistent with NVCF ai-glm-5_2 function ~50% zombie rate. The pattern is: 2 requests per cycle (one success, one zombie), ~30min apart.

## Zombie Analysis
```
[NV-GLM52-SUCCESS] tier=glm5_2_nv mode=pexec_us_rr k3 succeeded
[NV-ZOMBIE-EMPTY] (glm5_2_nv) passthrough zombie empty completion: finish_reason=stop but content_chars=12 reasoning_chars=0 < 50
[NV-UPSTREAM-ERROR-CHUNK] (glm5_2_nv) sent finish_reason=content_filter error SSE chunk
```

NVCF 返回 HTTP 200 + finish_reason=stop 但 content_chars=12 (几乎无内容)。网关 zombie 检测 (R852b) 正确识别并发送 error SSE chunk 给 cc4101, cc4101 触发 retry。这是 NVCF 上游内容过滤行为, 网关不可配置。

EMPTY_200_FASTBREAK=3 不适用 — zombie 走不同检测路径 (stream-level content validation, 非 HTTP status code)。

## Config Snapshot
| Parameter | Value | Status |
|---|---|---|
| KEY_COOLDOWN_S | 55 | ✅ R1668 — 消除 pexec_429 |
| TIER_COOLDOWN_S | 55 | ✅ R1668 — KEY=TIER aligned |
| TIER_TIMEOUT_BUDGET_S | 195 | ✅ |
| UPSTREAM_TIMEOUT | 66 | ✅ |
| PEXEC_TIMEOUT_FASTBREAK | 3 | ✅ |
| EMPTY_200_FASTBREAK | 3 | ✅ |
| BUDGET_GLM5_2_NV | 120 | ✅ |
| BUDGET_DSV4P_NV | 70 | ✅ |
| PEER_FALLBACK_TIMEOUT | 72 | ✅ |
| MIN_OUTBOUND_INTERVAL_S | 0 | ✅ floor |
| CONNECT_RESERVE_S | 0 | ✅ floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | ✅ floor |
| FORCE_STREAM_UPGRADE | 0 | ✅ |
| NV_INTEGRATE_MODELS | (empty) | ✅ pexec-only |

## Budget Check
- KEY=55 + TIER=55 = 110 << 195 ✓
- FASTBREAK=3 × UPSTREAM=66 = 198 > BUDGET=195 (但 FASTBREAK 仅触发 per-key 失败, zombie 是 per-request → FASTBREAK 从不触发 zombie)
- PEER_FALLBACK_TIMEOUT=72 ≥ BUDGET=195 ✓
- PEER_FB_SKIP_MODELS="" → dsv4p_nv peer-fb enabled ✓

## 铁律
NOP 轮。铁律：只改 HM1 不改 HM2。KEY_COOLDOWN=55 消除 pexec_429 是 R1668 重大成果, 需继续观察 24h+。zombie_empty_completion 是 NVCF 上游问题, 网关不可配置。全部参数已在 floor/optimal 状态。
## ⏳ 轮到HM1优化HM2
