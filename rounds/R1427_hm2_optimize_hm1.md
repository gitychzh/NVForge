# HM2 Optimize HM1 — Round R1427

## 触发分析
cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author = opc2_uname (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (583rd chain of R1133 false-trigger sequence)

## 数据收集 (改前必有数据 — 2026-07-15 13:36 UTC)

### 容器状态
- nv_gw: Up 2 hours (healthy), started 2026-07-15T03:25:06Z
- ms_gw: running
- Compose md5: 59dc3c54c49324859d1d31e7e422b31b (unchanged from R1426)

### DB 6h窗口 (2026-07-15 07:36-13:36 UTC)
- 总体: 58req/43OK 74.1%SR. 14 zombie_empty_completion + 1 ATE (all_tiers_exhausted dsv4p_nv)
- ms_gw: 23/22 OK = 95.7% — healthy fallback
- 0 tier_attempts (clean cycle)
- fallback_occurred=t: 13/13 OK (100% ms_gw rescue)

### 按模型分组
| 模型 | 总请求 | OK | 失败 | SR% | 平均延迟 |
|------|--------|-----|------|-----|---------|
| glm5_2_nv | 44 | 36 | 8 | 81.8% | 12,033ms |
| dsv4p_nv | 14 | 7 | 7 | 50.0% | 24,554ms |

### 错误分类
| 错误类型 | 模型 | 数量 | 平均延迟 | 根本原因 |
|----------|------|------|---------|---------|
| zombie_empty_completion | glm5_2_nv | 8 | 7,208ms | NVCF content-filter (209K+ chars input, 12 chars content), fast abort integrate |
| zombie_empty_completion | dsv4p_nv | 6 | 17,574ms | NVCF content-filter (210K+ chars input, 12 chars content), fast abort pexec |
| all_tiers_exhausted | dsv4p_nv | 1 | 56,083ms | Genuine ATE, ms_gw couldn't rescue (single anomaly) |

### 按小时 SR
| Hour | Total | OK | Fail | SR% |
|------|-------|-----|------|-----|
| 00:00 | 4 | 4 | 0 | 100.0% |
| 01:00 | 6 | 5 | 1 | 83.3% |
| 02:00 | 6 | 4 | 2 | 66.7% |
| 03:00 | 9 | 5 | 4 | 55.6% |
| 04:00 | 7 | 3 | 4 | 42.9% |
| 05:00 | 26 | 22 | 4 | 84.6% |

### 容器环境 (关键参数)
```
UPSTREAM_TIMEOUT=66
TIER_COOLDOWN_S=15
KEY_COOLDOWN_S=25
TIER_TIMEOUT_BUDGET_S=205
NVU_TIER_BUDGET_DSV4P_NV=112
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_MS_GW_FALLBACK_TIMEOUT=195
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_PEER_FB_SKIP_MODELS=(empty)
NVU_FORCE_STREAM_UPGRADE=0
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
MIN_OUTBOUND_INTERVAL_S=0
```

### nv_gw 日志关键信号
- ms_gw fallback OK: glm5_2_nv -> glm5_2_ms, status=200, healthy (2 rescues in log tail)
- glm5_2_nv integrate: NVCF 400 "Inference error" -> INTEGRATE-FALLBACK -> ms_gw rescue success
- dsv4p_nv pexec: zombie_empty_completion detected, error-chunk sent to openclaw
- 4 zombies in log tail (2 dsv4p_nv + 2 glm5_2_nv)
- ms_gw: all MS-OK/MS-STREAM-DONE, healthy

## 决策: NOP — 零变更

### 僵尸诊断
- **14 zombie_empty_completion** (6 dsv4p_nv pexec + 8 glm5_2_nv integrate): NVCF content-filter 返回空内容 (input=210K+ chars, content=12 chars, finish_reason=stop). 网关正确检测并快速中止 (7-22s, 远优于旧 96s NVStream_TimeoutError). 发送 error-chunk 触发 openclaw 模型 fallback. **不可配置修复** — NVCF 内容过滤层面问题.
- **新观察**: dsv4p_nv pexec 路径也出现 zombie (之前主要在 glm5_2_nv integrate). 这是 NVCF 内容过滤对长上下文的通用行为, 非模型特定.

### ATE 诊断
- **1 dsv4p_nv ATE** (56,083ms, tiers_tried_count=1): 单次异常, ms_gw 未能挽救. 在 58 请求中仅 1 次 (1.7%). 无统计意义, 不构成优化信号.

### 参数评估
- 全部参数处于 floor/optimal 状态
- FASTBREAK=1 正确 (pexec/integrate 均为 function-level 信号)
- BUDGET=205 充足, ms_gw fallback 健康 (95.7% SR)
- 0 tier_attempts — 无 key 循环浪费
- ms_gw fallback 13/13 100% 挽救率

### 结论
- 无可配置修复的错误模式
- zombie=NVCF content-filter (代码级快速中止已部署)
- ATE=单次异常 (1.7% incidence)
- ms_gw 健康, fallback 100% 有效
- 所有参数 floor/optimal
- 铁律: 只改HM1不改HM2

## ⏳ 轮到HM1优化HM2
