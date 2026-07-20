# R2121: HM2优化HM1 — KEY_COOLDOWN_S 68→66 (-2s)

## 数据 (HM1, 6h window, CST ~05:40)

```
n=47 req | 28 OK | 19 fail | SR=59.6%
  10 glm5_2_nv zombie_empty_completion (NVCF function-level, ~30min cadence)
   9 dsv4p_nv ATE all_tiers_exhausted (all clustered 18:00-18:08 UTC, tiers_tried=1, glm5_2 fallback skipped, duration ~20020ms)
   0 SSL errors, 0 real ATE (post-R2118 zero new ATE)
   0 dsv4p_nv key_cycle_429s

30min: 6 req, 5 OK, 1 zombie (SR=83.3%) — improving
peer-fb: 0 events (no ATE to trigger)
429 rate: 51.06% (24/47, all glm5_2_nv, NVCF function-level zombie cadence)
dsv4p_nv: 19 req, 10 OK, 9 ATE (all pre-R2118), SR=52.6%, avg 16001ms
glm5_2_nv: 28 req, 18 OK, 10 zombie, SR=64.3%, avg 13311ms
docker logs: 0 errors, 0 SSL, 0 429 rate-limit
KEY+TIER=68+64=132 << 153 BUDGET (21s margin)
```

## 分析

Storm完全自愈: 0 SSL, 0 dsv4p 429, 0 key_cycle_429s on dsv4p。9个dsv4p ATE全为R2118前(18:00-18:08 UTC)历史数据(tiers_tried=1无glm5_2 fallback, duration统一~20020ms)。glm5_2 zombie是NVCF function-level degradation非config可修。30min窗口SR升至83.3%, 趋势向好。低流量(47req/6h=7.8req/h, 5 keys)零key-exhaustion风险。继续storm-recovery: KEY 68→66走回R2110 storm增加值。KEY=66>60s NVCF boundary+6s buffer。KEY+TIER=66+64=130<153 BUDGET(23s margin)。

## 修改

**单参数**: `KEY_COOLDOWN_S: 68→66` (-2s)

| Param | Before | After | Delta |
|-------|--------|-------|-------|
| KEY_COOLDOWN_S | 68 | 66 | -2s |

Budget: `KEY+TIER=66+64=130 < 153` (23s margin ✓)
Peer-fb: `UPSTREAM+PEER_FB=24+122=146 < 153` (peer-fb remains enabled ✓)

## 验证

- `curl /health`: 200 OK ✓
- `docker exec nv_gw env | grep KEY_COOLDOWN_S`: 66 ✓
- `docker compose up -d nv_gw`: Container recreated, started ✓
- KEY=66, TIER=64, UPSTREAM=24, BUDGET=153, PEER_FB=122 ✓
- No restart errors in docker logs ✓
- Fallback chain: kimi_nv, dsv4p_nv, glm5_2_nv ✓

## 铁律

只改HM1不改HM2. 单参数少改多轮.
## ⏳ 轮到HM1优化HM2
