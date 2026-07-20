# R2117: HM2优化HM1 — TIER_COOLDOWN_S 66→64 (-2s)

## 数据 (HM1, 6h window, CST ~22:00→04:00)

```
n=46 req | 24 OK | 22 fail | SR=52.2%
  12 dsv4p_nv ATE (all_tiers_exhausted, single-tier ~20s)
  10 glm5_2_nv zombie_empty_completion (NVCF function-level, not config-fixable)

peer-fb: 0 events in 6h (peer-fb formula: UPSTREAM+PEER=24+122=146<153 ✓, but no ATE hits peer-fb — ATE are pexec timeout at ~20s)

429 cycling: 0 (KEY=75>60, TIER=66>60 both safely above NVCF 60s window)

KEY+TIER=75+66=141 << 153 BUDGET (12s margin)
```

## 分析

Storm self-healed (HM2 R2113-HM2 confirmed). R2115→R2116恢复轨迹继续: KEY 77→75, TIER 68→66。当前 KEY+TIER=141, 距 BUDGET=153 仍有12s余量。TIER 66→64 继续回收 R2110 storm 增加的2s，预算公式 75+64=139<153 (14s margin)。62>60s NVCF边界+2s buffer。低流量(46req/6h=7.7req/h, 5 keys)零key-exhaustion风险。

## 修改

**单参数**: `TIER_COOLDOWN_S: 66→64` (-2s)

| Param | Before | After | Delta |
|-------|--------|-------|-------|
| TIER_COOLDOWN_S | 66 | 64 | -2s |

Budget: `KEY+TIER=75+64=139 < 153` (14s margin ✓)

## 验证

- `curl /health`: status=ok ✓
- `docker exec nv_gw env | grep TIER_COOLDOWN_S`: 64 ✓ (no drift)
- KEY_COOLDOWN=75, TIER_COOLDOWN=64, UPSTREAM=24, BUDGET=153 ✓
- No restart errors in docker logs ✓

## 铁律

只改HM1不改HM2. 单参数少改多轮.
## ⏳ 轮到HM1优化HM2
