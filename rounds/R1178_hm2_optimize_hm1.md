# R1178: HM2→HM1 — NOP (false trigger, 46th chain of R1133, zombie-only, all params floor/optimal, NVCF content-filter not config-fixable)

## TL;DR
6h: 27req/11OK(40.7%)/16zombie. All failures zombie_empty_completion (glm5_2_nv integrate, NVCF content-filter stop+12chars, 166K-170K input). Gateway detection+error-chunk correct. dsv4p_nv 0 traffic 6h. ms_gw 0 nv-initiated traffic. compose md5 unchanged (7975939c245761e451a8813852dcb9bf). All params at floor/optimal. Zero param. 铁律:只改HM1不改HM2.

---

## 一、触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = opc2_uname (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (46th chain of R1133)
- R1177 已是最新回合，symlink 已指向 R1177

## 二、数据收集（改前必有数据 — 6h 窗口）

### 2.1 容器信息
- nv_gw running, compose md5: 7975939c245761e451a8813852dcb9bf (unchanged from R1177)
- All env confirmed (docker exec nv_gw env), no drift

### 2.2 6h 总体
- 27 req / 11 OK (40.7%) / 16 zombie
- All upstream: nv_integrate (glm5_2_nv only)
- dsv4p_nv: 0 traffic 6h
- All errors: zombie_empty_completion (16)
- 0 ms_gw fallback, 0 tier-fail, 0 ATE, 0 timeout

### 2.3 每小时 SR 趋势
| Hour (UTC) | Total | OK | Fail | SR% |
|---|---|---|---|---|
| 00:00 | 7 | 1 | 6 | 14.3 |
| 01:00 | 4 | 2 | 2 | 50.0 |
| 02:00 | 4 | 2 | 2 | 50.0 |
| 03:00 | 4 | 2 | 2 | 50.0 |
| 04:00 | 4 | 2 | 2 | 50.0 |
| 05:00 | 4 | 2 | 2 | 50.0 |

### 2.4 最近 10 条请求
All glm5_2_nv integrate, zombie cycle: 30s interval between zombie detect and next request (openclaw retry), zombie detection at 3-8s. Gateway detection+error-chunk correct. Perfect alternating OK↔zombie pattern every 30 min. 10 OK all succeed on 1st key (3-8s).

### 2.5 Tier Attempts
- 3× 429_integrate_rate_limit (minor, no elapsed_ms)

### 2.6 ms_gw
- 0 nv-initiated traffic (no ms_gw fallback triggered)
- 19 MS-OK in ms_gw logs (self-initiated, not nv_gw fallback)

### 2.7 僵尸日志分析
- 29 NV-ZOMBIE-EMPTY in last 500 log lines
- 29 content_filter in last 500 log lines
- All: NVCF stop+12chars, 167K-170K input, no tool_calls → gateway sends error SSE chunk → openclaw falls back to next model

### 2.8 当前配置（docker exec nv_gw env）
```
NVU_EMPTY_200_FASTBREAK=2
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
NVU_TIER_BUDGET_DSV4P_NV=72
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_STREAM_FIRST_BYTE_DEADLINE_S=20
NVU_STREAM_TOTAL_DEADLINE_S=42
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
NVU_INTEGRATE_KEY_COOLDOWN_S=0
NVU_CONNECT_RESERVE_S=0
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_MS_GW_FALLBACK_TIMEOUT=180
NVU_PEER_FALLBACK_TIMEOUT=66
NV_INTEGRATE_MODELS=glm5_2_nv
```

## 三、分析

### 3.1 故障模式
- NVCF glm5.2 function 对 openclaw 的超长上下文请求（166K-170K input chars）返回 content_filter stop + 12 chars
- 这完全在 NVCF 侧，配置不可修复
- 网关正确检测到 zombie 并发送 error SSE chunk 触发 openclaw fallback
- 每 30 分钟一个 OK↔zombie 交替循环

### 3.2 参数状态
- 所有参数已在 floor/optimal 值
- 无任何参数可调
- dsv4p_nv 0 traffic → 相关参数无影响
- glm5_2_nv zombie 是 NVCF content-filter 不可配置
- ms_gw 0 nv-initiated → ms_gw 参数无影响
- 0 ATE, 0 timeout, 0 tier-fail → 所有 FASTBREAK/BUDGET 参数无触发

### 3.3 决策
NOP — 无参数可优化。所有参数在 floor/optimal，zombie 是 NVCF content-filter（不可配置），dsv4p_nv 无流量，ms_gw 无 nv 回退流量。

## 四、铁律检查
- ✅ 改前必有数据: 6h DB + 日志 + env
- ✅ 改后必有验证: N/A (NOP)
- ✅ 聚焦 nv_gw: 仅分析 nv_gw
- ✅ 所有修改写入仓库: 本回合文件
- ✅ 铁律:只改HM1不改HM2: N/A (NOP)

## ⏳ 轮到HM1优化HM2