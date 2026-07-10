# HM2 Optimize HM1 — Round R1044

## 触发分析

- Cron 脚本输出: `"这是我提交的, 不触发"` — 自提交检测
- 最新 commit author: `opc2_uname` (HM2)
- GitHub 最新 commit: `7ef8c18` (R1043, HM2 NOP)
- HM1 本地 git log: 停留在 R821 (223 轮落后)
- **判定: FALSE TRIGGER (double-dispatch)** — R1043 已提交并推送，symlink 正确指向 R1043，cron 重复派遣

## 数据收集 (改前必有数据)

### nv_gw 容器状态
- 容器: `nv_gw` — Up 56 minutes (healthy)
- 重启时间: 2026-07-10 09:08 CST

### nv_requests 6h 统计
| 指标 | 值 |
|------|-----|
| 总请求 | 38 |
| 成功 (200) | 36 |
| 失败 | 2 |
| 成功率 | 94.7% |
| 错误类型 | NVStream_TimeoutError (1), all_tiers_exhausted (1) |

### nv_requests 按 tier 分组
| tier_model | total | ok | err | sr_pct | avg_ms |
|------------|-------|----|-----|--------|--------|
| glm5_2_nv | 36 | 35 | 1 | 97.2% | 9409 |
| dsv4p_nv | 2 | 1 | 1 | 50.0% | 36014 |

### nv_requests 按 upstream 分组
| upstream | total | ok | err |
|----------|-------|----|-----|
| nv_integrate | 36 | 35 | 1 |
| NULL (ATE) | 1 | 0 | 1 |
| nvcf_pexec | 1 | 1 | 0 |

### nv_tier_attempts 6h
- **0 rows** — 无 key 级失败尝试

### nv_gw 容器日志 (最近错误)
```
[10:03:55.6] [NV-INTEGRATE-SSL-CYCLE] tier=glm5_2_nv k2 SSL error (5001ms) — cycle
```
唯一近期异常: 一次 SSL 错误被 cycle 处理，无影响

### nv_gw 关键参数 (全部地板/最优)
| 参数 | 值 | 状态 |
|------|-----|------|
| TIER_TIMEOUT_BUDGET_S | 110 | 地板 |
| UPSTREAM_TIMEOUT | 66 | 地板 |
| MIN_OUTBOUND_INTERVAL_S | 0 | 地板 |
| KEY_COOLDOWN_S | 25 | 地板 |
| TIER_COOLDOWN_S | 18 | 地板 |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | 防御 |
| NVU_CONNECT_RESERVE_S | 0 | 地板 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | 地板 |
| NVU_FORCE_STREAM_UPGRADE | 0 | 地板 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | 地板 |
| NVU_EMPTY_200_FASTBREAK | 2 | 地板 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | 地板 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | 地板 |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | 最优 |
| NVU_STREAM_TOTAL_DEADLINE_S | 90 | 最优 |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.10 | 最优 |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | 最优 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 90 | 最优 |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | 最优 |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | 最优 |

### ms_gw 状态
- 日志: 全部 MS-OK / MS-OK-STREAM，无错误
- EMPTY_200_FASTBREAK_THRESHOLD=3 (地板)
- KEY_COOLDOWN_S=60 (合理)
- MIN_OUTBOUND_INTERVAL_S=1.0 (合理)
- 无优化空间

## 决策

**NOP — 所有参数已在地板/最优值，无优化空间。**

- SR 94.7% 与 R1043 的 94.6% 一致（±1 请求波动）
- 2 次失败均为 pre-restart (R1043 之前，容器重启前): 1x NVStream_TimeoutError (94s stream, nv_integrate) + 1x ATE (dsv4p_nv, 61s)
- nv_tier_attempts 0 rows — 无 key 级失败
- 全部参数已在地板 (TIER_TIMEOUT_BUDGET_S=110, UPSTREAM_TIMEOUT=66, 等)
- ms_gw 正常，参数已在最优
- 铁律: 只改 HM1 不改 HM2
- 零参数修改，零 compose 修改，零重启

## ⏳ 轮到HM1优化HM2