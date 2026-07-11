# HM2 Optimize HM1 — Round R1160

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = opc2_uname (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (false trigger)
- R1159 已提交，锚点已指向 R1159
- HM1 本地 git log 停留在 R821（339 轮落后）
- 这是 R1133 误触发链的第 29 轮 (R1133→R1160)

## 2. HM1 数据收集 (改前必有数据)

### 2.1 容器状态
- 容器: nv_gw (Up 16h+ since 2026-07-10T19:03:27Z)
- compose md5: `7975939c245761e451a8813852dcb9bf` (未变，与 R1133 相同)
- FALLBACK_GRAPH: {} (空，预期状态)
- tier_chain: ['glm5_2_nv'] (no fallback, 3model) — 预期状态

### 2.2 Docker 日志 (最近 100 行)
全为 zombie_empty_completion 模式:
- [NV-ZOMBIE-EMPTY] glm5_2_nv: finish_reason=stop, content_chars=12 < 50, input_chars=164K-167K
- [NV-ZOMBIE-ERROR-CHUNK] 发送 content_filter error SSE chunk
- 间隔 ~30min 规律出现 (openclaw 定时任务)
- 无 NVCFPexecTimeout, NVCFPexecSSLEEOFError, 无 ATE, 无 fallback 触发

### 2.3 环境变量 (关键参数)
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=198
TIER_COOLDOWN_S=15
KEY_COOLDOWN_S=25
KEY_AUTHFAIL_COOLDOWN_S=60
MIN_OUTBOUND_INTERVAL_S=0
NVU_CONNECT_RESERVE_S=0
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_STREAM_FIRST_BYTE_DEADLINE_S=20
NVU_STREAM_TOTAL_DEADLINE_S=42
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
NVU_MS_GW_FALLBACK_TIMEOUT=180
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
NVU_TIER_BUDGET_DSV4P_NV=72
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
```

### 2.4 DB 数据 (6h 窗口: 2026-07-11 04:30-10:30 UTC)

**6h 总体**: 45req/23OK(51.1%)/22fail
- 与 R1159 完全相同 (45req/23OK(51.1%)/22fail)

**按模型**:
| model | cnt | ok | err | sr_pct |
|-------|-----|----|-----|--------|
| glm5_2_nv | 45 | 23 | 22 | 51.1% |

**按上游路径**:
| upstream_type | cnt | ok | err | avg_ttfb | avg_dur |
|--------------|-----|----|-----|----------|---------|
| nv_integrate | 45 | 23 | 22 | 4786 | 4977 |

**错误类型**:
| error_type | cnt |
|-----------|-----|
| zombie_empty_completion | 22 |

**按小时**:
| hour | total | ok | fail | sr_pct |
|------|-------|----|------|--------|
| 20:00 | 5 | 5 | 0 | 100.0% |
| 21:00 | 9 | 9 | 0 | 100.0% |
| 22:00 | 9 | 1 | 8 | 11.1% |
| 23:00 | 9 | 4 | 5 | 44.4% |
| 00:00 | 7 | 1 | 6 | 14.3% |
| 01:00 | 4 | 2 | 2 | 50.0% |
| 02:00 | 2 | 1 | 1 | 50.0% |

**tiers_tried_count**: 所有 22 失败 = 1 (avg 4,338ms, 快速 zombie abort)
**fallback**: 0 触发 (fallback_occurred=f for all 45)
**tier_attempts**: 仅 3 条 429_integrate_rate_limit (轻微)
**ms_gw**: 0 流量 6h

### 2.5 ms_gw 日志
- 仅 4 条 MS-OK-STREAM / MS-STREAM-DONE (glm5.2 + deepseek-v4-pro)
- 1 条 MS-STREAM-CLIENT-EOF (BrokenPipeError)
- 无异常流量

## 3. 分析

### 3.1 数据与 R1159 完全一致
- 6h: 45req/23OK(51.1%)/22zombie — 与 R1159 相同
- 所有失败: zombie_empty_completion (glm5_2_nv integrate, NVCF content-filter stop+12chars, 164K-167K input)
- dsv4p_nv: 0 流量 6h (自 restart 以来 0 ATE)
- ms_gw: 0 流量
- kimi_nv + minimax_m3_nv: 0 流量
- 0 fallback 触发, 0 ATE (非 zombie)
- 仅 3 条 429_integrate_rate_limit (轻微，无影响)

### 3.2 僵尸模式确认
- NVCF content-filter 对 164K-167K 输入返回 stop+12chars
- 网关 zombie 检测正确: 3-12s 快速 abort (vs 旧 96s hang)
- error-chunk 正确发送 content_filter SSE
- 这是 NVCF 上游行为，非 config-fixable

### 3.3 参数状态
- 所有 FASTBREAK 参数在地板值 (1/2)
- BUDGET=198 充足
- 所有效果参数已优化到最优
- compose md5 48h+ 未变
- 容器 16h+ 未重启

## 4. 决策: NOP

**理由**: 零 config-fixable 问题。所有失败为 zombie_empty_completion (NVCF 上游 content-filter 行为，代码级快速 abort 已正确工作)。所有参数在地板/最优值。ms_gw 0 流量无优化空间。无 ATE，无 fallback 失败，无 tier_attempts 异常。数据与 R1159 相同。

**更改**: 零参数更改，零 compose 更改，零容器重启。

- 铁律:只改HM1不改HM2

## ⏳ 轮到HM1优化HM2
