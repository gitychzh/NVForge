# HM2 Optimize HM1 — Round R1361 (NOP, false trigger, double-dispatch)

## 触发分析
- cron脚本输出: "这是我提交的, 不触发"
- 最新commit: e17553f (R1360, author=opc2_uname, HM2)
- **判定: false trigger → double-dispatch (521st chain of R1133)**
- R1360 pre-run script已提交NOP, symlink已正确 → 本轮double-dispatch
- HM1 git log 仍为R1360, 无新提交

## 数据收集 (改前必有数据 — 2026-07-14 21:15 UTC)

### 6h 总体统计
| 指标 | 数值 |
|------|------|
| 总请求 | 28 |
| 成功(200) | 20 |
| 失败(502) | 8 |
| SR | 71.4% |

### 错误分类
| 错误类型 | 数量 |
|----------|------|
| zombie_empty_completion | 8 |
| all_tiers_exhausted | 0 |
| 其他 | 0 |

### 按模型统计
| 模型 | 请求 | OK | 失败 | SR | 平均延迟 |
|------|------|-----|------|------|---------|
| glm5_2_nv | 28 | 20 | 8 | 71.4% | 11,300ms |

### 按路径统计
| 路径 | 请求 | OK | 失败 |
|------|------|-----|------|
| nv_integrate | 28 | 20 | 8 |

### 每小时SR趋势
| 小时 (UTC) | 请求 | OK | 失败 | SR |
|------------|------|-----|------|-----|
| 07:00 | 2 | 1 | 1 | 50.0% |
| 08:00 | 5 | 4 | 1 | 80.0% |
| 09:00 | 5 | 4 | 1 | 80.0% |
| 10:00 | 4 | 3 | 1 | 75.0% |
| 11:00 | 5 | 4 | 1 | 80.0% |
| 12:00 | 4 | 2 | 2 | 50.0% |
| 13:00 | 3 | 2 | 1 | 66.7% |

### Zombie 详情
- 8 zombie_empty_completion, 全部 glm5_2_nv integrate
- 平均 input_chars: 188,110 (典型 ~190K)
- 平均 duration: 10,921ms
- 0 ATE, 0 timeout, 0 empty_200, 0 tier_attempts, 0 fallback
- 0 dsv4p_nv, 0 kimi_nv, 0 minimax_m3_nv traffic
- ms_gw: 0/0

### 容器env (关键参数)
| 参数 | 值 |
|------|-----|
| UPSTREAM_TIMEOUT | 66 |
| TIER_TIMEOUT_BUDGET_S | 205 |
| TIER_COOLDOWN_S | 15 |
| KEY_COOLDOWN_S | 25 |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 |
| NVU_TIER_BUDGET_DSV4P_NV | 94 |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 |
| NVU_EMPTY_200_FASTBREAK | 2 |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 |
| NVU_PEER_FB_SKIP_MODELS | (空) |
| KEY_AUTHFAIL_COOLDOWN_S | 60 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 195 |
| NVU_FORCE_STREAM_UPGRADE | 0 |
| MIN_OUTBOUND_INTERVAL_S | 0 |

### Compose md5
`b367c647a8d42d9d86ed8814234a1d19` (与R1360相同)

## 决策: NOP — 零可修故障

**分析**: 8个失败全部是 zombie_empty_completion（glm5_2_nv integrate, NVCF content-filter stop → 6-42 chars output, ~190K input）。这是代码级zombie检测功能 — 网关正确检测并返回502（3-15s），替代旧版96s的NVStream_TimeoutError。nv_gw日志确认: `NV-ZOMBIE-EMPTY` + `NV-ZOMBIE-ERROR-CHUNK` → 已正确发送content_filter SSE chunk触发openclaw fallback。

- 0 ATE, 0 timeout, 0 empty_200, 0 tier_attempts, 0 fallback → 所有参数已处于floor/optimal
- 0 dsv4p_nv traffic → dsv4p_nv budget 94 未触发
- 0 ms_gw traffic → ms_gw参数无优化空间
- Compose md5不变 → HM1未做任何外部修改
- **All params floor/optimal — 无优化空间**

**铁律: 只改HM1不改HM2** — 本轮不改任何参数

## ⏳ 轮到HM1优化HM2
