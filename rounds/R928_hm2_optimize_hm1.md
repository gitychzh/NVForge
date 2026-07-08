# HM2 Optimize HM1 — Round R928

**时间**: 2026-07-09 06:00 UTC  
**角色**: HM2 → HM1 优化执行者  
**触发类型**: 误触发 (double-dispatch)

## 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`  
- 最新 commit author = opc2_uname (HM2)  
- 脚本检测为自提交，标记 "不触发"  
- cron 仍被派遣 — double-dispatch (R927 已由前一次派遣处理)  
- HM1 本地 git log 停留在 R821（106 轮落后）  
- 预运行脚本已 commit R927 NOP + symlink fix

## HM1 数据收集 (改前必有数据)

### nv_gw 配置
| 参数 | 值 |
|---|---|
| UPSTREAM_TIMEOUT | 64 (R751) |
| TIER_TIMEOUT_BUDGET_S | 114 (R707) |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 (R768) |
| MIN_OUTBOUND_INTERVAL_S | 0 |
| KEY_COOLDOWN_S | 25 |
| TIER_COOLDOWN_S | 25 |
| NVU_CONNECT_RESERVE_S | 0 |
| NVU_EMPTY_200_FASTBREAK | 3 (R900) |
| NVU_FORCE_STREAM_UPGRADE | 0 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 64 (R751) |
| KEY_AUTHFAIL_COOLDOWN_S | 60 (R922) |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv,dsv4p_nv (R923) |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 |

### nv_gw 6h 统计
| 指标 | 值 |
|---|---|
| 总请求 | 57 |
| 成功 (200) | 57 (100.0%) |
| 失败 | 0 |
| ATE (502) | 0 |
| errors/warns (logs) | 0 |

### nv_gw 最近 10 请求
全部 `glm5_2_nv` → 200 OK, duration 2764-12893ms, 均正常。最新请求: 2026-07-08 21:33 UTC (~14h 前)。

### Fallback 统计
- fallback_occurred=true + actually_attempted=true: 1 (glm5_2_nv → dsv4p_nv, 成功)

### ms_gw 6h 统计
- 0 请求，零流量。所有参数已在地板值 (EMPTY_200_FASTBREAK_THRESHOLD=3, KEY_COOLDOWN_S=60)。

## 决策

**NOP — 零参数字段优化**。

nv_gw: 57/57 100% SR, 零 ATE, 零 error/warn, 所有参数在地板值。无优化空间。  
ms_gw: 零流量，参数已在地板值。无优化空间。

HM1 持续的 silence（106 轮落后于 HM2）不是配置问题 — HM1 的 agent 未被 cron 触发或未执行。nv_gw 本身完全健康。

## ⏳ 轮到HM1优化HM2
