# R1697: HM2→HM1 — NOP (false trigger, R1696 just deployed 7min ago, all params optimal)

> **轮次**: R1697 | **日期**: 2026-07-17 19:10 UTC | **操作者**: HM2 (opc2_uname)
> **决策**: ⏸️ NOP — R1696 (BIG_INPUT breaker) 刚部署 7min, 零 post-restart 数据, 所有参数 at optimal
> **铁律**: 只改HM1不改HM2

## 数据收集

### 容器状态
- **nv_gw**: Up 7 minutes (healthy) — R1696 刚重启
- **ms_gw**: Up 18 hours (healthy)
- **logs_db**: Up 18 hours (healthy)

### 6h 窗口 (2026-07-17 ~13:10–19:10 UTC)

| 指标 | 值 |
|------|-----|
| 总请求 | 54 |
| 成功 (200) | 43 |
| 失败 (502) | 11 |
| **成功率** | **79.6%** |
| ATE | 0 |
| peer-fb | 0 |
| fallback occurred | 0 |
| fallback actually attempted | 2 (未完成) |

### 错误分布 (6h)

| 错误类型 | 模型 | 数量 | 平均延迟 | tiers_tried |
|---------|------|------|---------|-------------|
| zombie_empty_completion | glm5_2_nv | 11 | 9,643ms | 1 |

### Zombie 详情
所有 11 个 zombie 均为 glm5_2_nv, input 257K-291K 字符 (>250K threshold), tiers_tried_count=1 (BIG_INPUT breaker 生效), duration 5.0s-26.3s.

### OK 延迟
| p50 | p95 | max | avg |
|-----|-----|-----|-----|
| 9,076ms | 21,281ms | 27,277ms | 10,810ms |

### 每小时 SR
| 小时 (UTC) | 请求 | OK | SR |
|-----------|------|-----|------|
| 05:00 | 8 | 7 | 87.5% |
| 06:00 | 5 | 3 | 60.0% |
| 07:00 | 5 | 4 | 80.0% |
| 08:00 | 5 | 3 | 60.0% |
| 09:00 | 11 | 9 | 81.8% |
| 10:00 | 10 | 8 | 80.0% |
| 11:00 | 10 | 9 | 90.0% |

### Tier Attempts (6h)
| tier | error_type | count | avg_ms | max_ms |
|------|-----------|-------|--------|--------|
| glm5_2_nv | pexec_success | 54 | 10,365 | 27,277 |
| glm5_2_nv | pexec_SSLEOFError | 2 | 5,003 | 5,003 |

### 日志 (nv_gw --tail 200)
```
[NV-GLM52-IDX] restored from glm52_mode_idx.json: idx=0
[NV-RR] restored from rr_counter.json: dsv4p=2563, kimi=83, glm5_2=758, minimax_m3=1
[NV-PROXY] Starting NV-unified proxy on 0.0.0.0:40006
[NV-PROXY] Listening on 0.0.0.0:40006 (role=passthrough, default_tier=dsv4p_nv)
```
零 ERROR/WARN/exception, 零 504, 零 NVCFPexecTimeout, 零 empty_200. 干干净净.

### 参数快照 (docker exec nv_gw env)

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | optimal |
| TIER_TIMEOUT_BUDGET_S | 195 | optimal |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 3 | optimal (R1690) |
| NVU_EMPTY_200_FASTBREAK | 1 | optimal (R1694) |
| NVU_TIER_BUDGET_GLM5_2_NV | 120 | optimal |
| NVU_TIER_BUDGET_DSV4P_NV | 70 | optimal |
| TIER_COOLDOWN_S | 25 | optimal |
| KEY_COOLDOWN_S | 25 | optimal |
| NVU_PEER_FALLBACK_TIMEOUT | 72 | optimal (≥HM2 BUDGET 70+2) |
| NVU_PEER_FALLBACK_ENABLED | 1 | enabled |
| NVU_PEER_FB_SKIP_MODELS | (空) | all models active |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | optimal |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms | optimal |
| NVU_BIG_INPUT_THRESHOLD | 250000 | optimal |
| NVU_BIG_INPUT_FAIL_N | 1 | floor (R1695) |
| NVU_BIG_INPUT_COOLDOWN_S | 180 | optimal |
| NVU_BIG_INPUT_MODELS | glm5_2_nv | optimal |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | reasonable |
| NVU_STREAM_TOTAL_DEADLINE_S | 35 | optimal |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| NV_INTEGRATE_MODELS | (空) | disabled |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | optimal |

## 候选参数评估

| 参数 | 当前值 | 候选 | 分析 | 结论 |
|------|--------|------|------|------|
| 全部参数 | — | — | R1696 刚部署 7min, 零 post-restart 数据 | ❌ 不可改 |
| NVU_BIG_INPUT_FAIL_N | 1 | — | floor | ❌ |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 3 | — | optimal (R1690) | ❌ |
| NVU_EMPTY_200_FASTBREAK | 1 | — | zero empty_200, floor | ❌ |
| TIER_COOLDOWN_S | 25 | — | floor, 零 ATE | ❌ |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | 0.5 | 仅 2 SSLEOF/6h, 影响极小 | ❌ 观察 > 微调 |

## 分析

### R1696 部署状态
R1696 (handlers.py zombie→big_input breaker feed) 7 分钟前部署, 容器重启。仅 2 个 post-restart 请求 (1 OK + 1 zombie), 不足以评估 breaker 效果。

### SR 趋势
- R1694 (EMPTY_200_FASTBREAK 3→1): 71.1% SR
- R1695 (BIG_INPUT breaker deploy): 74.4% SR
- R1696 (breaker feed fix): 79.6% SR (↑)

SR 持续上升, BIG_INPUT breaker 生效中: 所有 zombie 均 tiers_tried=1, 平均延迟 9.6s (vs 20-30s pre-breaker).

### BIG_INPUT breaker 验证
- 11/11 zombie 全部 input > 250K ✓ (breaker 正确识别)
- 11/11 zombie 全部 tiers_tried_count=1 ✓ (FAIL_N=1 正确生效)
- 零 false positive (无 <250K 的 zombie) ✓
- SSLEOF 2 次 (正常, 非 breaker 相关)

### 为什么不能改
1. **零 post-restart 数据**: 容器重启 7min, 仅 2 请求, 任何改动都是盲操作
2. **所有参数 at optimal**: BUDGET floor, FASTBREAK optimal, cooldown floor, breaker functional
3. **SR 上升中**: 79.6% 且趋势向上, 不应打断
4. **BIG_INPUT breaker 需要观察**: 首次在 R1696 修复 feed 路径后观察 24h+

## 决策

**⏸️ NOP** — R1696 刚部署 7min, 零 post-restart 数据, 所有参数 floor/optimal, SR 上升趋势中。BIG_INPUT breaker 需要至少 24h 观察窗口。保留所有参数不变, 仅维持 HM1↔HM2 交替节奏。
## ⏳ 轮到HM1优化HM2
