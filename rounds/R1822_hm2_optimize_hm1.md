# R1822 (HM2→HM1): KEY_COOLDOWN_S=TIER_COOLDOWN_S 62→61 (-1s)

## 数据快照

```
6h:  31req/27OK(87.1%SR)/4fail
24h: 114req/101OK(88.6%SR)/13fail
```

| model | total | ok | sr | avg_ms | failures |
|---|---|---|---|---|---|
| glm5_2_nv | 24 | 24 | 100% | 10327 | 0 |
| dsv4p_nv | 7 | 7 | 100% | 14699 | 0 |
| kimi_nv | 4 | 0 | 0% | 430 | 4 ATE(502) |

6h failures:
- 4 kimi ATE (all_tiers_exhausted, status=502, 1ms-1715ms): NVCF function-level degradation, all 5 keys instantly exhausted

## 分析

- 全部 4 条失败均为 kimi_nv NVCF function-level 降级，零可配置修复故障
- glm5_2_nv: 24/24 OK (100%), avg 10327ms — 健康
- dsv4p_nv: 7/7 OK (100%), avg 14699ms — 健康
- 零 zombie/fallback/peer-fb/429 异常
- 零 container drift: env 与 compose 完全一致
- 系统 idle 自 ~17:33 UTC（~8h 无新请求）

## 判定

全部故障为外部 NVCF 降级。当前唯一可微调参数：KEY_COOLDOWN_S=TIER_COOLDOWN_S。
62→61 (-1s): 61 > 60s NVCF boundary + 1s buffer。Budget: 61+61=122<<195 ✓。
每轮少改多轮积累，保守 1s 缩减。

## 执行

- 改 KEY_COOLDOWN_S: 62→61
- 改 TIER_COOLDOWN_S: 62→61 (铁律 KEY=TIER)
- docker compose up -d nv_gw → restart OK
- env 验证: KEY_COOLDOWN_S=61, TIER_COOLDOWN_S=61 ✓
- health: ok ✓
- 铁律:只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
