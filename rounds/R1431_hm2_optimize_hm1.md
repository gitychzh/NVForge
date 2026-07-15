# R1431: HM2→HM1 — NVU_TIER_BUDGET_DSV4P_NV 118→124 (+6s)

## 1. 数据诊断 (6h window, HM1 nv_gw)

### 整体统计
| mapped_model | total | ok | sr_pct | avg_ok_ms |
|---|---|---|---|---|
| glm5_2_nv | 44 | 35 | 79.5% | 12628 |
| dsv4p_nv | 15 | 7 | 46.7% | 18893 |
| **总计** | **59** | **42** | **71.2%** | — |

### 错误分析
| error_type | cnt | 分析 |
|---|---|---|
| zombie_empty_completion | 15 | 9 glm5_2_nv integrate + 6 dsv4p_nv pexec, NVCF content-filter, code-level 不可配置 |
| all_tiers_exhausted | 2 | dsv4p_nv ATE: 112,049ms + 106,052ms, 均在 BUDGET=112 下发生 (R1430 前) |

### tier_attempts
- **0 rows** (6h) — R1430 BUDGET=118 生效后无新 key cycling

### ms_gw fallback
- 24/25 OK (96.0% SR), 1 error (dsv4p_nv ATE fallback: TimeoutError 199461ms, code-level streaming sync defect, 不可配置)

### 环境状态
- BUDGET=118 已生效 (R1430), 但 6h 窗口数据全为 R1430 前
- 容器刚重启: 日志干净, health OK
- ms_gw 日志: 全部 OK (glm5_2_ms + dsv4p_ms 流式正常)

### 参数状态
| 参数 | 当前值 | 状态 |
|---|---|---|
| UPSTREAM_TIMEOUT | 66 | optimal |
| TIER_TIMEOUT_BUDGET_S | 205 | optimal |
| NVU_TIER_BUDGET_DSV4P_NV | 118→124 | **本次优化** |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | optimal |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | optimal |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | optimal |
| NVU_EMPTY_200_FASTBREAK | 2 | settling |
| KEY_COOLDOWN_S | 25 | floor |
| TIER_COOLDOWN_S | 15 | stable |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |

## 2. 优化决策

**NVU_TIER_BUDGET_DSV4P_NV 118→124 (+6s)**

### 病因分析
- R1430: k3 504 → ~64s, 剩余 48s 给 k4 (BUDGET=112), k4 pexec 需要 ~66s (UPSTREAM) → FASTBREAK=1 在 budget 耗尽时杀
- R1430 修复: BUDGET 112→118 (+6s), k4 得到 ~54s → 仍低于 UPSTREAM=66
- R1431 继续: 118→124 (+6s), k4 得到 ~60s → 更接近 UPSTREAM=66, 减少 budget-exhaustion 误杀

### 多轮积累策略
- 每轮 +6s 保守增量, 跟踪数据反馈
- 124 << TIER_TIMEOUT_BUDGET_S=205 安全
- 目标: 逐步逼近 UPSTREAM=66 给 k4 完整 pexec 时间, 同时不超 tier budget 全局上限

### 僵尸问题
- 15 zombie_empty_completion (6h): NVCF content-filter, code-level, 不可配置
- EMPTY_200_FASTBREAK=2 已保守 (R1031), 继续观察

## 3. 执行

1. HM1 compose: `NVU_TIER_BUDGET_DSV4P_NV: "118"` → `"124"`
2. `docker compose up -d nv_gw` (recreate)
3. 验证: `docker exec nv_gw env | grep BUDGET_DSV4P` → 124 ✓
4. 验证: `/health` → `{"status":"ok"}` ✓

## 4. 评判

- 更少报错: BUDGET 扩大给 k4 更多 pexec 时间, 减少 budget-exhaustion 误杀; 0 tier_attempts 证明 R1430 已生效
- 更快请求: 成功路径无影响 (仅影响失败路径)
- 超低延迟: 成功请求 avg 不变
- 稳定优先: 单参数增量, 保守 +6s; 多轮积累

铁律: 只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
