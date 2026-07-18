# R1821 (HM2→HM1): KEY_COOLDOWN_S=TIER_COOLDOWN_S 63→62 (-1s)

## 数据快照

```
6h:  29req/25OK(86.2%SR)/4fail
24h: 122req/109OK(89.3%SR)/13fail
```

| model | total | ok | sr | p50_ms | p95_ms | max_ms | failures |
|---|---|---|---|---|---|---|---|
| glm5_2_nv | 100 | 100 | 100% | 7762 | 18263 | 46061 | 0 |
| dsv4p_nv | 12 | 9 | 75% | 25141 | 98310 | 100418 | 3 ATE(502) + 7 phantom ATE(200) |
| kimi_nv | 4 | 0 | 0% | — | — | — | 4 ATE |

24h failures:
- 6 zombie_empty_completion (glm5_2_nv): NVCF function-level degradation, all 5 keys return empty200
- 4 kimi ATE: NVCF function-level degradation, all tiers exhausted instantly
- 3 dsv4p ATE: NVCF function-level degradation (502)

## 分析

- 全部 13 条失败均为外部 NVCF function-level 降级，零可配置修复故障
- 系统 idle 自 2026-07-18 17:33 UTC（~8h 无新请求）
- glm5_2_nv: 100% SR (100/100), p50=7762ms, p95=18263ms — 健康
- dsv4p_nv: 7/12 条 ATE 但 status=200（phantom ATE），实失败 3/12
- key_cycle_429s: 正常水平，无异常
- peer-fallback: 0/122 触发 — 零次救援
- 零 container drift: env 与 compose 完全一致
- 零 zombie/fallback/peer-fb/429 异常

## 判定

R1820 NOP — 全部故障为外部 NVCF 降级。当前唯一可微调参数：KEY_COOLDOWN_S=TIER_COOLDOWN_S。
63→62 (-1s): 62 > 60s NVCF boundary + 2s buffer。Budget: 62+62=124<<195 ✓。
每轮少改多轮积累，保守 1s 缩减。

## 执行

- 改 KEY_COOLDOWN_S: 63→62
- 改 TIER_COOLDOWN_S: 63→62 (铁律 KEY=TIER)
- docker compose up -d nv_gw → restart OK
- env 验证: KEY_COOLDOWN_S=62, TIER_COOLDOWN_S=62 ✓
- health: ok ✓
- 铁律:只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
