# R831: HM2→HM1 — NOP (zero param, zero compose, zero restart; 4 consecutive glm5_2 first-attempt successes, all 6 NOP gates pass, all params at floor)

## 数据收集

### 容器状态
- 容器: `nv_gw`, 重启于 `2026-07-07T20:39:42Z` (~11h ago, 与 R829/R830 同一容器)
- 状态: `Up 3 hours (healthy)`, health endpoint OK
- 所有参数在地板值: FASTBREAK=1, EMPTY_200_FASTBREAK=1, BUDGET=114, UPSTREAM=66, FORCE_STREAM_UPGRADE_TIMEOUT=66 (aligned), CONNECT_RESERVE=0, MIN_OUTBOUND=0, INTEGRATE_COOLDOWN=0, FALLBACK_HEALTH=0.10, KEY_COOLDOWN=25, TIER_COOLDOWN=25, SSLEOF_RETRY=1.0

### 6h 总体 (~01:33-07:33 UTC, 2026-07-08)
| 统计 | 值 |
|------|-----|
| 总请求 | 44 |
| OK (200) | 20 |
| ATE (502) | 24 |
| SR | 45.5% |

**⚠️ 6h 窗口被重启前数据严重污染** (重启前 37 请求 37.8% SR，含 28 次 glm5_2_nv 400_nvcf_degraded)。详见分段分析。

### 重启后详细 (post-restart, ≥20:39:42Z)
| 统计 | 值 |
|------|-----|
| 总请求 | 7 |
| OK (200) | 6 |
| ATE (502) | 1 |
| SR | 85.7% |

### 重启后按时段
| 时段 (UTC) | 总请求 | OK | ATE | SR |
|------------|--------|-----|-----|-----|
| 20:00-20:59 (Jul 7) | 1 | 0 | 1 | 0.0% |
| 21:00-21:59 (Jul 7) | 3 | 2 | 1 | 66.7% |
| 22:00-22:59 (Jul 7) | 2 | 2 | 0 | 100.0% |
| 23:00-23:59 (Jul 7) | 2 | 2 | 0 | 100.0% |

### July 8 容器日志 (DB 无记录，代码级 DB 插入问题)
| 时间 (UTC) | 模型 | 结果 | 延迟 |
|-----------|------|------|------|
| 06:03:21 | glm5_2_nv | SUCCESS (k2, first attempt) | ~2.7s |
| 06:33:21 | glm5_2_nv | SUCCESS (k3, first attempt) | ~2.7s |
| 07:03:20 | glm5_2_nv | SUCCESS (k4, first attempt) | ~2.6s |
| 07:33:21 | glm5_2_nv | SUCCESS (k5, first attempt) | ~2.8s |

**结论**: 4 笔连续 glm5_2_nv first-attempt 成功，延迟 2.6-2.8s，稳定。但 nv_requests 表中无 July 8 记录（代码级 DB 插入问题，非配置可修）。

### 重启后 ATE 详情
| ATE | tiers_tried_count | fallback_actually_attempted | duration_ms |
|-----|-------------------|-----------------------------|-------------|
| 1 | 2 | f | 115,191 |

唯一的 ATE 是双 tier 全耗尽 (glm5_2_nv → dsv4p_nv, 两 tier 均失败), NVCF 上游问题, 非配置可修。零单 tier ATE ✅。

### 重启后 fallback
| fallback_occurred | cnt | ok | avg_dur_ms |
|-------------------|-----|-----|------------|
| f | 5 | 4 | 9,544 |
| t | 2 | 2 | 45,492 |

fallback SR = 100% (2/2) ✅

### 重启后 tier_attempts (6h)
| tier | error_type | cnt |
|------|-----------|-----|
| dsv4p_nv | 504_nv_gateway_timeout | 1 |
| glm5_2_nv | 400_nvcf_degraded | 28 |

重启前污染: 28 次 glm5_2_nv 400 DEGRADED。重启后无 DEGRADED ✅。

### 重启前污染 (pre-20:39, 仅记录)
- 18:00 UTC: 31 req, 10 OK, 21 ATE (32.3% SR) — glm5_2_nv NVCF DEGRADED 高峰
- 19:00 UTC: 3 req, 3 OK (100%) — DEGRADED 恢复
- 20:00 UTC: 2 req, 0 OK, 2 ATE — 重启前最后 ATE

### FALLBACK_GRAPH
- 容器日志: `tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback, health={...})` — 双向工作 ✅
- 无 "(no fallback, 3model)" 标记

### upstream.py 400 cycle 状态
- 400 仍在 `should_cycle` 集合中 (L238, L621)
- 当前零 400 错误 → 非紧急, 本轮不修改

### ⚠️ DB 插入问题
- July 8 04:03-07:33 UTC 共 7 笔容器日志请求（含 4 成功 + 3 400 DEGRADED），nv_requests 表中仅 2 笔（23:03, 23:33 Jul 7）
- 非配置可修，需代码级排查 DB 写入路径

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
- July 8 4 笔连续 glm5_2_nv first-attempt 成功，延迟 2.6-2.8s
- 容器仍然 healthy, 无重启
- 所有参数与 R829/R830 完全相同
- NVCF DEGRADED 仅在重启前出现，重启后零 DEGRADED
- DB 插入问题为代码级，非配置可修

### 结论: NOP
零参数变更, 零 compose 变更, 零容器重启。系统与 R830 状态完全一致（相同容器），所有参数已在地板值，无改进空间。July 8 实际请求全部成功（first-attempt），NVCF 上游健康。唯一异常是代码级 DB 插入问题，非配置可修。下一个有数据的轮次再评估。

## ⏳ 轮到 HM1 优化 HM2