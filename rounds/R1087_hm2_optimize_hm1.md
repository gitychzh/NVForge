# HM2 Optimize HM1 — Round R1087

## 触发
R1086 NOP 后 cron 检测到 HM1 提交了新 commit → 轮到 HM2 优化 HM1。

## 数据收集 (改前必有数据)

### nv_gw 容器状态
- 重启时间: 2026-07-10 09:47 UTC
- 重启后运行: ~9.8h
- 容器: nv_gw, Up 2+ hours (healthy)

### 有效窗口: 重启后 (~9.8h, ts >= 09:47 UTC)
| 指标 | 值 |
|------|-----|
| 总请求 | 6 |
| 成功 | 6 (100.0% SR) |
| 失败 | 0 |
| 平均 TTFB | 4,173ms |
| 平均 duration | 4,174ms |
| 最大 duration | 5,683ms |

### 按路径分解 (重启后)
| upstream_type | cnt | ok | avg_ttfb | avg_dur |
|---------------|-----|-----|----------|---------|
| nv_integrate | 6 | 6 | 4,173ms | 4,174ms |

### 错误分类 (重启后)
- 零错误, 零 tier_attempts, 零 429s
- dsv4p_nv: 零流量 (仅 glm5_2_nv integrate 活跃)

### 6h 窗口 (含重启前污染, 仅供参考)
| 指标 | 值 |
|------|-----|
| 总请求 | 51 |
| 成功 | 43 (84.3%) |
| 失败 | 8 (全部 pre-restart, ts < 09:47 UTC) |
| glm5_2_nv NVStream_TimeoutError | 4 (pre-restart, max 105,819ms) |
| dsv4p_nv all_tiers_exhausted | 4 (pre-restart, max 132,017ms) |

### 6h tier_attempts (全部 pre-restart)
| tier | error_type | cnt | avg_ms | max_ms |
|------|-----------|-----|--------|--------|
| glm5_2_nv | IntegrateRemoteDisconnected | 1 | 20,284ms | 20,284ms |
| glm5_2_nv | IntegrateTimeout | 1 | 90,566ms | 90,566ms |

### 24h 错误全景
| error_type | cnt |
|----------------------|-----|
| all_tiers_exhausted | 36 |
| NVStream_TimeoutError | 7 |
| stream_total_deadline | 3 |

### nv_gw 日志 (tail 100)
- 全部 [NV-INTEGRATE-SUCCESS] tier=glm5_2_nv k1-k5 1st-key 成功
- 零 NV-TIER-FAIL, 零 NV-MS-FB, 零 NV-PEER-FB, 零 BrokenPipeError
- 零 empty_200, 零 timeout, 零 429
- 键循环正常: k1→k2→k3→k4→k5→k1 均匀轮转
- dsv4p_nv 零日志活动

### nv_gw 参数审查 — 全部 floor/optimal
所有参数与 R1086 一致, 无变化, 全部已 floor/optimal:
- UPSTREAM_TIMEOUT=66 (floor), TIER_TIMEOUT_BUDGET_S=132, TIER_COOLDOWN_S=18
- KEY_COOLDOWN_S=25, KEY_AUTHFAIL_COOLDOWN_S=60 (R922)
- NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_EMPTY_200_FASTBREAK=2, NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
- NVU_SSLEOF_RETRY_DELAY_S=1.0, NVU_CONNECT_RESERVE_S=0, MIN_OUTBOUND_INTERVAL_S=0
- NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
- NVU_TIER_BUDGET_DSV4P_NV=66, NVU_TIER_BUDGET_GLM5_2_NV=96
- NVU_PEER_FB_SKIP_MODELS=glm5_2_nv (dsv4p not skipped → peer-fb on)
- NVU_FALLBACK_HEALTH_THRESHOLD=0.10, FALLBACK_HEALTH_THRESHOLD=0.05 (legacy dead)
- NVU_STREAM_TOTAL_DEADLINE_S=90, NVU_INTEGRATE_THINKING_TIMEOUT_S=90

## 优化决策

**NOP — 无 config-fixable 信号。**

理由:
1. 重启后 100% SR (6/6), 零失败 — 所有参数已 floor/optimal
2. 全部 8 个 6h 失败是重启前 (ts < 09:47 UTC) — NVCF 504 外部 + dsv4p ATE, 非 config-fixable (R1085/R1086 已记录)
3. dsv4p_nv 重启后零流量 — 无法判断是否需要调整, 不盲改
4. glm5_2_nv integrate 1st-key 100% SR — 完美稳定, avg 4,173ms TTFB
5. 键轮转均匀, 零 429s, 零 tier_attempts — 无 rate-limit 信号
6. 所有 nv_gw 参数已 floor/optimal, 无下探空间
7. R1086 相同结论, 状态延续 — 无新信号触发变更

零参数修改。铁律: 只改 HM1 不改 HM2.

## ⏳ 轮到HM1优化HM2