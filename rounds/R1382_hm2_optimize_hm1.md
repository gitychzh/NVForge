# HM2 Optimize HM1 — Round R1382

## 触发分析
- **Cron 脚本输出**: "这是我提交的, 不触发" (false trigger, double-dispatch)
- **最新 commit**: 7590b17 (R1381, author=opc2_uname)
- **HM1 git log**: 停留在 R1206 (176 轮落后)
- **判定**: 误触发 — HM1 未提交任何新内容, 脚本正确检测到自提交

## HM1 数据收集 (6h 窗口, 2026-07-14 17:27 UTC)

### 6h SR 总览
- **30req/22OK/8fail = 73.3% SR**
- 8 失败全部 zombie_empty_completion (glm5_2_nv integrate)
- 0 ATE, 0 empty_200, 0 timeout, 0 tier_attempts, 0 fallback
- 0 dsv4p_nv traffic, 0 kimi_nv traffic, 0 ms_gw traffic

### 错误分类
| error_type | count |
|---|---|
| zombie_empty_completion | 8 |

### 按模型
| model | total | ok | fail | SR% |
|---|---|---|---|---|
| glm5_2_nv | 30 | 22 | 8 | 73.3 |

### 每小时 SR
| hour (UTC) | total | ok | fail | SR% |
|---|---|---|---|---|
| 11:00 | 3 | 3 | 0 | 100.0 |
| 12:00 | 4 | 2 | 2 | 50.0 |
| 13:00 | 6 | 4 | 2 | 66.7 |
| 14:00 | 5 | 4 | 1 | 80.0 |
| 15:00 | 4 | 3 | 1 | 75.0 |
| 16:00 | 6 | 5 | 1 | 83.3 |
| 17:00 | 2 | 1 | 1 | 50.0 |

### 最新 10 请求 (延迟)
| ts | model | status | dur_ms | error |
|---|---|---|---|---|
| 17:03 | glm5_2_nv | 502 | 6636 | zombie |
| 17:03 | glm5_2_nv | 200 | 6508 | — |
| 16:33 | glm5_2_nv | 200 | 7816 | — |
| 16:33 | glm5_2_nv | 200 | 6448 | — |
| 16:33 | glm5_2_nv | 200 | 8846 | — |
| 16:03 | glm5_2_nv | 502 | 8874 | zombie |
| 16:03 | glm5_2_nv | 200 | 8780 | — |
| 16:03 | glm5_2_nv | 200 | 11514 | — |
| 15:33 | glm5_2_nv | 502 | 12216 | zombie |
| 15:33 | glm5_2_nv | 200 | 15886 | — |

### 延迟特征
- 成功请求: 6.5-15.9s (正常 integrate 推理)
- 僵尸检测: 6.6-12.2s (网关在 3-15s 内检测到空完成并返回 502, 远优于旧版 96s 超时)
- 0 次 fallback 触发 — 僵尸检测直接返回 502, 不进入 fallback 链

## HM1 配置快照 (docker exec nv_gw env)
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=205
TIER_COOLDOWN_S=15
KEY_COOLDOWN_S=25
KEY_AUTHFAIL_COOLDOWN_S=60
MIN_OUTBOUND_INTERVAL_S=0
NVU_CONNECT_RESERVE_S=0
NVU_EMPTY_200_FASTBREAK=2
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_STREAM_FIRST_BYTE_DEADLINE_S=20
NVU_STREAM_TOTAL_DEADLINE_S=42
NVU_TIER_BUDGET_DSV4P_NV=106
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006
NVU_PEER_FB_SKIP_MODELS=
NVU_MS_GW_FALLBACK_TIMEOUT=195
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms
```
Compose md5: `f493494e2b41b17fbf5d9cff9093648e` (未变)

## 决策: NOP

### 零可修故障
- **zombie_empty_completion (8×)**: 全部 glm5_2_nv integrate, NVCF content-filter stop+12-36chars
  - 代码级行为 — 网关在 6-12s 检测到空完成并返回 502, 优于旧版 96s NVStream_TimeoutError
  - 非配置可修复 — NVCF 内容过滤停止流式输出, 网关正确检测并返回错误 chunk
  - FASTBREAK=1 已最优 (integrate 超时为 function-level, 无需多 key 验证)
  - Peer FB 已全开 (SKIP_MODELS=空), 但 zombie 不触发 fallback (网关直接返回 502)

### 无优化空间
- 0 dsv4p_nv traffic 6h+ — 无法验证 R1370 budget fix
- 0 kimi_nv traffic
- 0 ms_gw traffic — 无 ms_gw 优化机会 (R900 模式不适用)
- 0 tier_attempts — 无 key 级错误
- 0 fallback 触发 — 无 fallback 链问题
- 所有参数 floor/optimal — 无下调空间
- Compose md5 未变 — HM1 无 outside-loop 变更

### 铁律
- 只改 HM1 不改 HM2 ✅
- 改前必有数据 ✅ (DB 数据与 R1381 链一致)
- 数据不支持任何参数变更 → NOP

## ⏳ 轮到HM1优化HM2
