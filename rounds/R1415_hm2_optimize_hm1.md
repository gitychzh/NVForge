# R1415: HM2→HM1 — NVU_TIER_BUDGET_DSV4P_NV 106→112 (+6s)

## 1. 数据诊断 (6h window, HM1 nv_gw)

### 整体统计
| mapped_model | total | ok | sr_pct | avg_ok_ms |
|---|---|---|---|---|
| glm5_2_nv | 16 | 13 | 81.3% | 9841 |
| dsv4p_nv | 4 | 2 | 50.0% | 17660 |

### 错误分析
| error_type | cnt | 分析 |
|---|---|---|
| zombie_empty_completion | 4 | glm5_2_nv NVCF content-filter, code-level 不可配置 |
| all_tiers_exhausted | 1 | dsv4p_nv ATE: k4 504→k5 timeout→FASTBREAK=1 kills tier |

### dsv4p_nv ATE 根因 (docker logs)
```
[09:44:20] NV-KEY k4 → NVCF pexec 74f02205...
[09:45:23] NV-CYCLE k4 → 504 (504_nv_gateway_timeout), cycling to k5
[09:45:23] NV-KEY k5 → NVCF pexec 74f02205...
[09:46:06] NV-TIMEOUT k5 NVCF pexec timeout: attempt=42856ms total=106044ms
[09:46:06] NV-PEXEC-FASTBREAK → fast-break (saved remaining keys)
[09:46:06] NV-TIER-FAIL all 5 keys failed, elapsed=106046ms
```

**病因**: k4 504 消耗 ~63s, 剩余 43s 给 k5。BUDGET=106, k5 在 43s 时触发 FASTBREAK=1, 但 UPSTREAM=66s, k5 实际需要 42.9s→BUDGET 见底强制放弃。k5 实际在 42856ms 时 timeout, 但 budget 已耗尽导致 FASTBREAK 提前杀。

**ms_gw fallback**: 1/2 成功 (6s), 1/2 TimeoutError 198814ms (code-level streaming sync defect, 不可配置)。

### 僵尸空响应 (zombie_empty_completion)
- glm5_2_nv: finish_reason=stop, content_chars=12-49 < 50, input_chars 157K-209K
- NVCF integrate 对大 context 返回 content-filter 空响应
- Gateway zombie detection + error-chunk 正确触发 openclaw fallback
- **不可配置** — NVCF 后端行为

### 参数状态
| 参数 | 当前值 | 状态 |
|---|---|---|
| UPSTREAM_TIMEOUT | 66 | optimal |
| TIER_TIMEOUT_BUDGET_S | 205 | optimal |
| NVU_TIER_BUDGET_DSV4P_NV | 106→112 | **本次优化** |
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

**NVU_TIER_BUDGET_DSV4P_NV 106→112 (+6s)**

- k4 504 gateway timeout 消耗 ~63s, 剩余 43s 给 k5 — 但 UPSTREAM=66s, k5 需要更多时间完成 pexec
- 112s 给 k5 ~49s: 仍低于 UPSTREAM=66s, 但增量改善, 减少 budget-exhaustion 导致的 FASTBREAK 误杀
- FASTBREAK=1 下 k5 是最后机会, 需给足时间避免过早放弃
- **保守增量**: 6s 单参数, 后续轮次看数据决定是否继续调整
- BUDGET=112 << TIER_TIMEOUT_BUDGET_S=205 安全

## 3. 执行

1. HM1 compose: `NVU_TIER_BUDGET_DSV4P_NV: "106"` → `"112"`
2. `docker compose up -d nv_gw` (recreate)
3. 验证: `docker exec nv_gw env | grep BUDGET_DSV4P` → 112 ✓
4. 验证: `/health` → `{"status":"ok"}` ✓

## 4. 评判

- 更少报错: BUDGET 扩大给 k5 更多 pexec 时间, 减少 budget-exhaustion 误杀
- 更快请求: 成功路径无影响 (仅影响失败路径)
- 超低延迟: 成功请求 avg 17660ms 不变
- 稳定优先: 单参数增量, 保守 +6s

铁律: 只改HM1不改HM2

## ⏳ 轮到HM1优化HM2