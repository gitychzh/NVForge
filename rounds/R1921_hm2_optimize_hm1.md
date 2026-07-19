# R1921 (HM2→HM1): NVU_TIER_BUDGET_GLM5_2_NV 48→46 (-2s)

## 数据 (6h)
- **glm5_2_nv**: 31req/22OK(71.0%SR)/9 zombie_empty_completion
- **dsv4p_nv**: 7req/4OK(57.1%SR)/1 zombie + 2 real ATE
- Total: 38req/26OK(68.4%SR)/10 zombie + 2 ATE
- 429s: 26 cycles across 23 glm5_2 requests (moderate, key cycling functional)
- OK max: glm5_2=27.8s, dsv4p=19.6s — both << UPSTREAM=30 safe

## 分析
- glm5_2 zombies 是主要痛点 (9/31=29%)
- NVU_TIER_BUDGET_GLM5_2_NV=48 远超实际需求 — FASTBREAK=1 caps tier at ~30s (UPSTREAM=30), OK max=27.8s
- 48s budget 仅在 fail path (zombie) 上消耗, 每 zombie 浪费 48s→46s 省 2s
- OK 路径完全不受影响 (max=27.8s << 46s)
- 429s 26次 moderate — KEY_COOLDOWN=60 足够, 无需调整

## 修改
- **NVU_TIER_BUDGET_GLM5_2_NV: 48 → 46 (-2s)**
- 单参数; 铁律:只改HM1不改HM2

## 验证
- `docker exec nv_gw env`: NVU_TIER_BUDGET_GLM5_2_NV=46 ✓
- KEY=TIER=60 (iron law) ✓
- UPSTREAM_TIMEOUT=30 ✓
- TIER_TIMEOUT_BUDGET_S=153 (30+122=152<153, 1s margin) ✓
## ⏳ 轮到HM1优化HM2
