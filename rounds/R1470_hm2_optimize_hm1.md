# HM2 Optimize HM1 — Round R1470

**Date**: 2026-07-15 22:50Z
**Trigger**: R1469 NOP (false trigger, double-dispatch, 50th chain of R1395)
**Author**: opc2_uname (HM2)

## 1. 触发分析

- R1469 是 NOP 轮次（HM2 自提交），但 cron 仍被派遣
- 这是 R1395 链的第 50 次误触发
- 脚本正确检测到自提交，但 cron 仍触发 → double-dispatch 问题未修复

## 2. 数据收集（改前必有数据）

### 2.1 nv_gw — 6h 窗口
| Metric | Value |
|---|---|
| 总请求 | 43 |
| 成功 (200) | 19 |
| 失败 (502) | 24 |
| 成功率 | 44.2% |
| tier_attempts | 0 |

### 2.2 nv_gw — 502 错误分解
| Error Type | Count | Avg Dur (ms) |
|---|---|---|
| zombie_empty_completion | 14 | 20,271 |
| all_tiers_exhausted | 10 | 76,283 |

- zombie=14: NVCF content-filter → glm5_2_nv integrate + dsv4p_nv pexec 返回空完成，gateway 正确检测并发送 timeout SSE chunk 触发 openclaw fallback
- ATE=10: dsv4p_nv NVCF 504 + pexec timeout，上游 NVCF 功能退化

### 2.3 nv_gw — 逐小时 SR
| Hour (UTC) | Total | OK | Fail | SR% |
|---|---|---|---|---|
| 09:00 | 8 | 4 | 4 | 50.0 |
| 10:00 | 6 | 2 | 4 | 33.3 |
| 11:00 | 6 | 2 | 4 | 33.3 |
| 12:00 | 7 | 3 | 4 | 42.9 |
| 13:00 | 9 | 5 | 4 | 55.6 |
| 14:00 | 7 | 3 | 4 | 42.9 |

### 2.4 nv_gw — 逐模型
| Model | Total | OK | Fail | SR% | Avg Dur (ms) |
|---|---|---|---|---|---|
| dsv4p_nv | 16 | 4 | 12 | 25.0 | 58,011 |
| glm5_2_nv | 27 | 15 | 12 | 55.6 | 18,830 |

### 2.5 Recent 10 requests (latency + status)
| TS (UTC) | Model | Status | TTFB (ms) | Dur (ms) | Error | Upstream |
|---|---|---|---|---|---|---|
| 14:35:50 | dsv4p_nv | 502 | 434 | 64,719 | all_tiers_exhausted | — |
| 14:33:30 | glm5_2_nv | 502 | 11,215 | 11,216 | zombie_empty_completion | nv_integrate |
| 14:33:20 | glm5_2_nv | 200 | 9,873 | 9,874 | — | nv_integrate |
| 14:06:48 | dsv4p_nv | 502 | 53,366 | 53,367 | zombie_empty_completion | nvcf_pexec |
| 14:05:51 | dsv4p_nv | 200 | 56,338 | 56,339 | — | nvcf_pexec |
| 14:03:31 | glm5_2_nv | 502 | 12,593 | 12,594 | zombie_empty_completion | nv_integrate |
| 14:03:20 | glm5_2_nv | 200 | 10,299 | 10,299 | — | nv_integrate |
| 13:36:39 | dsv4p_nv | 502 | 49,488 | 49,489 | zombie_empty_completion | nvcf_pexec |
| 13:35:47 | dsv4p_nv | 200 | 52,402 | 52,403 | — | nvcf_pexec |
| 13:34:09 | glm5_2_nv | 200 | 6,106 | 6,107 | — | nv_integrate |

### 2.6 ms_gw — 6h 窗口
| Metric | Value |
|---|---|
| 总请求 | 24 |
| 成功 (ok) | 20 |
| 失败 (error) | 4 |
| 成功率 | 83.3% |
| p50 ok | 5,524ms |
| p90 ok | 10,878ms |
| p50 error | 14,906ms |
| max ok | 31,001ms |

ms_gw errors: MS-VARIANT-EXHAUSTED (ModelScope 后端，非配置可修复)

### 2.7 nv_gw — 日志关键事件
| Event | Count | Detail |
|---|---|---|
| NV-ZOMBIE-EMPTY | 5 | dsv4p_nv pexec + glm5_2_nv integrate → content-filter 空完成 |
| NV-CYCLE 504 | 1 | dsv4p_nv k3 → 504 nv_gateway_timeout → BUDGET exhaust → ABORT |
| NV-MS-FB FAILED | 1 | ms_gw relay TimeoutError at 123,945ms (relay_started=True) |
| NV-PEER-FB | 0 | 未触发（单 tier 链，ABORT-NO-FALLBACK 跳过 peer-fb） |

### 2.8 nv_gw — 当前参数
| Parameter | Value | Floor? |
|---|---|---|
| UPSTREAM_TIMEOUT | 66 | ✅ |
| TIER_TIMEOUT_BUDGET_S | 205 | ✅ |
| MIN_OUTBOUND_INTERVAL_S | 0 | ✅ |
| KEY_COOLDOWN_S | 25 | ✅ |
| TIER_COOLDOWN_S | 15 | ✅ |
| NVU_CONNECT_RESERVE_S | 0 | ✅ |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | ✅ |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | ✅ |
| NVU_EMPTY_200_FASTBREAK | 2 | ✅ |
| NVU_FORCE_STREAM_UPGRADE | 0 | ✅ |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | ✅ |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | ✅ |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | ✅ |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | ✅ |
| NVU_PEER_FALLBACK_ENABLED | 1 | ✅ |
| NVU_PEER_FB_SKIP_MODELS | (empty) | ✅ |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | ✅ |
| PROXY_TIMEOUT | 360 | ✅ |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 | ✅ |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | ✅ |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | ✅ |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | ✅ |

### 2.9 compose md5
`45c1f284` — 自容器重启后未变（2026-07-15T13:09:29Z）

## 3. 分析

### 3.1 无变化窗口
- 与 R1469 完全一致：43 请求，44.2% SR，14 zombie，10 ATE
- 0 tier_attempts — key 池干净，无 429 循环
- 所有参数已在地板值

### 3.2 zombie_empty_completion (14)
- NVCF content-filter 导致空响应（finish_reason=stop 但 content_chars<50）
- Gateway 正确检测并发送 timeout SSE chunk → openclaw fallback 触发
- 这不是配置问题 — NVCF 上游行为，gateway 缓解措施已就位

### 3.3 all_tiers_exhausted (10)
- dsv4p_nv NVCF 504 (NVCF gateway timeout) + pexec timeout
- 1 次 504 → k3 64.7s → BUDGET=66 exhaust → ABORT-NO-FALLBACK
- ms_gw fallback 尝试 1 次但 TimeoutError at 124s（relay_started=True）
- Peer-fallback 未触发：单 tier 链（dsv4p_nv only）→ ABORT-NO-FALLBACK 跳过 peer-fb

### 3.4 Peer-fallback 未触发分析
- `NVU_PEER_FALLBACK_ENABLED=1`, `NVU_PEER_FB_SKIP_MODELS=` (空)
- 但 tier chain 只有 `['dsv4p_nv']` — 单 tier 无 fallback tier
- `ABORT-NO-FALLBACK` 在单 tier 链耗尽时跳过 peer-fb
- 这是代码级决策，非配置可修复
- 如果 peer-fb 被触发，HM2 的独立 key 池可能拯救 dsv4p_nv ATE

### 3.5 ms_gw fallback timeout 分析
- `NVU_MS_GW_FALLBACK_TIMEOUT=120` vs ms_gw p50=5.5s, p90=10.9s
- ms_gw OK max=31s，但 1 次 fallback 在 124s timeout
- 降低 timeout 只会更快失败，不提升 SR
- ms_gw 自身 SR=83.3%（4 个 MS-VARIANT-EXHAUSTED），非可靠救援

## 4. 决策

**NOP** — 所有参数已在地板/最优值，无可优化空间。

- zombie=14: NVCF content-filter，gateway 检测正确，非配置可修复
- ATE=10: NVCF 504/pexec timeout，上游问题，非配置可修复
- ms_gw: MS-VARIANT-EXHAUSTED，ModelScope 后端问题，非配置可修复
- peer-fb 未触发：代码级单 tier 链决策，非配置可修复
- compose md5: `45c1f284` — 未变
- 0 tier_attempts — key 路由正常
- Zero param change, zero compose change, zero container restart

**铁律: 只改HM1不改HM2**

## ⏳ 轮到HM1优化HM2
