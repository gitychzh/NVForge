# R1934 (HM2→HM1): NOP — false trigger, all zombie NVCF content-filter, 0 config-fixable

## 触发
False trigger — HM2 自提交 `7d5e698` (R1933 cc2)，脚本输出"这是我提交的, 不触发"但 cron 仍派遣。R1933 刚部署 8min 前；stale symlink R1905→R1933 已修复。

## 6h 数据
| 指标 | 值 |
|------|-----|
| 总请求 | 41 |
| 成功 | 29 (70.7% SR) |
| 失败 | 12 |
| 30min | 3/3 OK (100%) |
| fallback_occurred | 0 |

**Per-model:**
| Model | Total | OK | Fail | SR | avg_ms | max_ok_ms |
|-------|-------|-----|------|-----|--------|-----------|
| glm5_2_nv | 35 | 25 | 10 | 71.4% | 8971 | 27809 |
| dsv4p_nv | 6 | 4 | 2 | 66.7% | 10991 | 43081 |

**Error breakdown:**
| Error | Count | Model | Notes |
|-------|-------|-------|-------|
| zombie_empty_completion | 10 | glm5_2_nv | NVCF upstream content-filter, all big_input |
| all_tiers_exhausted (status=502) | 2 | dsv4p_nv | 2-3ms fast-fail phantom ATE |

**ATE detail:** 16 rows with error_type=all_tiers_exhausted, but 14 are status=200 phantom ATE (peer-fb rescued). Only 2 are real failures (status=502, 2-3ms).

## 环境快照
- `TIER_TIMEOUT_BUDGET_S=153`
- `UPSTREAM_TIMEOUT=30`
- `NVU_TIER_BUDGET_GLM5_2_NV=30`
- `NVU_TIER_BUDGET_DSV4P_NV=25`
- `NVU_BIG_INPUT_FAIL_N=1`, `NVU_BIG_INPUT_COOLDOWN_S=21600`, `NVU_BIG_INPUT_MODELS=glm5_2_nv,dsv4p_nv`
- `NVU_PEER_FALLBACK_ENABLED=1`, `NVU_PEER_FALLBACK_TIMEOUT=122`
- All env stable, zero drift from R1931.

## 决策：NOP — 0 改
- 全部 10 条 zombie 为 NVCF 上游内容过滤 (all big_input>115K)，BIG_INPUT breaker 已以最大攻击性 (FAIL_N=1, COOLDOWN=6h) 工作
- 2 条 real ATE 为 fast-fail (2-3ms)，非超时类，非 config 可修
- glm5_2 OK max=27809ms < BUDGET=30 (2.2s margin) — 安全
- BUDGET_GLM5_2=30 已 tight；28 仅留 191ms margin 不安全
- 0 fallback 触发，0 SSLEOF，0 429
- 铁律「改前必有数据」→ 无数据支持任何参数变更
- 铁律：只改 HM1 不改 HM2
## ⏳ 轮到HM1优化HM2
