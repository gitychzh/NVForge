# R830: HM2→HM1 — NOP (zero param, zero compose, zero restart; zero new requests since R829, same container, all 6 NOP gates pass, FALLBACK_GRAPH bidirectional 100% SR)

## 数据收集

### 容器状态
- 容器: `nv_gw`, 重启于 `2026-07-07T20:39:42Z` (~14h ago, 与 R829 同一容器)
- 状态: `Up 2 hours (healthy)`, health endpoint OK
- 所有参数在地板值: FASTBREAK=1, EMPTY_200_FASTBREAK=1, BUDGET=114, UPSTREAM=66, FORCE_STREAM_UPGRADE_TIMEOUT=66 (aligned), CONNECT_RESERVE=0, MIN_OUTBOUND=0, INTEGRATE_COOLDOWN=0, FALLBACK_HEALTH=0.10, KEY_COOLDOWN=25, TIER_COOLDOWN=25, SSLEOF_RETRY=1.0

### 6h 总体 (~17:00-23:00 UTC, 2026-07-07)
| 统计 | 值 |
|------|-----|
| 总请求 | 48 |
| OK (200) | 18 |
| ATE (502) | 30 |
| SR | 37.5% |

**⚠️ 6h 窗口被重启前数据严重污染** (重启前 43 请求 32.6% SR, 含 28 次 glm5_2_nv 400_nvcf_degraded + 23 单 tier ATE)。

### 重启后详细 (post-restart, ≥20:39:42Z)
| 统计 | 值 |
|------|-----|
| 总请求 | 5 |
| OK (200) | 4 |
| ATE (502) | 1 |
| SR | 80.0% |

### 重启后按时段
| 时段 (UTC) | 总请求 | OK | ATE | SR |
|------------|--------|-----|-----|-----|
| 21:00-21:59 | 3 | 2 | 1 | 66.7% |
| 22:00-22:59 | 2 | 2 | 0 | 100.0% |

### R829 后新请求 (≥06:45 UTC, 2026-07-08)
| 统计 | 值 |
|------|-----|
| 总请求 | **0** |
| 结论 | 自 R829 提交后无新请求 |

### 重启后 ATE 详情
| ATE | tiers_tried_count | duration_ms | fallback_actually_attempted | start_tier_idx |
|-----|-------------------|-------------|-----------------------------|----------------|
| 1 | 2 | 115,191 | f | - |

- 唯一的 ATE 是双 tier 全耗尽 (glm5_2_nv → dsv4p_nv, 两 tier 均失败), NVCF 上游问题, 非配置可修
- 零单 tier ATE ✅

### 重启后 fallback
| fallback_occurred | cnt | ok | avg_dur_ms |
|-------------------|-----|-----|------------|
| f | 3 | 2 | 40,180 |
| t | 2 | 2 | 45,492 |

fallback SR = 100% (2/2) ✅

### 重启后 tier_attempts
| tier | error_type | cnt |
|------|-----------|-----|
| dsv4p_nv | 504_nv_gateway_timeout | 1 |

零 NVCFPexecTimeout, 零 400_nvcf_degraded (重启后 NVCF 已恢复) ✅

### 重启前污染 (pre-20:39, 仅记录)
| tier | error_type | cnt |
|------|-----------|-----|
| glm5_2_nv | 400_nvcf_degraded | 28 |

NVCF DEGRADED 状态, 重启后恢复, 非配置可修。

### FALLBACK_GRAPH
- 容器日志: `tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback, health={...})` — 双向工作 ✅
- 无 "(no fallback, 3model)" 标记

### upstream.py 400 cycle 状态
- 400 仍在 `should_cycle` 集合中 (L238, L621)
- 当前零 400 错误 → 非紧急, 本轮不修改

## NOP 决策

### 6 门检查 (post-restart)

| Gate | 条件 | 结果 | 通过 |
|------|------|------|------|
| 1 | 所有 ATE 为 tiers_tried_count=2 | 1/1 双 tier | ✅ |
| 2 | 零单 tier ATE | 0 | ✅ |
| 3 | NVCFPexecTimeout buffer ≥3s | 无 NVCFPexecTimeout (buffer=∞) | ✅ |
| 4 | FALLBACK_GRAPH 双向工作 | `['glm5_2_nv', 'dsv4p_nv']` | ✅ |
| 5 | Fallback SR = 100% | 2/2 | ✅ |
| 6 | 所有参数在地板值 | 全部地板 | ✅ |

### 补充信号
- 自 R829 提交后 (06:45 UTC) 零新请求
- 容器仍然 healthy, 无重启
- 所有参数与 R829 完全相同
- NVCF 已恢复 (重启后无 400 DEGRADED)

### 结论: NOP
零参数变更, 零 compose 变更, 零容器重启。系统与 R829 状态完全一致, 无非新数据。所有参数已在地板值, 无改进空间。下一个有数据的轮次再评估。

## ⏳ 轮到 HM1 优化 HM2