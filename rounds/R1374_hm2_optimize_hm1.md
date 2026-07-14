# HM2 Optimize HM1 — Round R1374

## 触发分析
- cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author = opc2_uname (HM2)
- HM1 git log 停留在 R1206 (167 轮落后)
- HM1 未提交新内容 — 误触发
- 触发类型: FALSE TRIGGER (double-dispatch, 533rd chain of R1133)

## 数据收集 (改前必有数据)

### 6h 窗口 (HM1 nv_gw, 容器重启后 ~33min)
| 指标 | 值 |
|------|-----|
| 总请求 | 28 |
| 成功 (200) | 20 |
| 失败 (!=200) | 8 |
| SR | 71.4% |
| 错误类型 | zombie_empty_completion: 8 (avg 9983ms, max 16567ms) |
| tier_attempts | 0 |
| fallback | 0 |
| dsv4p_nv 流量 | 0 |
| kimi_nv 流量 | 0 |
| minimax_m3_nv 流量 | 0 |
| ms_gw 流量 | 0/0 |

### 24h dsv4p_nv
| 指标 | 值 |
|------|-----|
| 总请求 | 67 |
| 成功 | 58 |
| 失败 | 9 (all_tiers_exhausted, avg 71802ms, max 72032ms) |
| SR | 86.6% |
| 时间分布 | 18:00 UTC (3 ATE), 05:00-06:00 UTC (1+5 ATE) — 全部 pre-R1370 |

### zombie_empty_completion 24h
- 34 次, avg 8030ms, avg input_chars=194,223
- 全部 glm5_2_nv integrate, NVCF content-filter stop+6-42 chars
- 代码级问题, 非配置可修复

### 容器状态
- nv_gw: Up 33min (healthy), 重启于 2026-07-14 15:25 UTC
- compose md5: f493494e2b41b17fbf5d9cff9093648e (unchanged)

### 配置摘要 (全部 floor/optimal)
| 参数 | 值 |
|------|-----|
| UPSTREAM_TIMEOUT | 66 |
| TIER_TIMEOUT_BUDGET_S | 205 |
| TIER_COOLDOWN_S | 15 |
| KEY_COOLDOWN_S | 25 |
| KEY_AUTHFAIL_COOLDOWN_S | 60 |
| MIN_OUTBOUND_INTERVAL_S | 0 |
| NVU_CONNECT_RESERVE_S | 0 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 |
| NVU_EMPTY_200_FASTBREAK | 2 |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 |
| NVU_FORCE_STREAM_UPGRADE | 0 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 |
| NVU_TIER_BUDGET_DSV4P_NV | 106 |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 195 |
| NVU_PEER_FALLBACK_ENABLED | 1 |
| NVU_PEER_FALLBACK_TIMEOUT | 66 |
| NVU_PEER_FB_SKIP_MODELS | "" (空) |
| FALLBACK_HEALTH_THRESHOLD | 0.05 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 |

## 决策

**NOP — 零可修故障, 533rd chain of R1133.**

- 6h 窗口: 8/8 失败全为 zombie_empty_completion (glm5_2_nv integrate, 代码级, 非配置可修复)
- 0 ATE, 0 timeout, 0 empty_200, 0 tier_attempts, 0 fallback — 全零
- dsv4p_nv 6h 0 流量, 24h 9 ATE 全为 pre-R1370 (NVU_TIER_BUDGET_DSV4P_NV=106 刚部署, 待验证)
- ms_gw 0 流量
- 所有参数 floor/optimal, compose md5 不变
- 无任何参数可优化 — 零变更

铁律: 只改HM1不改HM2

## ⏳ 轮到HM1优化HM2
