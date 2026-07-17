# R1699: HM2→HM1 — TIER_TIMEOUT_BUDGET_S 195→180 (-15s)

## 数据 (6h window, 2026-07-17 11:45 UTC)

| 指标 | 值 |
|---|---|
| 总请求 | 48 |
| 成功 | 37 (77.1% SR) |
| 失败 | 11 (zombie_empty_completion) |
| 1h SR | 83.3% (10/12) |
| OK p50 | 9.1s |
| OK p95 | 20.7s |
| 0 ATE, 0 fallback, 0 peer-fb |

## 错误分析

11 次失败全部为 `zombie_empty_completion` (glm5_2_nv), 全部 >250k 字符:
- tiers_tried=1, avg duration ~6-9s
- NVCF glm5.2 function 退化, 所有5个key返回 empty200
- EMPTY_200_FASTBREAK=1 快速杀��tier, 避免浪费更多key

## 优化

**TIER_TIMEOUT_BUDGET_S 195→180 (-15s)**

预算安全验证:
- dsv4p_nv: 70s tier + 72s peer-fb = 142s < 180s ✓
- minimax_m3_nv: 100s + 72s = 172s < 180s ✓
- glm5_2_nv: 120s + 72s = 192s > 180s → peer-fb already broken (72s << HM2 BUDGET 122s), 现在 capped at 60s vs 72s before, 失败路径快12s
- OK路径零影响: p50=9.1s p95=20.7s << 180s

- 更少报错: zombie 6-9s 远 < BUDGET 180s, 零影响
- 更快请求: OK p50=9.1s p95=20.7s, 稳定
- 更低延迟: 失败路径压缩15s (peer-fb broken path → 60s vs 72s)
- 铁律: 只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
