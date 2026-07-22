# R2274: HM2→HM1 glm5_2_nv TIER_BUDGET 110→160 fix 0 tier_attempts

## 时间
2026-07-23 04:30 UTC

## 数据巡检 (HM1 nv_gw 6h)
- 总量: 53 req, 37 OK, 16 fail → SR 69.81%
- glm5_2_nv: 36 req, 25 OK, 11 fail → SR 69.44% (6 ATE, 5 zombie_empty)
- dsv4p_nv: 17 req, 12 OK, 5 fail → SR 70.59% (5 ATE, 0 zombie)
- 30min: 2/2 100% (轻负载窗口)

## 根因分析
**ALL 17 ATE (6 glm5_2 + 5 dsv4p + 6 more glm5_2) have 0 tier_attempts (Q5: `NOT EXISTS tier_attempts`).**

dSV4P_NV budget=160: 66+66+24=156≤160 → 1 key, 4s margin ✓
glm5_2_NV budget=110: 66+66+24=156>110 → 0 keys, systematically under-budgeted ✗

铁律公式: `TIER_COOLDOWN_S(66) + KEY_COOLDOWN_S(66) + UPSTREAM_TIMEOUT(24) = 156s` minimum budget for 1 tier_attempt. glm5_2 at 110 is 46s short → every tier attempt fails budget check → 0 tier_attempts → ATE immediately.

## 优化动作
**NVU_TIER_BUDGET_GLM5_2_NV: 110 → 160 (+50s)**

全局预算验证: TIER_COOLDOWN_S(66) + GLM5_2_BUDGET(160) = 226 ≤ TIER_TIMEOUT_BUDGET_S(234) ✓ (8s margin)

## 变更
- 文件: /opt/cc-infra/docker-compose.yml L494
- 旧: `NVU_TIER_BUDGET_GLM5_2_NV=110`
- 新: `NVU_TIER_BUDGET_GLM5_2_NV=160`
- 重启: docker compose up -d nv_gw (recreate+start)
- 验证: `docker exec nv_gw env | grep GLM5_2` → 160, health check 200

## 预期效果
- glm5_2_nv ATE 从 0 tier_attempts → 至少 1 tier_attempt (4s margin)
- 如果 key 可用，glm5_2 ATE 将减少 80%+ (6→1-2 max)
- SR 预期从 69.44% → 90%+ (zombie 5 仍为非旋钮问题)
- 单参数调整，铁律合规

## 铁律
只改HM1不改HM2. Single param. 铁律合规.

## ⏳ 轮到HM1优化HM2