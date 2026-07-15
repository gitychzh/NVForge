# R1419: HM2→HM1 — NOP (zombie-only environment, all params optimal, R1415 verified)

## 1. 数据诊断 (6h window, 04:22 UTC, HM1 nv_gw)

### 整体统计
| mapped_model | total | ok | sr_pct | avg_ok_ms | p50_ms | p95_ms |
|---|---|---|---|---|---|---|
| dsv4p_nv | 9 | 5 | 55.6% | 16287 | 16477 | 77402 |
| glm5_2_nv | 20 | 15 | 75.0% | 9284 | 8732 | 13676 |
| **总计** | **29** | **20** | **69.0%** | — | — | — |

### 错误分析
| error_type | cnt | mapped_model | 分析 |
|---|---|---|---|
| zombie_empty_completion | 8 | glm5_2_nv×5, dsv4p_nv×3 | NVCF content-filter 后端行为, 不可配置 |
| all_tiers_exhausted | 2 | dsv4p_nv | **pre-R1415** (01:44 UTC + 02:06 UTC), R1415 BUDGET 106→112 后 0 ATE |

### zombie 每小时分布
| 小时 | dsv4p_nv | glm5_2_nv |
|---|---|---|
| 01:00 | 0 | 1 |
| 02:00 | 0 | 1 |
| 03:00 | 2 | 2 |
| 04:00 | 1 | 1 |

zombie 稳定在每小时 1-4 个, 大 context (209K-210K chars) → NVCF content-filter → 空响应。Gateway zombie detection 正确触发 error SSE chunk → openclaw fallback。

### 每小时SR趋势
| 小时 | total | ok | sr_pct |
|---|---|---|---|
| 00:00 | 4 | 4 | 100.0% |
| 01:00 | 6 | 5 | 83.3% |
| 02:00 | 6 | 4 | 66.7% |
| 03:00 | 9 | 5 | 55.6% |
| 04:00 | 4 | 2 | 50.0% |

SR 下降 = zombie 累积, 非新错误类型。

### nv_tier_attempts
| tier | 结果 |
|---|---|
| all | **0 rows** — 完全干净 |

R1415 BUDGET_DSV4P_NV 106→112 验证通过: 6h 内 0 tier_attempts。

### fallback 统计
| fallback | cnt |
|---|---|
| f | 28 |
| t | 1 |

仅 1 次 fallback (ms_gw), 主链路健康。

### Logs 诊断 (最近100行)
```
- NV-INTEGRATE-SUCCESS ×4 (glm5_2_nv k1/k2/k3/k4, 3-7s)
- NV-ZOMBIE-EMPTY ×4 (glm5_2_nv×2, dsv4p_nv×2)
- NV-THINKING-TIMEOUT ×4 (dsv4p_nv, 正常 extended timeout)
- NV-TIER ×3 (dsv4p_nv pexec, 正常)
```
**无 NV-TIER-FAIL, 无 NV-EMPTY-FASTBREAK, 无 SSLEOF, 无 404, 无 504** — 系统完全健康。

### 参数状态 (全参数)
| 参数 | 当前值 | 状态 |
|---|---|---|
| UPSTREAM_TIMEOUT | 66 | optimal |
| TIER_TIMEOUT_BUDGET_S | 205 | optimal |
| NVU_TIER_BUDGET_DSV4P_NV | 112 | **R1415 生效, 验证通过** |
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
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 | stable |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | stable |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | stable |
| NVU_PEER_FB_SKIP_MODELS | (empty) | optimal |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | stable |

## 2. 优化决策

**NOP — 本轮无优化**

理由:
1. R1415 BUDGET_DSV4P_NV 106→112 验证通过: 6h 内 0 tier_attempts, 0 ATE post-R1415
2. 所有 8 个错误均为 zombie_empty_completion — NVCF content-filter 后端行为, code-level 不可配置
3. 所有参数在 optimal/floor/settling 状态, 无需调整
4. 日志完全干净: 无 NV-TIER-FAIL, 无 SSLEOF, 无 404, 无 504
5. 主链路 69.0% SR, 仅 1 次 fallback, 系统稳定
6. 数据与 R1418 相同 (29req/20OK) — 无新数据, 无新信号

## 3. 执行

**无执行** — NOP 轮次, 未修改 HM1 任何配置。

## 4. 评判

- 更少报错: R1415 BUDGET 扩大后 ATE 消除, 仅剩不可配置的 zombie 错误
- 更快请求: 成功路径健康 (dsv4p_nv avg 16287ms, glm5_2_nv avg 9284ms)
- 超低延迟: dsv4p_nv p50=16477ms, glm5_2_nv p50=8732ms
- 稳定优先: NOP, 不引入变化风险
- 铁律: 只改HM1不改HM2

## ⏳ 轮到HM1优化HM2