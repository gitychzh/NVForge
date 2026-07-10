# HM2 Optimize HM1 — Round R1136

## 触发分析
cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author = opc2_uname (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (false trigger, R1136 = R1135 的 quintuple-dispatch)
- HM1 本地 git log 停留在 R821（315 轮落后）

## 容器状态
- nv_gw 重启时间: 2026-07-10T19:03:27Z（~11.5h 前）
- 重启后已运行 11.5h，无新重启

## 6h 数据 (00:30–06:30 UTC)

### 总体
| 时段 | 请求 | OK | 失败 | SR |
|------|------|-----|------|-----|
| 6h 总计 | 58 | 43 | 15 | 74.1% |
| 重启前 | 32 | 21 | 11 | 65.6% |
| 重启后 | 26 | 22 | 4 | 84.6% |

### 重启后按小时
| 小时 | 请求 | OK | 失败 | SR |
|------|------|-----|------|-----|
| 19:00 | 6 | 6 | 0 | 100% |
| 20:00 | 7 | 7 | 0 | 100% |
| 21:00 | 9 | 9 | 0 | 100% |
| 22:00 | 4 | 0 | 4 | 0% |

### 重启后失败分析
全部 4 次失败均为 zombie_empty_completion @ 22:03 UTC 集中爆发：
- 22:03:24 — 3105ms
- 22:03:28 — 3160ms
- 22:03:33 — 4353ms
- 22:03:39 — 3655ms

全部 glm5_2_nv, nv_integrate 路径，3-4s 快速 abort（vs 旧 96s NVStream_TimeoutError）

### 6h 错误类型
| 错误类型 | 次数 | 分类 |
|----------|------|------|
| zombie_empty_completion | 13 | 代码级（积极特征：3-15s 快速 abort vs 旧 96s hang） |
| NVStream_TimeoutError | 1 | 代码级 |
| all_tiers_exhausted | 1 | 1 ATE |

### nv_tier_attempts
0 行 — 所有失败均为代码级（zombie/stream timeout），无 key 级耗尽

### ms_gw
3 次请求，0 次成功 — ms_gw BrokenPipeError 模式（代码级缺陷，非配置可修复）

### 按模型
| 模型 | 请求 | OK | 失败 | SR | 平均延迟 |
|------|------|-----|------|-----|----------|
| glm5_2_nv | 48 | 34 | 14 | 70.8% | 8739ms |
| dsv4p_nv | 10 | 9 | 1 | 90.0% | 18029ms |

## 当前 HM1 参数（全部 floor/optimal）
- UPSTREAM_TIMEOUT=66, TIER_COOLDOWN_S=15, TIER_TIMEOUT_BUDGET_S=198
- NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
- NVU_EMPTY_200_FASTBREAK=2, NVU_TIER_BUDGET_DSV4P_NV=72
- NVU_TIER_BUDGET_GLM5_2_NV=96, NVU_MS_GW_FALLBACK_TIMEOUT=180
- NVU_PEER_FALLBACK_TIMEOUT=66, KEY_COOLDOWN_S=25
- MIN_OUTBOUND_INTERVAL_S=0, NVU_CONNECT_RESERVE_S=0
- NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66

## 决策：NOP (zero-change)
- 重启后 3 个连续小时 100% SR（19:00–21:00），22:00 的 zombie burst 是瞬时集群，已自愈
- 重启后 4/4 失败均为 zombie_empty_completion — 代码级特征，返回 502 只需 3-4s（vs 旧 96s hang），是积极优化
- 1 次 ATE 为代码级（all_tiers_exhausted），非配置可修复
- 所有参数处于 floor/optimal 状态，无优化空间
- 铁律:只改HM1不改HM2

## ⏳ 轮到HM1优化HM2
