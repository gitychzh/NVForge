# R1131: HM2→HM1 — NOP (zero-change, all errors code-level, post-restart clean)

## 数据收集 (HM1 via SSH)

**容器**: `nv_gw`，重启于 `2026-07-10T19:03:27Z` (~10.6h 前)
**DB 容器**: `logs_db`

### 6h 总体统计
```
total | ok | err | sr_pct
  110 | 96 |  14 |   87.3
```

### 按模型
| model | total | ok | err | sr% | avg_dur |
|-------|-------|----|-----|-----|---------|
| glm5_2_nv | 68 | 57 | 11 | 83.8 | 13,582ms |
| dsv4p_nv | 28 | 25 | 3 | 89.3 | 19,436ms |
| minimax_m3_nv | 8 | 8 | 0 | 100.0 | 16,062ms |
| kimi_nv | 6 | 6 | 0 | 100.0 | 3,691ms |

### 按路径
| upstream | total | ok | err | avg_ttfb | avg_dur |
|----------|-------|----|-----|----------|---------|
| nv_integrate | 75 | 64 | 11 | 11,371ms | 14,091ms |
| nvcf_pexec | 32 | 32 | 0 | 11,801ms | 11,802ms |
| (NULL) | 3 | 0 | 3 | 558ms | 61,297ms |

### 错误分类 (6h)
| error_type | count |
|------------|-------|
| zombie_empty_completion | 9 |
| all_tiers_exhausted | 3 |
| NVStream_TimeoutError | 2 |

### 24h 错误全景
| error_type | count |
|------------|-------|
| zombie_empty_completion | 9 |
| all_tiers_exhausted | 7 |
| NVStream_TimeoutError | 6 |

### 每小时 SR
| hour (UTC) | total | ok | err | sr% |
|------------|-------|----|-----|-----|
| 15:00 | 52 | 50 | 2 | 96.2 |
| 16:00 | 7 | 5 | 2 | 71.4 |
| 17:00 | 20 | 11 | 9 | 55.0 |
| 18:00 | 9 | 8 | 1 | 88.9 |
| 19:00 | 6 | 6 | 0 | 100.0 |
| 20:00 | 7 | 7 | 0 | 100.0 |
| 21:00 | 9 | 9 | 0 | 100.0 |

### nv_tier_attempts: 0 行
ZERO per-key failures recorded in 6h window. All requests either succeed on first key or hit code-level errors (zombie/stream timeout) that don't go through key cycling.

### 关键参数 (docker exec nv_gw env)
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=198
NVU_TIER_BUDGET_DSV4P_NV=72
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
NVU_MS_GW_FALLBACK_TIMEOUT=180
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms
NVU_STREAM_TOTAL_DEADLINE_S=42
NVU_STREAM_FIRST_BYTE_DEADLINE_S=20
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
TIER_COOLDOWN_S=15
KEY_COOLDOWN_S=25
KEY_AUTHFAIL_COOLDOWN_S=60
MIN_OUTBOUND_INTERVAL_S=0
NVU_CONNECT_RESERVE_S=0
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
FALLBACK_HEALTH_THRESHOLD=0.05
NV_INTEGRATE_KEY_COOLDOWN_S=0
```

### docker logs nv_gw (关键行)
```
tier_chain=['dsv4p_nv'] (no fallback, 3model)  ← FALLBACK_GRAPH={} 预期
tier_chain=['glm5_2_nv'] (no fallback, 3model)  ← FALLBACK_GRAPH={} 预期
NV-INTEGRATE-SUCCESS 全部成功，无 FAIL/TIER-FAIL/ABORT 行
NV-ZOMBIE/ALL-TIERS/Timeout 不在最近 1000 行日志中（全部在 pre-restart 时段）
```

### ms_gw 日志（最近）
正常处理：MS-OK-STREAM + MS-STREAM-DONE 正常完成。偶有 MS-STREAM-CLIENT-EOF (BrokenPipeError) 和 MS-STREAM-CYCLE (stream_no_data_lines)，但 ms_gw 的 FASTBREAK=3 和 variant cycling 正常 rescue。

## 分析

### 1. zombie_empty_completion (9/14 = 64.3% of failures)
- 全部 glm5_2_nv integrate 路径
- 耗时 2,609-15,320ms（快速中止，远优于旧 96s NVStream_TimeoutError）
- 全部集中在 17:00-17:33 UTC（9 连发 burst），之后停止
- **R1107 模式**: 代码级 zombie 检测，非配置可修复。零改动。

### 2. NVStream_TimeoutError (2/14 = 14.3%)
- glm5_2_nv integrate，95,076ms / 96,999ms
- NVU_STREAM_TOTAL_DEADLINE_S=42 未生效（95s >> 42s）
- **代码级缺陷**: stream deadline 在 integrate 路径未强制执行。非配置可修复。零改动。

### 3. all_tiers_exhausted (3/14 = 21.4%)
- 全部 dsv4p_nv，单 tier，fallback_actually_attempted=false
- 耗时 61,142-61,376ms (~61s)
- **全部发生在容器重启前** (15:50, 16:00, 18:02 UTC — 容器重启 19:03)
- 重启后 0 ATE，100% SR (19:00-21:00)
- 61s ≈ UPSTREAM=66 但低于 NVU_TIER_BUDGET_DSV4P_NV=72，说明单 key 超时
- 前置容器状态下的 FALLBACK_GRAPH 行为异常，与当前配置无关
- **前置容器污染**: 零改动

### 4. nv_tier_attempts = 0 行
6h 窗口内零 per-key 失败。所有请求首 key 成功或命中代码级错误。系统健康。

### 5. 重启后性能
19:00-21:00 UTC: 22 req / 22 OK = 100% SR。当前配置稳定。

## 决策: NOP (零改动)

**理由**: 所有 14 个失败均为代码级错误或前置容器污染：
- 9x zombie_empty_completion → 代码级 zombie 检测，非配置可修复 (R1107)
- 2x NVStream_TimeoutError → 代码级 stream deadline 未执行，非配置可修复
- 3x all_tiers_exhausted → 全部前置容器重启，重启后 0 ATE / 100% SR

**铁律**: 只改HM1不改HM2。本轮无配置变更。

## 参数状态（不变）
所有参数维持 R1130 值，无变更。

## ⏳ 轮到HM1优化HM2