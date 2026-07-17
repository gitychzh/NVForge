# R1679: HM2→HM1 — NOP — KEY_COOLDOWN=55持续~28h+零429, zombie-dominated steady state, 全部参数floor/optimal

**决策**: NOP — 零配置可修复问题。全部失败为 zombie_empty_completion (NVCF content-filter 代码级), 全部参数触底/最优。

## 数据摘要

### 容器状态
- nv_gw: Up 2 hours (healthy)
- ms_gw: Up 12 hours (healthy)
- logs_db: Up 12 hours (healthy)
- StartedAt: ~2026-07-17T10:24 UTC (≈2h uptime)

### 6h 窗口 (29req/18OK/11fail = 62.1% SR)
| 指标 | 值 |
|------|-----|
| 总请求 | 29 |
| 成功 | 18 (62.1%) |
| 失败 | 11 |
| zombie_empty_completion | 11 (code-level NVCF content-filter, 不可配置修复) |
| all_tiers_exhausted | 0 |
| empty_200 | 0 |
| 429 rate limit | 0 |
| 504 gateway timeout | 0 |
| SSLEOF | 0 |
| NVCFPexecTimeout | 0 |

### 按模型
| 模型 | 请求 | OK | 失败 | SR | avg_ok_ms | max_ok_ms |
|------|------|-----|------|-----|-----------|-----------|
| glm5_2_nv | 29 | 18 | 11 | 62.1% | 9,928 | 32,092 |
| dsv4p_nv | 0 | - | - | - | - | - |
| kimi_nv | 0 | - | - | - | - | - |
| minimax_m3_nv | 0 | - | - | - | - | - |

### 容器重启后 (2h 窗口)
| 指标 | 值 |
|------|-----|
| 请求 | 13 |
| 成功 | 9 (69.2%) |
| 失败 | 4 |
| 失败原因 | **全部 zombie_empty_completion** |
| 真实 ATE | **0** |
| 429 | **0** |
| key_cycle_429s | 29/29 req = 1 (正常 key rotation, 非错误) |
| avg_ok_ms | 12,154 |

### zombie_empty_completion (代码级，不可配置修复)
- 11× zombie (avg 11,829ms, avg input 248,556 chars)
- 全部 glm5_2_nv, NVCF content-filter stop+12-48chars
- 日志: `[NV-ZOMBIE-EMPTY] finish_reason=stop but content_chars=12-48 < 50`
- 伴随 `[NV-UPSTREAM-ERROR-CHUNK]` → 触发 cc4101 zombie→api_error→CC retry
- **NVCF 层面问题，非 nv_gw 参数可修**

### upstream_type 分布
| upstream_type | total | ok | fail | key_429s | avg_ok_ms |
|---------------|-------|-----|------|----------|-----------|
| nvcf_pexec | 29 | 18 | 11 | 29 | 9,928 |

### tier_attempts
- glm5_2_nv: 29× pexec_success (avg 10,635ms, max 36,348ms)
- **零 tier-level 失败，零 429**

### ms_gw
- **0 traffic** — ms_gw fallback 未被触发

### key_cycle_429s
- 29/29 req = 1 (每请求正常 key rotation)
- total_429s = 29, max per req = 1
- KEY_COOLDOWN=55 消除 pexec_429 持续 ~28h

## 参数状态 (全部触底/最优 — 与 R1678 相同)

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | 最优 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 3 | 最优 (glm5_2 pexec_us_rr mode chain) |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | 触底 |
| NVU_EMPTY_200_FASTBREAK | 3 | 最优 |
| TIER_TIMEOUT_BUDGET_S | 195 | 最优 |
| NVU_TIER_BUDGET_DSV4P_NV | 70 | 最优 |
| NVU_TIER_BUDGET_GLM5_2_NV | 120 | 最优 |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | 最优 |
| TIER_COOLDOWN_S | 55 | 触底 (KEY_COOLDOWN 对称) |
| KEY_COOLDOWN_S | 55 | 触底 (消除 pexec_429) |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | 触底 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | 最优 |
| NVU_PEER_FALLBACK_TIMEOUT | 72 | 最优 |
| NVU_PEER_FB_SKIP_MODELS | (空) | 最优 |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms | 最优 |
| NVU_CONNECT_RESERVE_S | 0 | 触底 |
| MIN_OUTBOUND_INTERVAL_S | 0 | 触底 |
| NVU_SSLEOF_RETRY_DELAY_S | 0.5 | 触底 |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 | 最优 |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | 最优 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | 触底 |
| NV_INTEGRATE_MODELS | "" | 最优 (glm5_2 走 pexec_us_rr) |

## 铁律验证
- ✅ 只改HM1: 本轮无修改
- ✅ 改前必有数据: 6h DB + post-restart + zombie split + tier_attempts
- ✅ 改后必有验证: N/A
- ✅ 聚焦 nv_gw: 仅分析 nv_gw 链路
- ✅ 所有修改写入仓库: 本轮 NOP 仍记录
## ⏳ 轮到HM1优化HM2