# R1383: HM2→HM1 — NOP (false trigger, double-dispatch, 零可修故障, 542nd chain of R1133)

## 触发分析
- **cron 脚本输出**: 检测到 HM1 提交新 commit → 触发 HM2 优化
- **最新 commit**: a920849 (R1382, author=opc2_uname, HM2 自提交)
- **git log**: HEAD=origin/main, 均为 opc2_uname (HM2), 无 HM1 (opc_uname) 新提交
- **HM1 git log**: 停留在 R1206 (184 轮落后)
- **判定**: 误触发 — HM1 未提交任何新内容, 脚本检测到 HM2 自提交后仍被派遣

## 数据收集 (改前必有数据, 2026-07-14 12:00–17:00 UTC)

### 6h SR 总览
| Metric | Value |
|---|---|
| Total requests | 29 |
| OK (200) | 20 |
| Failed (502) | 9 |
| SR | 69.0% |
| Tier attempts | 0 |
| ATE | 0 |
| empty_200 | 0 |
| Timeout | 0 |
| Fallback | 0 |
| dsv4p_nv traffic | 0 |
| kimi_nv traffic | 0 |
| ms_gw traffic | 0 |
| Compose md5 | f493494e (unchanged) |

### 错误分类
| error_type | count | avg_dur_ms |
|---|---|---|
| zombie_empty_completion | 9 | 10,182 |

### 按模型
| model | total | ok | fail | SR% |
|---|---|---|---|
| glm5_2_nv | 29 | 20 | 9 | 69.0 |

### 每小时 SR
| hour (UTC) | total | ok | fail | SR% |
|---|---|---|---|
| 12:00 | 4 | 2 | 2 | 50.0 |
| 13:00 | 6 | 4 | 2 | 66.7 |
| 14:00 | 5 | 4 | 1 | 80.0 |
| 15:00 | 4 | 3 | 1 | 75.0 |
| 16:00 | 6 | 5 | 1 | 83.3 |
| 17:00 | 4 | 2 | 2 | 50.0 |

### 最新 10 请求 (延迟)
| ts | model | status | dur_ms | error |
|---|---|---|---|---|
| 17:33 | glm5_2_nv | 502 | 11,169 | zombie |
| 17:33 | glm5_2_nv | 200 | 6,374 | — |
| 17:03 | glm5_2_nv | 502 | 6,636 | zombie |
| 17:03 | glm5_2_nv | 200 | 6,508 | — |
| 16:33 | glm5_2_nv | 200 | 7,816 | — |
| 16:33 | glm5_2_nv | 200 | 6,448 | — |
| 16:33 | glm5_2_nv | 200 | 8,846 | — |
| 16:03 | glm5_2_nv | 502 | 8,874 | zombie |
| 16:03 | glm5_2_nv | 200 | 8,780 | — |
| 16:03 | glm5_2_nv | 200 | 11,514 | — |

### 延迟特征
- 成功请求: 6.4-11.5s (正常 integrate 推理)
- 僵尸检测: 6.6-11.2s (网关在 3-15s 内检测到空完成并返回 502)
- 0 次 fallback 触发 — 僵尸检测直接返回 502, 不进入 fallback 链

### 日志 (last 100 lines, error/warn)
```
NV-INTEGRATE-ERR k2 SSLEOFError (1 occurrence, 23:33:41, cycled to k3 → success)
NV-ZOMBIE-EMPTY glm5_2_nv (4 occurrences, content_chars=12-42, finish_reason=stop)
NV-ZOMBIE-ERROR-CHUNK (4 occurrences, sent content_filter error SSE)
```
- 0 NV-TIER-FAIL, 0 NV-EMPTY-FASTBREAK, 0 NV-GLOBAL-COOLDOWN
- 0 NV-EMPTY-200, 0 NV-TIMEOUT, 0 NV-ATE
- 0 NV-INTEGRATE-TIMEOUT, 0 NV-PEER-FB, 0 NV-MS-FB

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
NV_INTEGRATE_KEY_COOLDOWN_S=0
NV_INTEGRATE_MODELS=glm5_2_nv
```
Compose md5: `f493494e2b41b17fbf5d9cff9093648e` (未变)

## 决策: NOP

### 零可修故障
- **zombie_empty_completion (9×)**: 全部 glm5_2_nv integrate, NVCF content_filter stop+12-42chars
  - 代码级行为 — 网关在 6-12s 检测到空完成并返回 502, 优于旧版 96s NVStream_TimeoutError
  - 非配置可修复 — NVCF 内容过滤停止流式输出, 网关正确检测并返回错误 chunk
  - FASTBREAK=1 已最优 (integrate 超时为 function-level, 无需多 key 验证)
  - Peer FB 已全开 (SKIP_MODELS=空), 但 zombie 不触发 fallback (网关直接返回 502)

### 无优化空间
- 0 dsv4p_nv traffic 6h+ — 无法验证 R1370 budget fix
- 0 kimi_nv traffic
- 0 ms_gw traffic — 无 ms_gw 优化机会
- 0 tier_attempts — 无 key 级错误
- 0 fallback 触发 — 无 fallback 链问题
- 1 SSLEOFError (k2) — 成功 cycle 到 k3, 无需调整
- 所有参数 floor/optimal — 无下调空间
- Compose md5 未变 — HM1 无 outside-loop 变更

### 铁律
- 只改 HM1 不改 HM2 ✅
- 改前必有数据 ✅ (DB 数据与 R1376-R1382 链一致)
- 数据不支持任何参数变更 → NOP

## ⏳ 轮到HM1优化HM2
