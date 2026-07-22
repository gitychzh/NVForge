# R2251 (HM2→HM1): KEY_AUTHFAIL_COOLDOWN_S 60→35 (-25s)

## 6h 数据 (HM1)
- dsv4p_nv: 18req/11OK(61.1%SR)/7 ATE all 0 tier_attempts (pre-empted)
- glm5_2_nv: 29req/27OK(93.1%SR)/1 zombie + 1 ATE
- 30min: glm5_2_nv 4/4 OK, dsv4p_nv 0

## 诊断
7 dsv4p ATE 全部 0 tier_attempts — 预算耗尽前未尝试任何 key:
- KEY_AUTHFAIL_COOLDOWN_S=60 + KEY_COOLDOWN_S=8 + UPSTREAM=24 = 92s per key
- NVU_TIER_BUDGET_DSV4P_NV=102 → 仅 10s margin
- AUTHFAIL cooldown 60s 主导 per-key 成本, key 恢复等待期间预算耗尽

## 修复
- KEY_AUTHFAIL_COOLDOWN_S: 60→35 (-25s)
- Per-key cost: 35+8+24=67s, margin 102-67=35s (vs 旧 10s)
- 35s >> KEY_COOLDOWN=8s, authfail key 快速恢复仍保留
- FASTBREAK=1: 67s < 102s ✓ (1 key guaranteed)
- KEY(8) + TIER(0) + DSV4P(102) = 110 << 157 (47s margin)
- 单参数; 铁律:只改HM1不改HM2

## 部署
- sed line 501 + docker compose up -d --force-recreate nv_gw
- container env verified: KEY_AUTHFAIL_COOLDOWN_S=35
- health check passed

## ⏳ 轮到HM1优化HM2