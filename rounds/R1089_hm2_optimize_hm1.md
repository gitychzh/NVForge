# HM2 Optimize HM1 — Round R1089

## 触发
R1088 提交了新 commit (TIER_TIMEOUT_BUDGET_S 132→198) → cron 检测到 HM1 提交 → 轮到 HM2 优化 HM1。

## 数据收集 (改前必有数据)

### nv_gw 容器状态
- 重启时间: 2026-07-10 20:09 CST (R1088 重启)
- 容器: nv_gw, Up 7 minutes (healthy)
- 有效窗口: 重启后 ~7m (零请求)

### 最近 10 条请求 (全部 pre-restart)
| ts | request_model | mapped_model | status | ttfb_ms | duration_ms | upstream_type |
|----|---------------|-------------|--------|---------|-------------|---------------|
| 12:03 UTC | glm5_2_nv | glm5_2_nv | 200 | 5,381 | 5,381 | nv_integrate |
| 11:33 UTC | glm5_2_nv | glm5_2_nv | 200 | 3,608 | 3,608 | nv_integrate |
| 11:03 UTC | glm5_2_nv | glm5_2_nv | 200 | 4,464 | 4,464 | nv_integrate |
| 10:33 UTC | glm5_2_nv | glm5_2_nv | 200 | 5,682 | 5,683 | nv_integrate |
| 10:30 UTC | glm5_2_nv | glm5_2_nv | 200 | 3,853 | 3,853 | nv_integrate |
| 10:28 UTC | glm5_2_nv | glm5_2_nv | 200 | 3,280 | 3,280 | nv_integrate |
| 10:03 UTC | glm5_2_nv | glm5_2_nv | 200 | 4,152 | 4,153 | nv_integrate |
| 09:34 UTC | glm5_2_nv | glm5_2_nv | 200 | 18,103 | 19,154 | nv_integrate |
| 09:34 UTC | glm5_2_nv | glm5_2_nv | 200 | 30,135 | 30,135 | nv_integrate |
| 09:33 UTC | glm5_2_nv | glm5_2_nv | 200 | 45,689 | 45,690 | nv_integrate |

### 6h 窗口 (含重启前数据)
| 指标 | 值 |
|------|-----|
| 总请求 | 30 |
| 成功 | 27 (90.0% SR) |
| 失败 | 3 |
| avg TTFB | 20,327ms |
| avg duration | 27,315ms |
| max duration | 132,017ms |

### 6h 按路径分解
| upstream_type | cnt | ok | avg_ttfb | avg_dur | max_dur |
|---------------|-----|-----|----------|---------|---------|
| nv_integrate | 28 | 27 | 21,237ms | 25,830ms | 96,068ms |
| (ATE) | 2 | 0 | 1,060ms | 66,673ms | 132,017ms |

### 6h 错误分类
| error_type | cnt |
|------------|-----|
| all_tiers_exhausted | 2 |
| NVStream_TimeoutError | 1 |

### 24h 总体统计
| 指标 | 值 |
|------|-----|
| 总请求 | 630 |
| 成功 | 584 (92.7% SR) |
| 失败 | 46 |
| avg TTFB | 16,592ms |
| avg duration | 24,833ms |
| max duration | 208,108ms |

### 24h 按路径分解
| upstream_type | cnt | ok | avg_ttfb | avg_dur | max_dur |
|---------------|-----|-----|----------|---------|---------|
| nv_integrate | 424 | 414 | 16,026ms | 19,550ms | 129,132ms |
| nvcf_pexec | 158 | 158 | 20,044ms | 20,052ms | 139,999ms |
| (ATE) | 48 | 12 | 354ms | 87,231ms | 208,108ms |

### 24h 错误分类
| error_type | cnt |
|------------|-----|
| all_tiers_exhausted | 36 |
| NVStream_TimeoutError | 7 |
| stream_total_deadline | 3 |

### 24h tier_attempts
| tier | error_type | cnt | avg_ms | max_ms |
|------|-----------|-----|--------|--------|
| dsv4p_nv | IntegrateTimeout | 14 | 56,021 | 67,086 |
| dsv4p_nv | NVCFPexecRemoteDisconnected | 1 | 9,134 | 9,134 |
| glm5_2_nv | IntegrateRemoteDisconnected | 1 | 20,284 | 20,284 |
| glm5_2_nv | IntegrateTimeout | 1 | 90,566 | 90,566 |
| kimi_nv | empty_200 | 1 | — | — |
| minimax_m3_nv | IntegrateTimeout | 1 | 90,762 | 90,762 |

### ms_gw 日志 (HM1)
- glm5_2_ms: MS-OK-STREAM / MS-STREAM-DONE 正常
- dsv4p_ms: MS-OK-STREAM 正常, 但 MS-STREAM-CLIENT-EOF BrokenPipeError 仍然发生 (nv_gw BUDGET 到期前 relay 未完成)

### 关键 env vars (容器当前)
| 参数 | 值 |
|------|-----|
| TIER_TIMEOUT_BUDGET_S | 198 (R1088) |
| NVU_TIER_BUDGET_DSV4P_NV | 66 |
| UPSTREAM_TIMEOUT | 66 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 180 |
| NVU_EMPTY_200_FASTBREAK | 2 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.10 |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 |
| NVU_STREAM_TOTAL_DEADLINE_S | 90 |

## 诊断

### NOP 判定
R1088 的 `TIER_TIMEOUT_BUDGET_S 132→198` 变更于 20:09 CST 重启容器，**仅 7 分钟前**。重启后零请求，所有 6h 数据均为 pre-restart 旧数据。

"改前必有数据" 铁律：无法对 R1088 变更的效果做出任何判断。BUDGET=198 是否让 ms_gw dsv4p_ms 完成 relay？是否有资源压力？一概不知。需要至少数小时运行数据才能评估。

### 当前状态评估
- nvcf_pexec: 100% SR (158/158) — pexec 路径干净，无需修改
- nv_integrate: 97.6% SR (414/424) — 良好的集成路径
- ATE: 25% SR (12/48) — 这是 R1088 主要目标，但数据全为旧 BUDGET=132 下的行为
- dsv4p_nv IntegrateTimeout: 14 次，avg 56s — 在 UPSTREAM=66 范围内正常

## 决策

**NOP** — 不执行任何优化。

1. R1088 的 BUDGET=198 变更尚无数据支撑评估
2. 所有现有指标均为 pre-restart 旧数据，不代表新配置效果
3. 铁律要求 "改前必有数据" — 当前无有效数据
4. 下一轮 cron 将新数据，届时可进行评估

## 评判
- 更少报错: 等待 R1088 数据后再判断
- 更快请求: 不改变任何路径
- 超低延迟: NOP 无影响
- 稳定优先: 避免在无数据情况下盲目变更

**铁律: 只改 HM1 不改 HM2** ✓ (NOP)

## ⏳ 轮到HM1优化HM2