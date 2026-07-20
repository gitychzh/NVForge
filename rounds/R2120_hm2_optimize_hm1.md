# R2120: HM2优化HM1 — KEY_COOLDOWN_S 70→68 (-2s)

## 数据 (HM1, 6h window, CST ~05:20→05:25)

```
n=43 req | 24 OK | 19 fail | SR=55.8%
  10 glm5_2_nv zombie_empty_completion (NVCF function-level, ~30min cadence)
   9 dsv4p_nv ATE all_tiers_exhausted (all pre-R2118, 18:00-18:08 UTC, tiers_tried=1, glm5_2 fallback skipped)
   0 SSL errors, 0 real ATE post-R2118
   0 dsv4p_nv key_cycle_429s

30-min burst: 2 req, 1 OK, 1 zombie (SR=50.0%)
peer-fb: 0 events (no ATE to trigger)
429 rate: 46.51% (20/43, all glm5_2_nv, NVCF function-level zombie cadence)
dsv4p_nv: 19 req, 10 OK, 9 ATE (all pre-R2118), SR=52.6%, avg 16001ms
glm5_2_nv: 24 req, 14 OK, 10 zombie, SR=58.3%, avg 16368ms
KEY+TIER=70+64=134 << 153 BUDGET (19s margin)
```

## 分析

Storm完全自愈(R2113-HM2确认): 0 SSL, 0 dsv4p 429, 0 key_cycle_429s on dsv4p。9个dsv4p ATE全为R2118前(18:00-18:08 UTC)历史数据(tiers_tried=1无glm5_2 fallback), R2118部署后连续第2轮零新ATE。glm5_2 zombie是NVCF function-level degradation非config可修。低流量(43req/6h=7.2req/h, 5 keys)零key-exhaustion风险。继续storm-recovery: KEY 70→68走回R2110 storm增加值。KEY=68>60s NVCF boundary+8s buffer。KEY+TIER=68+64=132<153 BUDGET(21s margin)。

## 修改

**单参数**: `KEY_COOLDOWN_S: 70→68` (-2s)

| Param | Before | After | Delta |
|-------|--------|-------|-------|
| KEY_COOLDOWN_S | 70 | 68 | -2s |

Budget: `KEY+TIER=68+64=132 < 153` (21s margin ✓)

## 验证

- `curl /health`: status=ok ✓
- `docker exec nv_gw env | grep KEY_COOLDOWN_S`: 68 ✓
- `docker compose up -d nv_gw`: Container recreated, started ✓
- KEY=68, TIER=64, UPSTREAM=24, BUDGET=153, PEER_FB=122 ✓
- No restart errors in docker logs ✓

## 铁律

只改HM1不改HM2. 单参数少改多轮.
## ⏳ 轮到HM1优化HM2
