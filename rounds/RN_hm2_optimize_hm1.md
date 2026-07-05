# RN_hm2_optimize_hm1.md — HM2→HM1 优化回合记录

## R756: HM2→HM1 — NOP — 96% SR健康regime，NVCFPexecTimeout非绑定，零参数变更

### 变更
**无参数变更** — NOP（零运维轮）。系统处于自维持健康regime，无任何配置参数需要调整。

### 6h 数据
- **总体**: 376req/341OK (**90.7%**) / 35 ATE (9.3%)
- **Hourly SR 趋势**: 74%→94%→97.6%→97.6%→97.1%→100%→100%→100%→100%→100%→100%
  - 自 21:00 UTC 进入 **96-100% SR regime**，最后7小时 0 ATE
- **dsv4p_nv**: OK 直接成功 (non-fallback)，少量 empty_200 + NVCFPexecTimeout → glm5_2 fallback 救回
- **glm5_2_nv**: 极低延迟 (2-3s)，100% SR
- **Fallback 双向健康**: ds4p_nv→glm5_2_nv (22救回), glm5_2_nv→ds4p_nv (61救回)

### ATE 分析
| tiers_tried_count | cnt | avg_dur | 原因 |
|---|---|---|---|
| 1 | 14 | 78.6s | 13 dsv4p_nv single-tier exhaustion (avg 84.5s)，1 start_idx=0 outlier (2.6s) |
| 2 | 21 | 159.2s | NVCF 双函数耗尽，非配置可修复 |

- 所有 ATE 均非配置级问题可解决
- HEALTH_THRESHOLD=0.10 正常工作，FALLBACK_GRAPH 双向活跃
- tier_chain: dsv4p_nv=['dsv4p_nv','glm5_2_nv'] (dynamic fallback, health={74f02205:0.95-1.0, 3b9748d8:1.0})
- tier_chain: glm5_2_nv=['glm5_2_nv','dsv4p_nv'] (dynamic fallback, health={74f02205:0.95-1.0, 3b9748d8:1.0})

### NVCFPexecTimeout 绑定诊断
| tier | key | max_ms | UPSTREAM=66 buffer | 判定 |
|---|---|---|---|---|
| dsv4p_nv | k0 | 60,823ms | **5.2s** >3s | ✅ 非绑定 |
| glm5_2_nv | k1 | 62,389ms | **3.6s** >3s | ✅ 非绑定 |

- BUDGET=114 >> 66 per-tier safe
- UPSTREAM=66 ↔ NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66 synced — 零漂移

### 上游非配置问题（零变更依据）
| 问题 | count | 类型 | 可修复性 |
|---|---|---|---|
| empty_200 | dsv4p 41 + glm5_2 35 = 76 | NVCF upstream systemic | ❌ 非配置 |
| 504_nv_gateway_timeout | glm5_2 19 | NVCF gateway issue | ❌ 非配置 |
| NVCFPexecTimeout | dsv4p 21 + glm5_2 47 = 68 | 函数级均匀分布 | ❌ 非配置 |
| 429_nv_rate_limit | dsv4p 5 | NVCF rate limit | ❌ 非配置 |

### 当前配置快照
| 参数 | 值 | 状态 |
|---|---|---|
| UPSTREAM_TIMEOUT | 66 | 缓冲 ≥3.6s，非绑定 ✅ |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | 同步 UPSTREAM，零漂移 ✅ |
| TIER_TIMEOUT_BUDGET_S | 114 | >>66 per-tier safe ✅ |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | 省 60s/ATE ✅ |
| NVU_EMPTY_200_FASTBREAK | 3 | 3 连发 empty 才 fastbreak ✅ |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | 仅排除真死函数 ✅ |
| NVU_FORCE_STREAM_UPGRADE | 0 | thinking 仅 glm5_2 ✅ |

### 安全分析
- BUDGET=114 >> UPSTREAM=66, 48s headroom safe
- FASTBREAK=1: 1×66=66s << 114s, key2 + fallback 空间充足
- 零变更无风险

### 铁律
单参数每轮（NOP 轮例外）。铁律：只改 HM1 不改 HM2。

## ⏳ 轮到HM1优化HM2