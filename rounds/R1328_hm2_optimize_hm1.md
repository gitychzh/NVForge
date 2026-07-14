# HM2 Optimize HM1 — Round R1328

## 触发分析

- 脚本检测到 R1327 自提交 (HM2→HM1 NOP, "这是我提交的, 不触发")
- cron 仍被派遣 — 误触发 (double-dispatch, 42nd consecutive post-R1286)
- HM1 本地 git log 停留在 R1206 (120+ 轮落后)

## 数据收集 (改前必有数据)

### 6h 总体
| 指标 | 值 |
|------|-----|
| 总请求 | 52 |
| 成功 (200) | 46 |
| 失败 (502) | 6 |
| 成功率 | 88.5% |
| 模型分布 | glm5_2_nv 52/52 (100%) |
| 路径分布 | nv_integrate 52/52 (100%) |
| fallback 触发 | 0/52 |
| tier_attempts | 0 |
| ATE | 0 |
| IncompleteRead | 0 |

### 错误分类
| 错误类型 | 数量 | 可修复 |
|---------|------|--------|
| zombie_empty_completion | 6 | ❌ 代码级 (NVCF content-filter stop) |

### Zombie 详情
| 模型 | 数量 | avg input_chars | avg duration_ms | avg output_tokens |
|------|------|-----------------|-----------------|-------------------|
| glm5_2_nv | 6 | 184,807 | 5,845 | 16 |

### 每小时 SR
| 小时 | 总量 | OK | 失败 | SR |
|------|------|-----|------|-----|
| 00:00 | 6 | 5 | 1 | 83.3% |
| 01:00 | 29 | 28 | 1 | 96.6% |
| 02:00 | 5 | 5 | 0 | 100.0% |
| 03:00 | 5 | 3 | 2 | 60.0% |
| 04:00 | 4 | 3 | 1 | 75.0% |
| 05:00 | 3 | 2 | 1 | 66.7% |

### 最近 10 条请求 (延迟+状态)
| ts | model | status | ttfb_ms | dur_ms | error_type | output_tokens |
|----|-------|--------|---------|--------|-----------|---------------|
| 05:33:25 | glm5_2_nv | 200 | 5108 | 5108 | - | 38 |
| 05:03:40 | glm5_2_nv | 502 | 9913 | 9914 | zombie_empty_completion | 27 |
| 05:03:30 | glm5_2_nv | 200 | 10023 | 10023 | - | 150 |
| 04:33:32 | glm5_2_nv | 502 | 5432 | 5433 | zombie_empty_completion | 25 |
| 04:33:26 | glm5_2_nv | 200 | 6388 | 6389 | - | 140 |
| 04:03:37 | glm5_2_nv | 200 | 8279 | 8280 | - | 34 |
| 04:03:28 | glm5_2_nv | 200 | 8374 | 8375 | - | 158 |
| 03:33:31 | glm5_2_nv | 502 | 4783 | 4784 | zombie_empty_completion | 28 |
| 03:33:25 | glm5_2_nv | 200 | 5568 | 5568 | - | 138 |
| 03:03:54 | glm5_2_nv | 200 | 13751 | 13752 | - | 49 |

### 日志信号
- tier_chain=['glm5_2_nv'] (no fallback, 3model) — 正常 (FALLBACK_GRAPH={})
- NV-ZOMBIE-EMPTY: content_chars=12-46 < 50, input_chars=175K-178K, content_filter stop
- NV-ZOMBIE-ERROR-CHUNK: sent finish_reason=content_filter to openclaw
- 零 ERROR/WARN, 零 NV-TIER-FAIL, 零 NV-CYCLE
- 全部 NV-INTEGRATE-SUCCESS first-attempt (非zombie请求)

### ms_gw 信号
| 总请求 | 成功 | SR |
|--------|------|-----|
| 13 | 13 | 100% |

### 容器状态
- nv_gw: Up 15 hours (healthy), started 2026-07-13T22:14:51Z
- Compose md5: 6e1b58bc70eca49e500e3034b08376d9 (stable, unchanged from R1315+)
- NVU_PEER_FB_SKIP_MODELS: empty

### 参数状态
所有参数处于 floor/optimal:
- UPSTREAM_TIMEOUT=66, TIER_COOLDOWN_S=15, KEY_COOLDOWN_S=25
- NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_EMPTY_200_FASTBREAK=2
- NVU_INTEGRATE_TIMEOUT_FASTBREAK=1, NVU_INTEGRATE_THINKING_TIMEOUT_S=90
- TIER_TIMEOUT_BUDGET_S=205, NVU_PEER_FALLBACK_TIMEOUT=66
- NVU_MS_GW_FALLBACK_TIMEOUT=195, NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms
- NVU_TIER_BUDGET_DSV4P_NV=72, NVU_TIER_BUDGET_GLM5_2_NV=96, NVU_TIER_BUDGET_MINIMAX_M3_NV=100
- NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
- NVU_STREAM_FIRST_BYTE_DEADLINE_S=20, NVU_STREAM_TOTAL_DEADLINE_S=42
- NVU_SSLEOF_RETRY_DELAY_S=1.0, NVU_CONNECT_RESERVE_S=0
- MIN_OUTBOUND_INTERVAL_S=0, NVU_FALLBACK_HEALTH_THRESHOLD=0.05
- NVU_PEER_FALLBACK_ENABLED=1, NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006

## 决策: NOP (零变更)

**理由**: 全部 6 个失败均为 zombie_empty_completion — 代码级检测 (NVCF content-filter 返回 finish_reason=stop + content_chars<50)。非配置参数可修复。零 tier_attempts、零 ATE、零 fallback、零 key_cycle_429s。全部参数 floor/optimal。ms_gw 100% SR。Compose md5 稳定。42nd consecutive NOP since R1286。

**评判**: 无改进空间。zombie 检测为代码级功能，返回 502 触发 openclaw fallback (3-10s) 比旧 96s NVStream_TimeoutError 更优。铁律:只改HM1不改HM2。

## ⏳ 轮到HM1优化HM2