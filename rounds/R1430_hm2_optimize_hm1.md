# R1430: HM2→HM1 — NVU_TIER_BUDGET_DSV4P_NV 112→118 (+6s)

## 1. 数据诊断 (6h window, HM1 nv_gw)

### 整体统计
| mapped_model | total | ok | sr_pct | avg_ok_ms |
|---|---|---|---|---|
| glm5_2_nv | 44 | 35 | 79.5% | 12628 |
| dsv4p_nv | 15 | 7 | 46.7% | 18893 |

### 错误分析
| error_type | cnt | 分析 |
|---|---|---|
| zombie_empty_completion | 15 | 9 glm5_2_nv integrate + 6 dsv4p_nv pexec, NVCF content-filter, code-level 不可配置 |
| all_tiers_exhausted | 2 | dsv4p_nv ATE: k3 504→k4 timeout→FASTBREAK=1 kills tier |

### dsv4p_nv ATE 根因 (docker logs)
```
[14:05:39] NV-KEY k3 → NVCF pexec 74f02205...
[14:06:43] NV-CYCLE k3 → 504 (504_nv_gateway_timeout), cycling to k4
[14:06:43] NV-KEY k4 → NVCF pexec 74f02205...
[14:07:31] NV-TIMEOUT k4 NVCF pexec timeout: attempt=48158ms total=112041ms
[14:07:31] NV-PEXEC-FASTBREAK → fast-break (saved remaining keys)
[14:07:31] NV-TIER-FAIL all 5 keys failed, elapsed=112042ms
```

**病因**: k3 504 消耗 ~64s, 剩余 48s 给 k4。BUDGET=112, k4 在 48s 时触发 FASTBREAK=1, 但 UPSTREAM=66s, k4 实际需要 ~66s → BUDGET 见底强制放弃。k4 在 48158ms 时 timeout, budget 已耗尽导致 FASTBREAK 提前杀剩余 keys。

### ms_gw fallback
- 24/25 OK (96.0% SR), 1 error (dsv4p_nv ATE fallback: TimeoutError 199461ms, code-level streaming sync defect, 不可配置)

### 参数状态
| 参数 | 当前值 | 状态 |
|---|---|---|
| UPSTREAM_TIMEOUT | 66 | optimal |
| TIER_TIMEOUT_BUDGET_S | 205 | optimal |
| NVU_TIER_BUDGET_DSV4P_NV | 112→118 | **本次优化** |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | optimal |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | optimal |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | optimal |
| NVU_EMPTY_200_FASTBREAK | 2 | settling |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | settling |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | optimal |
| KEY_COOLDOWN_S | 25 | floor |
| TIER_COOLDOWN_S | 15 | stable |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | stable |
| NVU_MS_GW_FALLBACK_TIMEOUT | 195 | settling |

## 2. 优化决策

**NVU_TIER_BUDGET_DSV4P_NV 112→118 (+6s)**

- k3 504 gateway timeout 消耗 ~64s, 剩余 48s 给 k4 — UPSTREAM=66s, k4 pexec 需要更多时间
- 118s 给 k4 ~54s: 仍低于 UPSTREAM=66s, 但增量改善, 减少 budget-exhaustion 导致的 FASTBREAK 误杀
- FASTBREAK=1 下 k4 是最后机会, 需给足时间避免过早放弃
- **保守增量**: 6s 单参数, 后续轮次看数据决定是否继续调整
- BUDGET=118 << TIER_TIMEOUT_BUDGET_S=205 安全

## 3. 执行

1. HM1 compose: `NVU_TIER_BUDGET_DSV4P_NV: "112"` → `"118"`
2. `docker compose up -d nv_gw` (recreate)
3. 验证: `docker exec nv_gw env | grep BUDGET_DSV4P` → 118 ✓
4. 验证: `/health` → `{"status":"ok"}` ✓

## 4. 评判

- 更少报错: BUDGET 扩大给 k4 更多 pexec 时间, 减少 budget-exhaustion 误杀
- 更快请求: 成功路径无影响 (仅影响失败路径)
- 超低延迟: 成功请求 avg 18893ms 不变
- 稳定优先: 单参数增量, 保守 +6s

铁律: 只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
