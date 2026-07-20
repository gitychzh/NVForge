# R2118: HM2优化HM1 — KEY_COOLDOWN_S 75→73 (-2s)

## 数据 (HM1, 6h window, CST ~22:00→04:50)

```
n=43 req | 24 OK | 19 fail | SR=55.8%
  10 glm5_2_nv zombie_empty_completion (NVCF function-level, ~30min cadence)
   9 dsv4p_nv ATE all_tiers_exhausted (tiers_tried=1, glm5_2 fallback skipped)
   0 429 cycles, 0 SSL errors

glm5_2_nv per-key: 6h total=24, 20 pexec_success, 5 pexec_timeout, 2 pexec_SSLEOFError
dsv4p_nv per-key: 6h total=19, 10 pexec_success (all 5 keys working), 9 ATE (NULL nv_key_idx)
  → All 9 ATE have tiers_tried=1 (only dsv4p_nv), glm5_2 fallback NOT attempted
  → R2112 glm5_2 budget 25>24 should enable fallback but no new ATE since R2112 deploy

KEY+TIER=75+64=139 << 153 BUDGET (14s margin)
```

## 分析

Storm完全自愈(R2113-HM2确认): 0 429, 0 SSL, 0 key_cycle_429s。dsv4p ATE全为R2112前历史数据(tiers_tried=1无glm5_2 fallback), 新部署后零新ATE。glm5_2 zombie是NVCF function-level degradation非config可修。低流量(43req/6h=7.2req/h, 5 keys)零key-exhaustion风险。继续storm-recovery: KEY 75→73走回R2110 storm增加值。KEY+TIER=73+64=137<153 BUDGET(16s margin)。73>60s NVCF边界+13s buffer。

## 修改

**单参数**: `KEY_COOLDOWN_S: 75→73` (-2s)

| Param | Before | After | Delta |
|-------|--------|-------|-------|
| KEY_COOLDOWN_S | 75 | 73 | -2s |

Budget: `KEY+TIER=73+64=137 < 153` (16s margin ✓)

## 验证

- `curl /health`: status=ok ✓
- `docker exec nv_gw env | grep KEY_COOLDOWN_S`: 73 ✓
- No restart errors in docker logs ✓
- KEY=73, TIER=64, UPSTREAM=24, BUDGET=153 ✓

## 铁律

只改HM1不改HM2. 单参数少改多轮.
## ⏳ 轮到HM1优化HM2