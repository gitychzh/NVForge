# HM2 Optimize HM1 — Round R1371

## 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = opc2_uname (HM2)，R1370 刚提交
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (false trigger, double-dispatch, 530th chain of R1133)

## 数据采集 (改前必有数据)

### HM1 容器状态
- nv_gw: Up 5 minutes (healthy), 重启于 2026-07-14T15:25:43Z (R1370 部署)
- compose md5: f493494e2b41b17fbf5d9cff9093648e (R1370 写入后)

### HM1 nv_gw 关键参数
| 参数 | 值 |
|------|-----|
| UPSTREAM_TIMEOUT | 66 |
| TIER_TIMEOUT_BUDGET_S | 205 |
| NVU_TIER_BUDGET_DSV4P_NV | 106 (R1370: 94→106) |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 |
| TIER_COOLDOWN_S | 15 |
| KEY_COOLDOWN_S | 25 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 |
| NVU_EMPTY_200_FASTBREAK | 2 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 195 |
| NVU_PEER_FALLBACK_ENABLED | 1 |
| NVU_PEER_FALLBACK_TIMEOUT | 66 |
| NVU_PEER_FB_SKIP_MODELS | (空) |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 |

### 6h DB 数据 (nv_requests)
- 29req/22OK(75.9%)/7fail
- 所有失败: zombie_empty_completion (7)
- 0 ATE, 0 timeout, 0 empty_200, 0 tier_attempts, 0 fallback
- 仅 glm5_2_nv 流量，0 dsv4p_nv/0 kimi_nv/0 minimax_m3_nv
- ms_gw: 0/0 (DB窗口内无 ms_gw 请求)

### 6h 逐小时
| 小时 (UTC) | total | ok | fail | SR% |
|-----------|-------|-----|------|-----|
| 09:00 | 3 | 3 | 0 | 100.0 |
| 10:00 | 4 | 3 | 1 | 75.0 |
| 11:00 | 5 | 4 | 1 | 80.0 |
| 12:00 | 4 | 2 | 2 | 50.0 |
| 13:00 | 6 | 4 | 2 | 66.7 |
| 14:00 | 5 | 4 | 1 | 80.0 |
| 15:00 | 2 | 2 | 0 | 100.0 |

### 24h dsv4p_nv ATE (R1370 前)
- 9 ATE: all_tiers_exhausted, tiers_tried=1, fallback_actually_attempted=false
- 全部 ~72s (3 on 07-13, 6 on 07-14 05:00-06:37 UTC)
- dsv4p_nv 成功 p95=40,162ms
- R1370: NVU_TIER_BUDGET_DSV4P_NV 94→106 (+12s), key2 budget = 106-66=40s, 覆盖 p95=40.2s

### ms_gw 日志
- 活跃: dsv4p_ms → DeepSeek-V4-Pro, MS-STREAM-DONE 正常
- EMPTY_200_FASTBREAK_THRESHOLD=3, UPSTREAM_TIMEOUT=300
- 健康，无异常

## 分析

- **零可修故障**: 7 失败全部 zombie_empty_completion (code-level, NVCF content-filter stop+少量 chars, 非 config 可修)
- **0 ATE, 0 timeout, 0 empty_200, 0 tier_attempts, 0 fallback**: 系统实际无配置可修的故障
- **R1370 刚部署 5 分钟**: NVU_TIER_BUDGET_DSV4P_NV 94→106, post-restart 0 流量，需等待下一轮验证效果
- **ms_gw 健康**: dsv4p_ms 正常处理，EMPTY_200_FASTBREAK_THRESHOLD=3 已到位
- **所有参数 floor/optimal**: 无优化空间

## 决策: NOP

零参数变更，零 compose 变更，零容器重启。
铁律:只改HM1不改HM2

## ⏳ 轮到HM1优化HM2
