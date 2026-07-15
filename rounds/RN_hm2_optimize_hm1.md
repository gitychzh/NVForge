# R1416: HM2→HM1 — NOP (false trigger, double-dispatch, 574th chain of R1133)

## 1. 数据诊断 (6h window, HM1 nv_gw, post-R1415)

### 整体统计
| mapped_model | total | ok | sr_pct | avg_ok_ms |
|---|---|---|---|---|
| dsv4p_nv | 7 | 4 | 57.1% | 16287 |
| glm5_2_nv | 18 | 14 | 77.8% | 9841 |
| **总计** | **25** | **18** | **72.0%** | — |

### 错误分析
| error_type | cnt | mapped_model | 分析 |
|---|---|---|---|
| zombie_empty_completion | 6 | glm5_2_nv×4, dsv4p_nv×2 | NVCF content-filter 后端行为, 不可配置 |
| all_tiers_exhausted | 1 | dsv4p_nv | **pre-R1415** (02:11 UTC), R1415 BUDGET 106→112 后未再出现 |

### 错误详情 (created_at)
| 时间 | 模型 | 错误 | 耗时ms |
|---|---|---|---|
| 01:03 UTC | glm5_2_nv | zombie_empty_completion | 10382 |
| 02:03 UTC | glm5_2_nv | zombie_empty_completion | 4866 |
| 02:11 UTC | dsv4p_nv | **all_tiers_exhausted (pre-R1415)** | 106052 |
| 03:03 UTC | glm5_2_nv | zombie_empty_completion | 8396 |
| 03:07 UTC | dsv4p_nv | zombie_empty_completion | 34426 |
| 03:33 UTC | glm5_2_nv | zombie_empty_completion | 9980 |
| 03:36 UTC | dsv4p_nv | zombie_empty_completion | 12822 |

### nv_tier_attempts
| tier | error_type | cnt |
|---|---|---|
| dsv4p_nv | (none) | 0 rows |

**关键发现**: R1415 BUDGET_DSV4P_NV 106→112 后, 6h 内 0 tier_attempts。之前的 ATE 已消除。

### 僵尸空响应 (zombie_empty_completion)
- 本质: NVCF integrate 大 context (209K-210K 输入字符) → 返回 content-filter 空响应 (finish_reason=stop, content_chars=8-12 < 50)
- Gateway zombie detection properly triggers error SSE chunk → openclaw fallback
- **不可配置** — NVCF 后端内容过滤行为

### fallback 统计
| fallback_occurred | cnt |
|---|---|
| f | 24 |
| t | 1 |

仅 1 次 fallback (ms_gw), 主链路健康。

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

## 2. 优化决策

**NOP — 本轮无优化**

理由:
1. R1415 BUDGET_DSV4P_NV 106→112 生效: 6h 内 0 tier_attempts, 0 ATE
2. 所有 6 个错误均为 zombie_empty_completion — NVCF content-filter 后端行为, code-level 不可配置
3. 所有参数在 optimal/floor/settling 状态, 无需调整
4. 主链路 72.0% SR, 仅 1 次 fallback, 系统稳定
5. 日志仅 7 行 NV-ZOMBIE/NV-THINKING (正常)

**触发分析**: 这是一个 false trigger (double-dispatch)。HM1 提交 R1415 的 commit 被脚本检测到, 但该 commit 是 HM1 自己写的 NOP 交接, 不需要 HM2 实际修改。574th chain of R1133 的延续。

## 3. 执行

**无执行** — NOP 轮次, 未修改 HM1 任何配置。

## 4. 评判

- 更少报错: R1415 BUDGET 扩大后 ATE 消除, 仅剩不可配置的 zombie 错误
- 更快请求: 成功路径不变 (dsv4p_nv avg 16287ms, glm5_2_nv avg 9841ms)
- 超低延迟: 状态稳定
- 稳定优先: NOP, 不引入变化风险

铁律: 只改HM1不改HM2

## ⏳ 轮到HM1优化HM2