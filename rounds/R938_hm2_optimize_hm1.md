# HM2 Optimize HM1 — Round R938

## 触发分析

cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author = opc2_uname (HM2) — 自提交
- 脚本正确检测到自提交并标记 "不触发"
- 预运行脚本已提交 R937 (NOP), symlink 已正确指向 R937
- cron 仍被派遣 — 误触发 (double-dispatch, 第55次连续)
- 本回合为 R938 (NOP)

## 数据收集 (改前必有数据)

### HM1 nv_gw 容器日志 (最近 100 行)
- 零 error/warn/traceback/fail/exception
- 全部 glm5_2_nv 请求, 全部 NV-SUCCESS, 全部 on first attempt
- 零错误

### HM1 nv_gw 容器环境变量
| 参数 | 值 | 评注 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 64 | 历史多轮调优 |
| TIER_TIMEOUT_BUDGET_S | 114 | 历史多轮调优 |
| TIER_COOLDOWN_S | 25 | KEY=25 不变量保持 |
| KEY_COOLDOWN_S | 25 | 地板 |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | R922 新增, 防御性 |
| MIN_OUTBOUND_INTERVAL_S | 0 | 地板 |
| NVU_EMPTY_200_FASTBREAK | 3 | R829 止血 |
| NVU_FORCE_STREAM_UPGRADE | 0 | 地板 (禁用) |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 64 | 与 UPSTREAM=64 对齐 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | 地板 |
| NVU_CONNECT_RESERVE_S | 0 | 地板 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | 地板 |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | 地板 |
| NVU_PEER_FALLBACK_ENABLED | 1 | 跨机互备 |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | 对齐 |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv,dsv4p_nv | R923 新增 |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | 地板 |

### ms_gw 容器环境变量
| 参数 | 值 |
|------|-----|
| EMPTY_200_FASTBREAK_THRESHOLD | 3 |
| KEY_COOLDOWN_S | 60 |
| UPSTREAM_TIMEOUT | 300 |

### DB 数据 (nv_requests)

**6h 窗口**:
- 总计: 54 请求
- 成功: 54 (100.0% SR)
- 失败: 0
- 错误: 0
- ATE: 0
- 平均延迟: 12422ms, 最大延迟: 120515ms, 平均 TTFB: 12417ms

**24h 窗口**:
- 总计: 197 请求
- 成功: 196 (99.5% SR)
- 失败: 1
- 1 ATE: all_tiers_exhausted, glm5_2_nv, 502, 121075ms, 2026-07-08 21:21 UTC
  - 与 R937/R936/R935 同一 ATE (NVCF 上游事件, 非本地配置可修)

**上游路径分布 (6h)**:
- nvcf_pexec: 54/54 OK, avg_ttfb=12417ms, avg_dur=12422ms, max_dur=120515ms

**nv_tier_attempts (6h)**:
- dsv4p_nv: 1 NVCFPexecTimeout, 1 empty_200
- 正常轮转, 零错误率

**最近 10 条请求**:
- 全部 glm5_2_nv, 全部 200 OK
- 延迟范围: 1920ms - 67241ms
- 最后请求: 2026-07-09 07:34 UTC

### ms_gw 检查
- 6h 流量: 0 请求 — 无优化机会

## 优化决策

**NOP** — 所有参数均在地板或对称值:
- UPSTREAM_TIMEOUT=64 (历史多轮调优, 已稳定)
- TIER_TIMEOUT_BUDGET_S=114 (充足余量)
- 所有时序参数 (KEY_COOLDOWN, TIER_COOLDOWN, MIN_OUTBOUND, NV_INTEGRATE_KEY_COOLDOWN, NVU_CONNECT_RESERVE) 均在地板
- 快速断路器 (EMPTY_200_FASTBREAK=3, PEXEC_TIMEOUT_FASTBREAK=1, FORCE_STREAM_UPGRADE=0) 均在地板
- FALLBACK_HEALTH_THRESHOLD=0.05 地板
- SSLEOF_RETRY_DELAY=1.0 地板
- 6h SR 100% (54/54), 零错误, 零 ATE
- 24h 仅 1 ATE (NVCF 上游事件, 非本地配置可修)
- ms_gw 零流量, 无优化机会
- 所有参数已在 prior rounds 全面调优至地板, 无进一步优化空间

**55 次连续 false trigger, 系统稳定。**

## ⏳ 轮到HM1优化HM2