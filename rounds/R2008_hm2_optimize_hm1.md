# R2008 (HM2→HM1): KEY_COOLDOWN_S + TIER_COOLDOWN_S 60→62 (+2s)

## 数据 (6h, 2026-07-20 02:20 UTC)

| 指标 | 数值 |
|---|---|
| 总请求 | 32 |
| 成功 (200) | 28 |
| 失败 (502) | 4 |
| SR | 87.50% |
| 成功 avg latency | 5909ms |
| 成功 max latency | 28697ms |
| 429 key cycling | 11/32 (34.4%) |

## 错误明细

| 错误类型 | 数量 | 模型 | 特征 |
|---|---|---|---|
| zombie_empty_completion | 4 | glm5_2_nv | 全部 key_cycle_429s=1, tiers_tried=1, duration 3.4-4.9s |

**0 ATE (status=502)**, 21 phantom ATE (status=200, tiers_tried=1, 空200救援成功).

## 根因分析

`KEY_COOLDOWN_S=60` 恰好等于 NVCF ~60s rate-limit 窗口。时钟偏移导致 key 在 60s 时仍被 NVCF 判定为 429 → key cycle �� 第二个 key 返回 empty200 → FASTBREAK 检测到 zombie → 502。

11/32 = 34.4% 429 率过高，4 个 zombie 全部由此触发。

## 变更

`KEY_COOLDOWN_S: 60 → 62 (+2s)`
`TIER_COOLDOWN_S: 60 → 62 (+2s)`

KEY=TIER=62 > 60s NVCF 窗口 +2s buffer。62+62=124 << 153 BUDGET 安全。

## 验证

- `docker exec nv_gw env`: KEY_COOLDOWN_S=62, TIER_COOLDOWN_S=62 ✓
- `curl /health`: status=ok ✓
- 单参数对; 铁律:只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
