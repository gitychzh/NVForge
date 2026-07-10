# HM2 Optimize HM1 — Round R1091 (NOP)

**日期**: 2026-07-10 20:35 UTC
**触发器**: cron 派遣 (false trigger — 脚本输出: "这是我提交的, 不触发")
**操作者**: HM2 (opc2_uname)

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit: `72976de R1090: HM2→HM1 — NOP` (author=opc2_uname, HM2)
- 脚本正确检测到自提交并标记 "不触发", cron 仍被派遣 — 误触发
- HM1 本地 git log 停留在 R821，269 轮落后

## 2. HM1 容器状态

- **nv_gw 重启时间**: 2026-07-10 12:09:57 UTC (R1088 重启)
- **重启后请求数**: 1 (glm5_2_nv integrate, 200 OK, 33.8s, k1 first attempt)
- **R1088 BUDGET=198 待验证**: dsv4p_nv 重启后零请求，BUDGET 198 尚未被 exercising

## 3. DB 数据 (6h)

| 指标 | 值 |
|------|-----|
| 总请求 | 30 |
| 成功 | 27 (90.0%) |
| 失败 | 3 |
| glm5_2_nv | 28req/27OK/1err → 96.4% SR |
| dsv4p_nv | 2req/0OK/2err → 0.0% SR (pre-R1088, BUDGET=132 killed) |

### 错误分类
| 错误类型 | 次数 |
|---------|------|
| all_tiers_exhausted | 2 (dsv4p_nv, pre-restart) |
| NVStream_TimeoutError | 1 (glm5_2_nv) |

### 按 upstream 路径
| upstream_type | cnt | ok | avg_dur | max_dur |
|---------------|-----|-----|---------|---------|
| nv_integrate | 27 | 26 | 21,682ms | 96,068ms |
| (NULL=ATE) | 2 | 0 | 66,673ms | 132,017ms |
| nvcf_pexec | 1 | 1 | 125,917ms | 125,917ms |

### ATE 详情
- tiers_tried_count=1: 3 ATE, avg 76,471ms
- fallback_occurred=0 for all 30 requests (all single-tier, no fallback triggered)
- 2 dsv4p_nv ATE: duration 132,017ms ≈ BUDGET=132 (pre-R1088, BUDGET killed at 132s)
- 1 glm5_2_nv NVStream_TimeoutError: 96,068ms

### tier_attempts
- glm5_2_nv IntegrateTimeout: 1 (90,566ms)

## 4. 当前配置 (HM1 nv_gw env)

| 参数 | 值 | 状态 |
|------|-----|------|
| TIER_TIMEOUT_BUDGET_S | 198 | R1088 刚改, 待验证 |
| UPSTREAM_TIMEOUT | 66 | 稳定 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | 稳定 |
| NVU_EMPTY_200_FASTBREAK | 2 | 稳定 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | 稳定 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 180 | 稳定 |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | 稳定 |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | 稳定 |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | 稳定 |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.10 | 稳定 |
| KEY_COOLDOWN_S | 25 | 稳定 |
| TIER_COOLDOWN_S | 18 | 稳定 |
| MIN_OUTBOUND_INTERVAL_S | 0 | 稳定 |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | 稳定 |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | 稳定 |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms | 稳定 |

## 5. 决策: NOP (零参数变更)

- **False trigger**: HM1 未提交新内容，cron 误派遣
- **R1088 待验证**: BUDGET 198 重启后仅 1 个 glm5_2_nv 请求，dsv4p_nv 零请求
- **所有参数地板/最优**: 无优化空间
- **铁律遵守**: 只改 HM1, 不改 HM2 ✓

## ⏳ 轮到HM1优化HM2
