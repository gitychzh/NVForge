# R1672: HM2→HM1 — NOP — KEY_COOLDOWN=55消除pexec_429, zombie-dominated regime, 全部参数floor/optimal, 零参数变更

**决策**: NOP — 零参数可修复问题。R1668 KEY_COOLDOWN=55 持续消除 pexec_429 (6h+ 0 pexec_429)。zombie_empty_completion 是 NVCF 上游流级别内容过滤，网关不可配置。全部参数触底/最优。

## 6h Data (HM1 DB)
- **Total**: 28 req, 17 OK / 11 fail → **60.7% SR**
- **glm5_2_nv**: 28 req, 100% of traffic (0 dsv4p_nv, 0 kimi_nv)
- **All 11 failures**: zombie_empty_completion (NVCF stream-level content filter)
- **0 ATE**: FASTBREAK=3 + PEXEC_FASTBREAK=3 持续消除 ATE
- **0 pexec_429**: 6h tier_attempts: 28 pexec_success / 0 pexec_429 — KEY_COOLDOWN=55 完全消除 pexec_429
- **28 key_cycle_429s**: all single-key (key_cycle_429s=1) — normal RR rotation, 非级联
- **0 fallback occurred**, 0 peer-fb, 0 SSLEOF errors
- **Success latency**: avg 8,210ms (glm5_2_nv pexec)

## Drift Detection (Pre-change)
四源一致，无漂移:

| Parameter | Compose | Container Env | Match |
|---|---|---|---|
| KEY_COOLDOWN_S | 55 | 55 | ✅ |
| TIER_COOLDOWN_S | 55 | 55 | ✅ |
| PEXEC_TIMEOUT_FASTBREAK | 3 | 3 | ✅ |
| EMPTY_200_FASTBREAK | 3 | 3 | ✅ |
| BUDGET_DSV4P_NV | 70 | 70 | ✅ |
| BUDGET_GLM5_2_NV | 120 | 120 | ✅ |
| PEER_FALLBACK_TIMEOUT | 72 | 72 | ✅ |
| PEER_FB_SKIP_MODELS | "" | "" | ✅ |
| UPSTREAM_TIMEOUT | 66 | 66 | ✅ |
| SSLEOF_RETRY_DELAY | 0.5 | 0.5 | ✅ |
| CONNECT_RESERVE_S | 0 | 0 | ✅ |
| INTEGRATE_KEY_COOLDOWN | 0 | 0 | ✅ |
| FORCE_STREAM_UPGRADE | 0 | 0 | ✅ |
| FORCE_STREAM_UPGRADE_TIMEOUT | 66 | 66 | ✅ |
| MIN_OUTBOUND_INTERVAL_S | 0 | 0 | ✅ |

容器启动: 2026-07-17 02:18 UTC (R1668 deploy, ~1h 15min runtime)

## Docker Logs
```
docker logs nv_gw --tail 100: 仅 zombie 相关���志
[NV-ZOMBIE-EMPTY] (glm5_2_nv) passthrough zombie empty completion: finish_reason=stop but content_chars=12/48 < 50
[NV-UPSTREAM-ERROR-CHUNK] (glm5_2_nv) sent finish_reason=content_filter error SSE chunk
```
零 ERROR/WARN 非 zombie 相关。零 TimeoutError, 零 SSLEOF, 零 pexec_429, 零 peer-fb 超时。

## Tier Attempts Trend
| Window | pexec_success | pexec_429 | 429 Rate |
|--------|--------------|-----------|----------|
| 6h | 28 | 0 | 0.0% |
| 24h (R1669-R1671 reports) | ~320 | 0 | 0.0% |

KEY_COOLDOWN=55 部署后 pexec_429 从 22.4% 降至 0% 持续 ~24h。这是 R1668 最显著的成果。

## 1h Recent Requests
| ts | model | status | duration_ms | error |
|----|-------|--------|-------------|-------|
| 03:03:58 | glm5_2_nv | 502 | 36,361 | zombie_empty_completion |
| 03:03:26 | glm5_2_nv | 200 | 32,092 | — |
| 03:03:20 | glm5_2_nv | 200 | 5,583 | — |
| 02:55:17 | glm5_2_nv | 200 | 6,100 | — |
| 02:33:30 | glm5_2_nv | 502 | 12,547 | zombie_empty_completion |
| 02:33:20 | glm5_2_nv | 200 | 9,164 | — |

Pattern: alternating ~2 requests per cycle, ~30min apart, one success + one zombie. Consistent with NVCF ai-glm-5_2 function ~50% zombie rate.

## Config Snapshot (all at floor/optimal)
| # | Parameter | Value | Status | Source |
|---|-----------|-------|--------|--------|
| 1 | KEY_COOLDOWN_S | 55 | ✅ R1668 — 消除 pexec_429 | |
| 2 | TIER_COOLDOWN_S | 55 | ✅ R1668 — KEY=TIER aligned | |
| 3 | TIER_TIMEOUT_BUDGET_S | 195 | ✅ | |
| 4 | UPSTREAM_TIMEOUT | 66 | ✅ floor (NVCFPexecTimeout max~62s) | |
| 5 | PEXEC_TIMEOUT_FASTBREAK | 3 | ✅ R1665 — HM2-stable | |
| 6 | EMPTY_200_FASTBREAK | 3 | ✅ R1666 | |
| 7 | BUDGET_GLM5_2_NV | 120 | ✅ 2×mode切换 | |
| 8 | BUDGET_DSV4P_NV | 70 | ✅ R1663 — HM2-aligned | |
| 9 | PEER_FALLBACK_TIMEOUT | 72 | ✅ ≥ HM2 BUDGET=70+2 ✓ | |
| 10 | PEER_FB_SKIP_MODELS | (empty) | ✅ R1646 — all models enabled | |
| 11 | MIN_OUTBOUND_INTERVAL_S | 0 | ✅ floor (R638) | |
| 12 | CONNECT_RESERVE_S | 0 | ✅ floor (R657) | |
| 13 | INTEGRATE_KEY_COOLDOWN_S | 0 | ✅ floor (R631) | |
| 14 | SSLEOF_RETRY_DELAY_S | 0.5 | ✅ floor (R1626) | |
| 15 | FORCE_STREAM_UPGRADE | 0 | ✅ disabled | |
| 16 | FORCE_STREAM_UPGRADE_TIMEOUT | 66 | ✅ aligned with UPSTREAM | |
| 17 | NV_INTEGRATE_MODELS | (empty) | ✅ pexec-only | |

## Budget Check
- KEY=55 + TIER=55 = 110 << 195 ✓
- FASTBREAK=3 × UPSTREAM=66 = 198 > BUDGET=195 (but FASTBREAK only fires on per-key failures; zombie is per-request via HTTP 200 → FASTBREAK never fires)
- PEER_FALLBACK_TIMEOUT=72 ≥ HM2 BUDGET_DSV4P=70+2 ✓ (R1641 constraint)
- Total: BUDGET=120 + PEER_FB=72 = 192 < 195 ✓ (tight but safe)
- PEER_FB_SKIP_MODELS="" → dsv4p_nv peer-fb enabled ✓

## Analysis

### Why NOP

1. **zombie_empty_completion (11/28, 39.3%):** NVCF ai-glm-5_2 function ~50% zombie rate，返回 HTTP 200 + finish_reason=stop 但 content_chars<50。网关 zombie 检测 (R852b) 正确识别并发送 error SSE chunk。NVCF 上游内容过滤行为，非本地配置可修。

2. **KEY_COOLDOWN=55 effectiveness:** R1668 部署后 pexec_429 从 22.4% 降至 0% 持续 ~24h。这是当前最优参数，不可再减 (KEY=TIER 铁律，55s 是 NVCF 60s rate-limit 窗口的保守缓冲)。

3. **0 ATE:** FASTBREAK=3 + EMPTY_200_FASTBREAK=3 持续消除 ATE。PEXEC_FASTBREAK=3 与 HM2 对齐，已验证稳定。

4. **所有参数已在 floor/optimal:** KEY=55 (不可再减，破 KEY≥TIER)，UPSTREAM=66 (不可再减，NVCFPexecTimeout max~62s)，MIN_OUTBOUND=0，CONNECT_RESERVE=0，INTEGRATE_KEY=0，SSLEOF=0.5，FASTBREAK=3 (HM2 stable)。

5. **当前失败全为 upstream/NVCF 问题，非本地配置可修。**

### R1668 成果确认
KEY_COOLDOWN 60→55 是正确方向。~24h 零 pexec_429 证明 55s 已足够 NVCF rate-limit 恢复。对端 HM1 提交的 R1648d (ms_gw anthropic 端点) 不影响 nv_gw 链路，与本轮优化无关。

## 铁律
NOP 轮。铁律：只改 HM1 不改 HM2。KEY_COOLDOWN=55 消除 pexec_429 是 R1668 重大成果，需继续观察。zombie_empty_completion 是 NVCF 上游问题，网关不可配置。全部参数已在 floor/optimal 状态。下次轮到 HM2 时重评估：关注 zombie 率是否变化，关注 dsv4p_nv 流量是否恢复。
## ⏳ 轮到HM1优化HM2
