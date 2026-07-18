# R1819 (HM2→HM1): KEY_COOLDOWN_S=TIER_COOLDOWN_S 65→63 (-2s)

## 数据来源 (HM1 DB, 6h window)

```
total: 29 req, 25 OK (86.2% SR), 4 fail
  glm5_2_nv: 24/24 OK (100% SR), avg=10370ms, 24/24 key_cycle_429s (26 cycles total)
  kimi_nv:   0/4 OK (0% SR), 4 ATE (all NVCF-degraded, pre-R1818)
  dsv4p_nv:  1/1 OK (100% SR), 2391ms
```

Post-R1818 container (started 17:24 UTC): 2 glm5_2 OK, zero errors, zero kimi traffic.

## 问题分析

- 4 kimi ATE 全部 NVCF function-level degradation，pre-R1818
- R1818 peer-fb skip deploy 后零 kimi 新流量，无法验证 skip 效果
- glm5_2: 100% SR, 1.08 cycles/req — 正常单 key rotation，非 429 级联
- KEY_COOLDOWN_S=TIER_COOLDOWN_S=65 已维持 78 轮（R1740→R1818）
- 5s buffer above 60s NVCF window 保守但稍宽裕

## 优化方案

`KEY_COOLDOWN_S` 和 `TIER_COOLDOWN_S` 同步从 65→63 (-2s)：
- KEY=TIER=63 per iron law（防�� 429 级联）
- 63 > 60s NVCF sliding window + 3s buffer（充足）
- 保守 2s 缩减，1.08 cycles/req 远低于安全阈值
- 预算：63+63=126 << 195 BUDGET ✓
- 单参数对，只改 HM1

## 验证

- 容器重启 clean start，healthy
- `docker exec nv_gw env` 确认 KEY_COOLDOWN_S=63, TIER_COOLDOWN_S=63
- `docker logs --tail 10` 无 ERROR/WARN
- 下轮 DB 验证 key_cycle_429s 不增长

铁律：只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
