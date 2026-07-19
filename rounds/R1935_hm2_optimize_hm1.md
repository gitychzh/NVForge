# R1935 (HM2→HM1): NOP — false trigger, R1934 self-commit, 0 new data, 0 config-fixable

## 触发
False trigger — HM2 自提交 `e4bc8eb` (R1934)，脚本输出"这是我提交的, 不触发"但 cron 仍派遣。数据与 R1934 完全一致 (同 6h window)，零新数据。

## 6h 数据 (≈12:00-22:00 UTC, 实际与 R1934 相同窗口)
| 指标 | 值 |
|------|-----|
| 总请求 | 41 |
| 成功 | 29 (70.7% SR) |
| 失败 | 12 |
| fallback_occurred | 0 |
| peer-fb | 0 |
| 429 cascade | 0 |
| SSLEOF | 0 |

**Per-model OK:**
| Model | Total | OK | Fail | SR | avg_ms | min_ms | max_ms |
|-------|-------|-----|------|-----|--------|--------|--------|
| glm5_2_nv | 35 | 25 | 10 | 71.4% | 8,870 | 2,333 | 27,809 |
| dsv4p_nv | 6 | 4 | 2 | 66.7% | 16,485 | 1,963 | 43,081 |

**Clean OK (no error_type):**
| Model | Count | avg_ms | max_ms |
|-------|-------|--------|--------|
| glm5_2_nv | 17 | 12,101 | 27,809 |

**Error breakdown:**
| Error | Count | Model | Details |
|-------|-------|-------|---------|
| zombie_empty_completion | 10 | glm5_2_nv | NVCF upstream content-filter, all big_input (128K-142K chars > 115K threshold) |
| all_tiers_exhausted (status=502) | 2 | dsv4p_nv | 2-3ms fast-fail phantom ATE |
| all_tiers_exhausted (status=200) | 14 | mixed | phantom ATE — empty_200 rescue succeeded |

## 环境快照 (container env, zero drift)
```
TIER_TIMEOUT_BUDGET_S=153
UPSTREAM_TIMEOUT=30
NVU_TIER_BUDGET_GLM5_2_NV=30
NVU_TIER_BUDGET_DSV4P_NV=25
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
KEY_COOLDOWN_S=60
TIER_COOLDOWN_S=60
MIN_OUTBOUND_INTERVAL_S=0
NVU_BIG_INPUT_THRESHOLD=115000
NVU_BIG_INPUT_FAIL_N=1
NVU_BIG_INPUT_COOLDOWN_S=21600
NVU_BIG_INPUT_MODELS=glm5_2_nv,dsv4p_nv
NVU_EMPTY_200_FASTBREAK=1
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=122
```

## 决策：NOP — 0 改
- False trigger: HM2 自提交 R1934，零新数据，零新流量
- 全部 10 zombie 为 NVCF 上游内容过滤 (BIG_INPUT breaker 已最大攻击性: FAIL_N=1, COOLDOWN=6h)
- 2 real ATE 为 fast-fail (2-3ms)，非超时类，非 config 可修
- 14 phantom ATE (status=200) 已被 empty_200 rescue 成功处理
- glm5_2 OK max=27,809ms < BUDGET=30 (2.2s margin) — safe
- UPSTREAM=30 + PEER=122 = 152 < BUDGET=153 (1s margin) — tight but holding
- 铁律「改前必有数据」→ 无数据支持任何参数变更
- 铁律：只改 HM1 不改 HM2
## ⏳ 轮到HM1优化HM2
