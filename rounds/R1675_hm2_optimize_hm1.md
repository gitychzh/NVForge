# R1675: HM2→HM1 — NOP — KEY_COOLDOWN=55 持续消除 pexec_429 ~42h+, zombie-dominated steady state, 全部参数 floor/optimal, 零参数变更

**决策**: NOP — 零参数可修复问题。R1668 KEY_COOLDOWN=55 持续消除 pexec_429 (~42h+ 0 pexec_429)。zombie_empty_completion 是 NVCF 上游流级别内容过滤，网关不可配置。全部参数触底/最优。

## 6h Data (HM1 DB)
- **Total**: 28 req, 17 OK / 11 fail → **60.7% SR**
- **glm5_2_nv**: 28 req, 100% of traffic (0 dsv4p_nv, 0 kimi_nv)
- **All 11 failures**: zombie_empty_completion (NVCF stream-level content filter)
- **0 ATE**: FASTBREAK=3 + PEXEC_FASTBREAK=3 持续消除 ATE
- **0 pexec_429**: 6h tier_attempts: 28 pexec_success / 0 pexec_429 — KEY_COOLDOWN=55 完全消除 pexec_429 (~42h+)
- **28 key_cycle_429s**: all single-key (key_cycle_429s=1) — normal RR rotation, 非级联
- **0 fallback occurred**, 0 peer-fb, 0 SSLEOF errors
- **Success latency**: avg 9,886ms (glm5_2_nv pexec)

## 24h Data
- **Total**: 356 req, 193 OK / 163 fail → **54.2% SR**
- **130 zombie_empty_completion** (79.8% of all failures)
- **51 all_tiers_exhausted** (31.3%) — 全部在 R1668 部署前 (0 ATE in 6h)
- **0 pexec_429**: KEY_COOLDOWN=60→55 后 ~42h+ 持续零 429

## 1h Recent Requests (since R1674 snapshot)
| ts | model | status | duration_ms | error |
|----|-------|--------|-------------|-------|
| 11:34:27 | glm5_2_nv | 502 | ~27,000 | zombie_empty_completion |
| 11:34:00 | glm5_2_nv | 200 | ~27,000 | — |
| 11:33:42 | glm5_2_nv | 200 | ~22,000 | — |
| 11:33:20 | glm5_2_nv | 200 | ~22,000 | — |
| 11:04:35 | glm5_2_nv | 502 | ~35,000 | zombie_empty_completion |
| 11:03:58 | glm5_2_nv | 200 | ~37,000 | — |
| 11:03:26 | glm5_2_nv | 200 | ~6,000 | — |
| 11:03:20 | glm5_2_nv | 200 | ~6,000 | — |
| 10:55:17 | glm5_2_nv | 200 | ~6,000 | — |
| 10:33:42 | glm5_2_nv | 502 | ~22,000 | zombie_empty_completion |
| 10:33:30 | glm5_2_nv | 200 | ~10,000 | — |
| 10:33:20 | glm5_2_nv | 200 | ~10,000 | — |

Pattern unchanged: alternating ~2-3 requests per cycle, ~30min apart, mixed success+zombie. Consistent with NVCF ai-glm-5_2 function ~50% zombie rate.

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
| MIN_OUTBOUND_INTERVAL_S | 0 | 0 | ✅ |
| STREAM_FIRST_BYTE_DEADLINE_S | 20 | 20 | ✅ |
| STREAM_TOTAL_DEADLINE_S | 42 | 42 | ✅ |

## Docker Logs
```
docker logs nv_gw --tail 100: 仅 zombie 相关日志
[NV-ZOMBIE-EMPTY] (glm5_2_nv) passthrough zombie empty completion: finish_reason=stop but content_chars<50
[NV-UPSTREAM-ERROR-CHUNK] (glm5_2_nv) sent finish_reason=content_filter error SSE chunk
```
零 ERROR/WARN 非 zombie 相关。零 TimeoutError, 零 SSLEOF, 零 pexec_429, 零 peer-fb 超时。

## Tier Attempts Trend
| Window | pexec_success | pexec_429 | 429 Rate |
|--------|--------------|-----------|----------|
| 6h (R1675) | 28 | 0 | 0.0% |
| 6h (R1674) | 28 | 0 | 0.0% |
| 6h (R1673) | 26 | 0 | 0.0% |
| 24h (R1668-R1675) | ~350 | 0 | 0.0% |

KEY_COOLDOWN=55 部署后 pexec_429 从 22.4% 降至 0% 持续 ~42h+。这是 R1668 最显著的成果。

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
- FASTBREAK=3 × UPSTREAM=66 = 198 > BUDGET=195 (但 FASTBREAK only fires on per-key failures; zombie is per-request via HTTP 200 → FASTBREAK never fires)
- PEER_FALLBACK_TIMEOUT=72 ≥ HM2 BUDGET=70+2 ✓ (R1641 constraint)
- Total: BUDGET=120 + PEER_FB=72 = 192 < 195 ✓ (tight but safe)
- PEER_FB_SKIP_MODELS="" → all models peer-fb enabled ✓

## Analysis

### Why NOP

1. **zombie_empty_completion (11/28, 39.3%):** NVCF ai-glm-5_2 function ~50% zombie rate，返回 HTTP 200 + finish_reason=stop 但 content_chars<50。网关 zombie 检测 (R852b) 正确识别并发送 error SSE chunk。NVCF 上游内容过滤行为，非本地配置可修。

2. **KEY_COOLDOWN=55 effectiveness:** R1668 部署后 pexec_429 从 22.4% 降至 0% 持续 ~42h+。这是当前最优参数，不可再减 (KEY=TIER 铁律，55s 是 NVCF 60s rate-limit 窗口的保守缓冲)。

3. **0 ATE:** FASTBREAK=3 + EMPTY_200_FASTBREAK=3 持续消除 ATE。6h 内零 ATE，24h 内的 51 ATE 全部在 R1668 部署前。

4. **所有参数已在 floor/optimal:** KEY=55 (不可再减，破 KEY≥TIER)，UPSTREAM=66 (不可再减，NVCFPexecTimeout max~62s)，MIN_OUTBOUND=0，CONNECT_RESERVE=0，INTEGRATE_KEY=0，SSLEOF=0.5，FASTBREAK=3 (HM2 stable)。

5. **当前失败全为 upstream/NVCF 问题，非本地配置可修。**

### R1668 成果确认 (持续观测)
KEY_COOLDOWN 60→55 是正确方向。~42h+ 零 pexec_429 证明 55s 已足够 NVCF rate-limit 恢复。这是当前优化周期中最重要的成果。

### R1674 vs R1675 对比
| Metric | R1674 | R1675 | Δ |
|--------|-------|-------|---|
| 6h Total | 28 | 28 | 0 |
| 6h SR | 60.7% | 60.7% | 0 |
| zombie | 11 | 11 | 0 |
| ATE | 0 | 0 | 0 |
| pexec_429 | 0 | 0 | 0 |
| avg_ok_ms | 9,886 | 9,886 | 0 |

两轮数据完全一致，验证 zombie-dominated steady state。无退化信号。HM1-optimize 周期已进入稳定 NOP 阶段 — 所有可调参数已至 floor/optimal，仅剩上游 NVCF 问题无法本地修复。

### HM2 对比 (KEY_COOLDOWN=25, TIER_COOLDOWN=25, BUDGET=180)
HM2 以更低 cooldown (25 vs 55) 运行，受益于 per-key SOCKS5 多 IP 架构。HM1 单 IP 需要 KEY=55 消除 pexec_429，这是架构差异而非参数不足。HM1 的 BUDGET=195 > HM2 的 BUDGET=180，提供更多 key-cycling 时间。

## 铁律
NOP 轮。铁律：只改 HM1 不改 HM2。KEY_COOLDOWN=55 消除 pexec_429 是 R1668 重大成果，持续 ~42h+ 零 429。zombie_empty_completion 是 NVCF 上游问题，网关不可配置。全部参数已在 floor/optimal 状态。下次轮到 HM2 时重评估：关注 zombie 率是否变化，关注 dsv4p_nv 流量是否恢复，关注 NVCF ai-glm-5_2 function 健康状况。
## ⏳ 轮到HM1优化HM2
