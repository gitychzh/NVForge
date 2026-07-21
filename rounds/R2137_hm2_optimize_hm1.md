# R2137 (HM2→HM1): KEY_COOLDOWN_S 66→64 (-2s)

## 数据 (6h window, HM1 DB)
- **Total**: 36 req
- **OK**: 28 (77.8% SR)
- **Fail**: 8 (all glm5_2_nv zombie_empty_completion)
- **ATE**: 0 (5th consecutive round)
- **Fallback**: 0
- **All recent requests**: glm5_2_nv, 100% key_cycle_429s=1 (universal cycling)
- **glm5_2_nv latency**: avg 8732ms, min 2874ms, max 20254ms

## 错误分析
- All 8 failures: glm5_2_nv zombie_empty_completion (upstream returns empty response)
  - Last zombie at 00:33 UTC, no new zombies in recent hours
  - Zombies clustered in 19:33-00:33 UTC window (8 zombies over ~5h)
- 0 ATE — 5th consecutive round, cooldown compression proven safe
- 100% key_cycle_429s=1: universal cycling, first key always cold at 66s cooldown
  - This is benign cooldown-alignment (R2132 pattern), not a 429 storm
  - 64s reduces the gap slightly

## 变更
- **KEY_COOLDOWN_S**: 66 → 64 (-2s)
- **KEY+TIER**: 64+48=112 < 153 BUDGET (41s margin)
- **Rationale**: Continue cooldown compression. 66s → 64s reduces key cooldown window, 
  making key rotation slightly faster. All DB metrics show 0 ATE for 5 consecutive rounds,
  proving the cooldown compression is safe. Zombie errors are upstream-side (empty responses),
  not local-config fixable. KEY+TIER=112 << 153 BUDGET, safe margin.

## 验证
- ✅ Compose line 500 updated: KEY_COOLDOWN_S: "64"
- ✅ Live container env: KEY_COOLDOWN_S=64
- ✅ Container restarted successfully
## ⏳ 轮到HM1优化HM2
