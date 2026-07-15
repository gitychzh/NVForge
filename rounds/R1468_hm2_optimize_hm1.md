# HM2 Optimize HM1 — Round R1468

**Date**: 2026-07-15 22:30Z
**Trigger**: False trigger (double-dispatch, 48th chain of R1395)
**Author**: opc2_uname (HM2)

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = `opc2_uname` (HM2)
- HM1 本地 git log 停留在 R1206（229 轮落后于 HM2）
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发（double-dispatch）

## 2. 数据收集（改前必有数据）

### 2.1 nv_gw — 6h 窗口
| Metric | Value |
|---|---|
| 总请求 | 42 |
| 成功 (200) | 19 |
| 失败 (502) | 23 |
| 成功率 | 45.2% |
| tier_attempts | 0 |

### 2.2 nv_gw — 502 错误分解
| Model | Error Type | Count | Avg Dur (ms) |
|---|---|---|---|
| glm5_2_nv | zombie_empty_completion | 11 | 12,083 |
| dsv4p_nv | all_tiers_exhausted | 8 | 63,867 |
| dsv4p_nv | zombie_empty_completion | 3 | 49,159 |
| glm5_2_nv | all_tiers_exhausted | 1 | 187,171 |

- zombie=14 (NVCF content-filter: glm5_2_nv integrate, not config-fixable)
- ATE=9 (dsv4p_nv NVCF 504/pexec timeout)

### 2.3 nv_gw — 逐小时 SR
| Hour (UTC) | Total | OK | Fail | SR% |
|---|---|---|---|---|
| 08:00 | 2 | 1 | 1 | 50.0 |
| 09:00 | 8 | 4 | 4 | 50.0 |
| 10:00 | 6 | 2 | 4 | 33.3 |
| 11:00 | 6 | 2 | 4 | 33.3 |
| 12:00 | 7 | 3 | 4 | 42.9 |
| 13:00 | 9 | 5 | 4 | 55.6 |
| 14:00 | 4 | 2 | 2 | 50.0 |

### 2.4 ms_gw — 6h 窗口
| Metric | Value |
|---|---|
| 总请求 | 24 |
| 成功 (ok) | 20 |
| 失败 (error) | 4 |
| 成功率 | 83.3% |

ms_gw errors: MS-VARIANT-EXHAUSTED (ModelScope backend, not config-fixable)

## 3. nv_gw 当前参数
| Parameter | Value | Floor? |
|---|---|---|
| UPSTREAM_TIMEOUT | 66 | ✅ |
| TIER_TIMEOUT_BUDGET_S | 205 | ✅ |
| MIN_OUTBOUND_INTERVAL_S | 0 | ✅ |
| KEY_COOLDOWN_S | 25 | ✅ |
| TIER_COOLDOWN_S | 15 | ✅ |
| NVU_CONNECT_RESERVE_S | 0 | ✅ |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | ✅ |
| NVU_FORCE_STREAM_UPGRADE | 0 | ✅ |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | ✅ |

## 4. ms_gw 当前参数
| Parameter | Value |
|---|---|
| EMPTY_200_FASTBREAK_THRESHOLD | 3 |
| KEY_COOLDOWN_S | 60 |
| ALL_EXHAUSTED_COOLDOWN_S | 30 |
| VARIANT_COOLDOWN_S | 30 |
| MIN_OUTBOUND_INTERVAL_S | 1.0 |
| UPSTREAM_TIMEOUT | 300 |
| PROXY_TIMEOUT | 600 |

## 5. nv_gw 日志错误
- NV-THINKING-TIMEOUT: dsv4p_nv thinking requests → 66s extended timeout (3 occurrences)
- NV-ZOMBIE-ERROR-CHUNK: dsv4p_nv + glm5_2_nv timeout error SSE chunks → gateway correctly sends failover signals (5 occurrences)

## 6. 决策

**NOP** — 所有参数已在地板/最优值，无可优化空间。

- zombie=14: NVCF content-filter 导致的空完成，不是配置问题，gateway 检测正确
- ATE=9: NVCF 504/pexec timeout，上游问题，非配置可修复
- ms_gw: 4 个 MS-VARIANT-EXHAUSTED 错误，ModelScope 后端问题，非配置可修复
- compose md5: `45c1f284` — 自容器重启后未变（2026-07-15T06:39:45Z）
- 0 tier_attempts — 无 key cycling，key 路由正常
- Zero param change, zero compose change, zero container restart

**铁律: 只改HM1不改HM2**

## ⏳ 轮到HM1优化HM2
