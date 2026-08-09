# R1227: dsv4f0731_nv40666 self-opt NOP

**日期**: 2026-08-09 13:16 (采集窗口结束)

**结论**: NOP — 数据正常，无容器杠杆。

## 数据 (30min 窗口)

| 指标 | 值 |
|---|---|
| 总量 / 成功 / 失败 | 49 / 47 / 2 |
| SR | **95.9%** |
| Avg / P50 / P95 / Max | 47279 / 26758 / 135774 / 170378 ms |
| 净 429 | 0 |
| fallback (hm4104) | 0 |
| upstream_type | nvcf_pexec 49/47 (100%) |

### 错误分类
| error_type | n | avg_ms | key |
|---|---|---|---|
| all_tiers_exhausted | 1 | 180027 | 0 |
| stream_absolute_cap | 1 | 159925 | 4 |

### per-key 200 延迟
| key | n | avg | p95 |
|---|---|---|---|
| 0 | 7 | 43406 | 130248 |
| 1 | 10 | 45715 | 102579 |
| 2 | 10 | 45610 | 89154 |
| 3 | 8 | 47245 | 117552 |
| 4 | 12 | 31806 | 62208 |

### 趋势
- 6h: 622 / 588 / 34 / 0 → SR=94.5%
- 3h 逐小时: 05:00 21/20, 04:00 115/110, 03:00 74/63(SR85%), 02:00 81/79
- 24h all_tiers_exhausted: 117 (持续背景水平)

## 分析

两个错误均为 NVCF 侧瞬态：
1. **all_tiers_exhausted (key0, 180027ms)** — 单请求烧满 180s 全 tier budget，5 key 全被消耗。属 tier-level NVCF 过载，非参数杠杆。
2. **stream_absolute_cap (key4, 159925ms)** — NVCF 流绝对上限，单次瞬态。

净值：净 429=0，无 fallback，无 per-key 持续劣化（key4 延迟最低 avg=31.8s / p95=62.2s）。key1 key_cycle_429s=37 但经 key 循环自恢复，未造成请求失败。

24h ATE=117 与 R1221-R1226 背景水平（108-118）一致，属 NVCF 侧持续背景，非本容器可调杠杆。

## 未修改参数
所有参数保持 R1226 之后状态（无变更）。

## 下一步建议
- 持续观察 all_tiers_exhausted → 若单窗口 >3 次或 24h ATE 显著上升（>150），考虑 NVU_TIER_BUDGET_DSV4F0731_NV 或 TIER_COOLDOWN_S 微调。
- 关注 key1 持续高 key_cycle_429s（37）是否在后续窗口累积为实际失败。