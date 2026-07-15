# R1502: HM2→HM1 — NOP (zero ATE, zero tier-fail, zombie-only, all params floor/optimal)

## 数据收集

### SSH HM1
- SSH: `ssh -p 222 opc_uname@100.109.153.83` — 成功连接
- nv_gw: Up 2 hours (healthy), started 2026-07-15T18:15:54Z
- compose md5: `ba4f2871` (与 R1501 相同，未变更)
- HM2 peer health: 200 OK, peer-fb connectivity verified

### DB (6h 窗口)
| 指标 | 值 |
|------|-----|
| 总请求 | 60 |
| 成功 | 37 (61.7%) |
| 失败 | 23 |
| 最新请求 | 2026-07-15 20:35:49 UTC |

### DB (2h 窗口，容器重启后)
| 指标 | 值 |
|------|-----|
| 总请求 | 19 |
| 成功 | 11 (57.9%) |
| 失败 | 8 |

### 错误分类 (6h)
| 模型 | 错误类型 | 数量 | 平均延迟 |
|------|---------|------|---------|
| dsv4p_nv | zombie_empty_completion | 11 | ~10s |
| glm5_2_nv | zombie_empty_completion | 8 | ~12s |
| dsv4p_nv | all_tiers_exhausted | 7 | 43.3s |

**总计**: 19 zombie (83%), 7 ATE (30% — 全部在容器重启前)

### 按模型 (6h)
| 模型 | 总数 | 成功 | SR | 平均成功延迟 |
|------|------|------|-----|-------------|
| dsv4p_nv | 36 | 25 | 69.4% | 24.4s |
| glm5_2_nv | 24 | 12 | 50.0% | 13.2s |

### 按模型 (2h 容器重启后)
| 模型 | 总数 | 成功 | SR | 平均成功延迟 |
|------|------|------|-----|-------------|
| dsv4p_nv | 11 | 7 | 63.6% | 9.8s |
| glm5_2_nv | 8 | 4 | 50.0% | 12.3s |

### Fallback
- 全部 60 请求显示 fallback_occurred=f — 无 fallback 触发
- 零 peer-fb (full logs: 0× NV-PEER-FB)
- 零 ms-fb (full logs: 0× NV-MS-FB)

### Tier 尝试
- 2× `429_integrate_rate_limit` (glm5_2_nv) — 瞬时速率限制，非配置可修复

### ms_gw
- 19 请求: 15 ok, 3 error, 1 client_disconnect (78.9% SR)

### Live 日志分析 (tail 100)
| 信号 | 数量 | 说明 |
|------|------|------|
| NV-ZOMBIE-EMPTY | 9 | NVCF content-filter，代码级不可修复 |
| NV-INTEGRATE-SUCCESS | 6 | 全部首次尝试成功 |
| NV-THINKING-TIMEOUT | 若干 | thinking 请求超时延长 66s |
| NV-TIER-FAIL | 0 | ✅ |
| NV-CYCLE | 0 | ✅ |
| NV-PEER-FB | 0 | ✅ |
| NV-MS-FB | 0 | ✅ |
| 504 | 0 | ✅ |
| NV-FASTBREAK | 0 | ✅ |

### ATE 详情 (error_detail JSONL)
July 16 文件 (容器重启后): **零 ATE 条目**。全部 5 条 ATE 记录时间戳为容器重启前 (16:07-18:05 UTC)。

容器重启前 ATE 模式:
- 3× 504_nv_gateway_timeout (k1/k4/k5, ~63s) — NVCF 函数级
- 3× empty_200 (k1/k3/k4, ~62s) — 单键 empty_200，num_attempts=1
- 1× NVCFPexecTimeout (k1, 66s) — FASTBREAK=1 正确触发
- 1× all_cooldown skipped (0ms) — 全键冷却中

## 环境变量 (全部参数)
| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | 地板 |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | 地板 (=UPSTREAM) |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | 地板 |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | 地板 |
| TIER_TIMEOUT_BUDGET_S | 205 | 最优 |
| TIER_COOLDOWN_S | 15 | 地板 |
| KEY_COOLDOWN_S | 25 | 地板 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | 地板 |
| NVU_EMPTY_200_FASTBREAK | 2 | 最优 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | 地板 |
| NVU_PEER_FALLBACK_ENABLED | 1 | 最优 |
| NVU_PEER_FB_SKIP_MODELS | (空) | 最优 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | 最优 |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms | 最优 (R1488: 无 dsv4p_nv) |
| NVU_CONNECT_RESERVE_S | 0 | 地板 |
| MIN_OUTBOUND_INTERVAL_S | 0 | 地板 |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | 最优 |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 | 最优 |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | 最优 |
| NVU_FORCE_STREAM_UPGRADE | 0 | 最优 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | 最优 |

**全部 16 个参数已触底/最优。compose md5 未变，container env 一致。**

## 决策: NOP

### 失败根因分析
1. **zombie_empty_completion (83% of failures)**: NVCF 返回 finish_reason=stop 但 content_chars=12 < 50，网关正确检测+快速 abort。代码级 NVCF content-filter 问题，不可配置修复。
2. **all_tiers_exhausted (30% of failures, 0% in 2h post-restart)**: 全部 7 个 ATE 发生在容器重启前（R1501 窗口）。2h 重启后零 ATE、零 tier-fail、零 FASTBREAK、零 peer-fb、零 ms-fb。BUDGET=UPSTREAM_TIMEOUT 地板模式有效。

### 零可配置修复项
- 零 504 → 无需调整 UPSTREAM_TIMEOUT
- 零 tier cycling → 无需调整 COOLDOWN
- 零 peer-fb/ms-fb → 无需调整 fallback 参数
- 零 SSLEOFError → 无需调整 retry delay
- FASTBREAK 全部地板 → 无需调整
- BUDGET 全部地板 → 无需调整
- compose md5 未变，container env 一致 → 无需重启

### 与 R1501 对比
完全相同的 NOP 模式 — 同一数据集 (60 vs 59 请求)，同样 zombie 主导，同样全部参数触底。2h 重启后零 ATE 进一步确认 BUDGET 地板模式有效。连续 4 轮 (R1499-R1502) 零新数据，零新流量，零可配置问题。

## 铁律
- ✅ 只改HM1不改HM2 — 本轮无配置修改
- ✅ compose md5 ba4f2871 未变
- ✅ container env 与 compose 一致 (无 R1484 陈旧容器问题)
- ✅ 铁律:只改HM1不改HM2
## ⏳ 轮到HM1优化HM2