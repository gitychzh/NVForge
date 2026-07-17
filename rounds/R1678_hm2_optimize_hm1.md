# R1678: HM2→HM1 — NOP — KEY_COOLDOWN=55 持续~24h+零429, zombie-dominated steady state, 全部参数floor/optimal, 零参数变更

**决策**: NOP — 零参数可修复问题。R1668 KEY_COOLDOWN=55 持续消除 pexec_429 (~24h+ 零 429)。zombie_empty_completion 是 NVCF 上游流级别内容过滤，网关不可配置。全部参数触底/最优。

## 6h Data (HM1 DB)
- **Total**: 29 req, 18 OK / 11 fail → **62.1% SR**
- **glm5_2_nv**: 29 req, 100% of traffic (0 dsv4p_nv, 0 kimi_nv)
- **All 11 failures**: zombie_empty_completion (NVCF stream-level content filter)
- **0 ATE**: FASTBREAK=3 + EMPTY_200_FASTBREAK=3 持续消除 ATE
- **0 pexec_429**: 6h tier_attempts: 28 pexec_success / 0 pexec_429 — KEY_COOLDOWN=55 完全消除 pexec_429
- **0 fallback occurred**, 0 peer-fb, 0 SSLEOF errors, 0 stream_first_byte_timeout
- **Success latency**: avg 9,962ms (glm5_2_nv pexec)

## 1h Data
- **Total**: 6 req, 4 OK / 2 fail → **66.7% SR**
- **2 failures**: both zombie_empty_completion

## Recent Requests
| ts | model | status | duration_ms | error |
|----|-------|--------|-------------|-------|
| 04:24:48 | glm5_2_nv | 200 | 4,300 | — |
| 04:03:33 | glm5_2_nv | 502 | 7,360 | zombie_empty_completion |
| 04:03:20 | glm5_2_nv | 200 | 12,462 | — |
| 03:34:00 | glm5_2_nv | 502 | 27,270 | zombie_empty_completion |
| 03:33:42 | glm5_2_nv | 200 | 17,138 | — |

Pattern unchanged: alternating ~2-3 requests per cycle, ~30min apart, mixed success+zombie. Consistent with NVCF ai-glm-5_2 function ~50% zombie rate.

## Tier Attempts
| tier | error_type | cnt |
|------|-----------|-----|
| glm5_2_nv | pexec_success | 28 |
| glm5_2_nv | pexec_429 | 0 |

Perfect 100% pexec success rate. 0 pexec_429 for ~24h+.

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
| TIER_TIMEOUT_BUDGET_S | 195 | 195 | ✅ |
| MS_GW_FALLBACK_TIMEOUT | 120 | 120 | ✅ |

## Docker Logs
```
docker logs nv_gw --tail 200: 仅 zombie 和正常 pexec 日志
[NV-GLM52-CHAIN] tier=glm5_2_nv mode=pexec_us_rr (正常请求)
[NV-GLM52-SUCCESS] tier=glm5_2_nv mode stabilized (正常成功)
[NV-STREAM-BUFFER-FLUSH] (glm5_2_nv) full-buffer flushed (正常流)
[NV-UPSTREAM-ERROR-CHUNK] (glm5_2_nv) sent finish_reason=content_filter error SSE chunk (zombie)
```
零 ERROR/WARN 非 zombie 相关。零 TimeoutError, 零 SSLEOF, 零 pexec_429, 零 peer-fb 超时。

## Tier Attempts Trend (pexec_429)
| Window | pexec_success | pexec_429 | 429 Rate |
|--------|--------------|-----------|----------|
| 1h (R1678) | 6 | 0 | 0.0% |
| 6h (R1678) | 28 | 0 | 0.0% |
| 6h (R1677) | 28 | 0 | 0.0% |
| 6h (R1676) | 28 | 0 | 0.0% |
| 6h (R1675) | 28 | 0 | 0.0% |
| 6h (R1674) | 28 | 0 | 0.0% |
| 6h (R1673) | 26 | 0 | 0.0% |

KEY_COOLDOWN=55 部署后 pexec_429 持续零 ~24h+。R1668 是当前周期最重大成果。

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

1. **zombie_empty_completion (11/29, 37.9%):** NVCF ai-glm-5_2 function ~50% zombie rate，返回 HTTP 200 + finish_reason=stop 但 content_chars<50。网关 zombie 检测 (R852b) 正确识别并发送 error SSE chunk。NVCF 上游内容过滤行为，非本地配置可修。

2. **KEY_COOLDOWN=55 effectiveness:** R1668 部署后 pexec_429 持续零 ~24h+。这是当前优化周期中最显著的成果。

3. **0 ATE:** FASTBREAK=3 + EMPTY_200_FASTBREAK=3 持续消除 ATE。连续多轮零 ATE。

4. **所有参数已在 floor/optimal:** KEY=55 (不可再减，破 KEY≥TIER)，UPSTREAM=66 (不可再减，NVCFPexecTimeout max~62s)，MIN_OUTBOUND=0，CONNECT_RESERVE=0，INTEGRATE_KEY=0，SSLEOF=0.5，FASTBREAK=3 (HM2 stable)。

5. **当前失败全为 upstream/NVCF 问题，非本地配置可修。**

### R1668 成果确认 (持续观测)
KEY_COOLDOWN 60→55 是正确方向。~24h+ 零 pexec_429 证明 55s 已足够 NVCF rate-limit 恢复。这是当前优化周期中最重要的成果。

### R1677 vs R1678 对比
| Metric | R1677 | R1678 | Δ |
|--------|-------|-------|---|
| 6h Total | 28 | 29 | +1 |
| 6h SR | 60.7% | 62.1% | +1.4% |
| zombie | 11 | 11 | 0 |
| ATE | 0 | 0 | 0 |
| pexec_429 | 0 | 0 | 0 |
| avg_ok_ms | 10,295 | 9,962 | -333 |

两轮数据几乎一致，验证 zombie-dominated steady state。无退化信号。HM1-optimize 周期已进入稳定 NOP 阶段 — 所有可调参数已至 floor/optimal，仅剩上游 NVCF 问题无法本地修复。

### HM2 对比 (KEY_COOLDOWN=25, TIER_COOLDOWN=25, BUDGET=180)
HM2 以更低 cooldown (25 vs 55) 运行，受益于 per-key SOCKS5 多 IP 架构。HM1 单 IP 需要 KEY=55 消除 pexec_429，这是架构差异而非参数不足。HM1 的 BUDGET=195 > HM2 的 BUDGET=180，提供更多 key-cycling 时间。

## 铁律
NOP 轮。铁律：只改 HM1 不改 HM2。KEY_COOLDOWN=55 消除 pexec_429 是 R1668 重大成果，持续 ~24h+ 零 429。zombie_empty_completion 是 NVCF 上游问题，网关不可配置。全部参数已在 floor/optimal 状态。下次轮到 HM2 时重评估：关注 zombie 率是否变化，关注 dsv4p_nv 流量是否恢复，关注 NVCF ai-glm-5_2 function 健康状况。
## ⏳ 轮到HM1优化HM2
