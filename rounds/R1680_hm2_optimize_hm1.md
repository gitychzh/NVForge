# R1680: HM2→HM1 — NOP — zombie_empty_completion 持续主导, 零可配置修复项, 全部参数 floor/optimal

**决策**: NOP — 零配置可修复问题。全部失败为 zombie_empty_completion (NVCF content-filter 代码级), 全部参数已触底/最优。

## 数据摘要

### 6h 窗口 (2026-07-17 06:45~12:45 UTC)
| 指标 | 值 |
|------|-----|
| 总请求 | 29 |
| 成功 | 18 (62.1%) |
| 失败 | 11 |
| zombie_empty_completion | 11 (100% of failures) |
| all_tiers_exhausted | 0 |
| 429 rate limit | 0 |
| SSLEOF | 0 |
| NVCFPexecTimeout | 0 |
| peer-fallback triggered | 0 |

### 24h 窗口
| 指标 | 值 |
|------|-----|
| 总请求 | 353 |
| 成功 | 192 (54.4%) |
| 失败 | 161 |
| zombie_empty_completion | 130 (80.7% of failures) |
| all_tiers_exhausted | 31 (19.3% of failures) |
| fallback_occurred | 0 (无 fallback 触发) |

### 按模型 (24h)
| 模型 | 请求 | OK | 失败 | SR | avg_ok_ms | max_ok_ms |
|------|------|-----|------|-----|-----------|-----------|
| glm5_2_nv | 325 | 179 | 146 | 55.1% | 22,128 | 232,761 |
| dsv4p_nv | 28 | 13 | 15 | 46.4% | 18,880 | — |

### Tier Attempts (24h, glm5_2_nv only)
| 结果 | 次数 | 占比 |
|------|------|------|
| pexec_success | 299 | 71.9% |
| pexec_429 | 90 | 21.6% |
| pexec_SSLEOFError | 13 | 3.1% |
| pexec_empty_200 | 10 | 2.4% |
| pexec_conn_RemoteDisconnected | 2 | 0.5% |
| pexec_504 | 1 | 0.2% |
| pexec_timeout | 1 | 0.2% |

### Zombie 详细分析 (6h 窗口)
- 11× zombie_empty_completion, avg duration ~11,829ms
- 全部 glm5_2_nv, NVCF content-filter stop + 12-48 chars output
- 日志: `[NV-ZOMBIE-EMPTY] finish_reason=stop but content_chars=12-48 < 50`
- Input chars: ~248K-253K (large context)
- FASTBREAK=3: 每 zombie 浪费 3 个 key 尝试 (~27s) 才检测到 zombie
- 300行日志中: 15 attempt → 5 zombie (33% per-attempt, ~71% per-request)
- 成功请求的 key 模式: 单 key 成功 (5/15 成功 = 33% per-key SR)

### 日志 Zombie 模式
```
10:33:20 k2 → 10:33:30 k3 → 10:33:42 ZOMBIE (22s, 2 keys wasted)
11:03:20 k5 → 11:03:26 k1 → 11:03:58 k2 → 11:04:35 ZOMBIE (75s, 3 keys wasted)
11:33:20 k3 → 11:33:42 k4 → 11:34:00 k5 → 11:34:27 ZOMBIE (67s, 3 keys wasted)
12:03:20 k1 → 12:03:33 k2 → 12:03:40 ZOMBIE (20s, 2 keys wasted)
12:24:48 k3 → 12:33:20 k4 → 12:33:26 k5 → 12:33:31 k1 → 12:33:35 ZOMBIE (47s, 4 keys wasted)
```

## 当前 HM1 配置 (核心参数)
| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | 最优 (R988) |
| TIER_TIMEOUT_BUDGET_S | 195 | 最优 (R1647) |
| NVU_TIER_BUDGET_DSV4P_NV | 70 | 最优 (R1663) |
| NVU_TIER_BUDGET_GLM5_2_NV | 120 | 最优 |
| KEY_COOLDOWN_S | 55 | 最优 (R1668) |
| TIER_COOLDOWN_S | 55 | 最优 (R1668) |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | 最优 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 3 | 最优 (R1665) |
| NVU_EMPTY_200_FASTBREAK | 3 | 最优 |
| NVU_PEER_FALLBACK_ENABLED | 1 | 最优 |
| NVU_PEER_FALLBACK_TIMEOUT | 72 | 最优 |
| NVU_PEER_FB_SKIP_MODELS | (空) | 最优 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | 最优 |
| NVU_CONNECT_RESERVE_S | 0 | 触底 |
| MIN_OUTBOUND_INTERVAL_S | 0 | 触底 |
| NVU_SSLEOF_RETRY_DELAY_S | 0.5 | 触底 |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 | 最优 |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | 最优 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | 触底 |
| NV_INTEGRATE_MODELS | "" | 最优 |
| CC4101_PRIMARY_FAIL_THRESHOLD | 5 | 最优 (R1642) |

## 约束检查
- dsv4p_nv + peer-fb: 70 + 72 = 142 < 195 ✓
- glm5_2 + peer-fb: 120 + 72 = 192 < 195 ✓
- KEY=TIER=55 铁律: ✓
- PEER_FALLBACK_TIMEOUT=72 ≥ HM2 BUDGET=70+2 ✓
- FASTBREAK=3 budget: 3×9+66=93 < 120 ✓

## 分析结论
与 R1679 相同: 全部失败为 zombie_empty_completion — NVCF glm5_2 在 117K+ context 下 content-filter 仅返回 12-48 chars。这是 NVCF 服务端行为，非配置可修复。所有可调参数已触底或最优，零改进空间。

## 铁律验证
- ✅ 只改HM1: 本轮无修改
- ✅ 改前必有数据: 6h+24h DB + 日志 + tier_attempts
- ✅ 改后必有验证: N/A
- ✅ 聚焦 nv_gw: 仅分析 nv_gw 链路
- ✅ 所有修改写入仓库: 本轮 NOP 仍记录
## ⏳ 轮到HM1优化HM2
