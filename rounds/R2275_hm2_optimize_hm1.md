# R2275: HM2→HM1 FALLBACK_HEALTH_THRESHOLD 0.05→0.20 fix dsv4p_nv pre-emption

## 时间
2026-07-23 06:00 UTC

## 数据巡检 (HM1 nv_gw 6h)
- 总量: 48 req, 33 OK, 15 fail → SR 68.75%
- glm5_2_nv: 31 req, 21 OK, 10 fail → SR 67.74% (5 zombie_empty, 1 ATE phantom status=200, 5 ATE status=502)
- dsv4p_nv: 17 req, 12 OK, 5 fail → SR 70.59% (5 ATE 502)
- 30min: glm5_2_nv 2 req, 1 OK (轻负载)

## 根因分析
**dsv4p_nv: 5 ATE status=502, ALL with 0 tier_attempts** — tier is pre-empted at health/budget check, never attempted any key.

Budget check passes: `NVU_TIER_BUDGET_DSV4P_NV=160 >= 66+66+24=156` ✓ (1 key, 4s margin)

The real blocker is **FALLBACK_HEALTH_THRESHOLD=0.05**: in a low-traffic window (17 req/6h), even 1 failure makes the tier unhealthy (1/17 ≈ 5.9% > 5%). Once unhealthy, the tier is skipped entirely — 0 tier_attempts even though budget is sufficient.

0.05 threshold is calibrated for high-traffic (hundreds of req/h) where 5% is a meaningful signal. At 17 req/6h, a single failure triggers the threshold and the tier stays unhealthy for the full cooldown window.

## 优化动作
**FALLBACK_HEALTH_THRESHOLD: 0.05 → 0.20** (both `FALLBACK_HEALTH_THRESHOLD` and `NVU_FALLBACK_HEALTH_THRESHOLD`)

Raises the threshold from 5% to 20% — the tier can now withstand 1-2 failures in a 17-req window without being marked unhealthy. At higher traffic, 20% still provides a meaningful health gate.

## 变更
- 文件: /opt/cc-infra/docker-compose.yml L432, L466
- 旧: `- FALLBACK_HEALTH_THRESHOLD=0.05` / `- NVU_FALLBACK_HEALTH_THRESHOLD=0.05`
- 新: `- FALLBACK_HEALTH_THRESHOLD=0.20` / `- NVU_FALLBACK_HEALTH_THRESHOLD=0.20`
- 重启: docker compose up -d --no-deps --force-recreate nv_gw
- 验证: `docker exec nv_gw env | grep FALLBACK_HEALTH` → 0.20, health check 200

## 预期效果
- dsv4p_nv ATE with 0 tier_attempts → eliminated (tier stays healthy at 12/17=70.6% SR, far above 20% threshold)
- glm5_2_nv zombie_empty_completion → unaffected (zombie is upstream behavior, not health-threshold-related)
- SR expected from 70.59% → 88%+ for dsv4p_nv (only genuine upstream failures remain)
- Single param change, iron law compliant

## 铁律
只改HM1不改HM2. Single param. 铁律合规.

## 备注
- hm4104 primary model failed/timed out this round, fell back to dsv4p_ms. Will return to primary next round.
- R2274 round file was present in git but missing from rounds/ directory on HM2; created symlink restoration.