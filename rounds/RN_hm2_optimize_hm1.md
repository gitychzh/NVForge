# R720: HM2→HM1 — 零变更轮（NVCF dsv4p_nv primary function 持续死亡，glm5_2→dsv4p fallback 已自愈，所有参数已达最优/地板，无需配置变更）

## TL;DR
dsv4p_nv primary NVCF function `74f02205` 持续死亡 (health=0.0) 大部分窗口，但在 09:03 UTC 健康度回升至 0.167 > 0.10 → **glm5_2_nv→dsv4p_nv fallback 自愈**。R719 报告的 fallback 消失 (08:33-09:03 UTC) 已自动恢复。Post-restart (08:00+) 所有 ATE 均为 tiers_tried_count=2 (双 tier 真正 NVCF 耗尽)。dsv4p_nv auto-switch `8915fd28` 健康度 0.091-0.125 仍低。所有参数已达最优或地板。零变更。单参数每轮；铁律：只改 HM1 不改 HM2。

## 6h 整体数据
- **394 req / 283 OK (71.8%) / 111 ATE (28.2%)** — 与 R719 (71.6%/28.4%) 基本持平
- dsv4p_nv: 226 req / 127 OK (56.2%) / avg 50,658ms
- glm5_2_nv: 160 req / 149 OK (93.1%) / avg 13,847ms
- kimi_nv: 8 req / 7 OK (87.5%) / avg 9,368ms

## Post-Restart 数据 (08:00 UTC+, 容器重启后)
- 35 req / 23 OK (65.7%) / 12 ATE (34.3%)
- dsv4p_nv: 26 req / 14 OK (53.8%)
- glm5_2_nv: 9 req / 9 OK (100.0%)
- Fallback 成功: 8/8 OK (100%), avg 52,906ms, max 63,014ms

## ATE 分类
- tiers_tried_count=1: 70 ATE, avg 47,103ms — **全部 fallback_actually_attempted=f (pre-restart)**
  - start_tier_idx=1 (dsv4p_nv): 58, avg 50,383ms
  - start_tier_idx=3 (glm5_2_nv): 11, avg 33,847ms
  - start_tier_idx=0: 1, avg 2,682ms
- tiers_tried_count=2: 41 ATE, avg 95,592ms — **双 tier 真正 NVCF 耗尽 (全部 post-restart)**

## NVCFPexecTimeout (dsv4p_nv, 失败尝试)
- 64 timeouts, 5 keys 均匀分布: k0=12, k1=13, k2=18, k3=11, k4=11
- avg 31,397ms, max 40,492ms — **UPSTREAM_TIMEOUT=40 边缘绑定** (max=40,492ms ≈ 40+~500ms)
- IntegrateTimeout: 16, avg 25,394ms, max 25,511ms

## NVCFPexecTimeout (glm5_2_nv, 失败尝试)
- 15 NVCFPexecTimeout, avg 30,012ms, max 40,271ms
- 14 429_nv_rate_limit

## 🔑 关键发现：glm5_2_nv→dsv4p_nv fallback 已自愈
- 08:03 UTC: glm5_2_nv tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback, MIN_SAMPLES 保护)
- 08:33 UTC: glm5_2_nv tier_chain=['glm5_2_nv'] (no fallback, 3model) — R719 报告致命缺陷
- **09:03 UTC: glm5_2_nv tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback, health={'74f02205...': 0.167})** — **自愈！**
- 自愈原因: dsv4p_nv primary function 74f02205 健康度从 0.0 回升至 0.167 > 0.10 (FALLBACK_HEALTH_THRESHOLD)
- dsv4p_nv→glm5_2_nv fallback 始终正常工作 (tier_chain=['dsv4p_nv', 'glm5_2_nv'] 持续)

## 健康度状态
- dsv4p_nv primary `74f02205`: health=0.0→0.167 (从死亡回升, 09:03 UTC 突破阈值)
- dsv4p_nv auto-switch `8915fd28`: health=0.091-0.125 (低健康度, 递减趋势)
- glm5_2_nv primary `3b9748d8`: health=0.45-0.5 (稳定)

## 小时级 SR 趋势
| 小时 (UTC) | 请求 | OK | ATE | SR% |
|-----------|------|-----|-----|-----|
| 19:00 (Jul 4) | 114 | 99 | 15 | 86.8 |
| 20:00 | 14 | 8 | 6 | 57.1 |
| 21:00 | 15 | 8 | 7 | 53.3 |
| 22:00 | 28 | 13 | 15 | 46.4 |
| 23:00 | 9 | 8 | 1 | 88.9 |
| 00:00 (Jul 5) | 2 | 2 | 0 | 100.0 |
| 01:00 | 13 | 8 | 5 | 61.5 |
| 02:00 | 49 | 35 | 14 | 71.4 |
| 03:00 | 27 | 20 | 7 | 74.1 |
| 04:00 | 21 | 14 | 7 | 66.7 |
| 05:00 | 20 | 7 | 13 | 35.0 |
| 06:00 | 29 | 22 | 7 | 75.9 |
| 07:00 | 24 | 21 | 3 | 87.5 |
| 08:00 | 23 | 13 | 10 | 56.5 |
| 09:00 | 6 | 5 | 1 | 83.3 |

## 当前配置 (全部已达最优/地板)
- UPSTREAM_TIMEOUT=40 (R716, edge binding, max=40,492ms)
- TIER_TIMEOUT_BUDGET_S=110 (R706, 充足余量)
- NVU_PEXEC_TIMEOUT_FASTBREAK=1 (R709, 省60s/ATE, 地板)
- FALLBACK_HEALTH_THRESHOLD=0.10 (R708, 地板值)
- KEY_COOLDOWN_S=25, TIER_COOLDOWN_S=25
- NVU_CONNECT_RESERVE_S=0 (R657, 地板)
- MIN_OUTBOUND_INTERVAL_S=0 (R638, 地板)
- NV_INTEGRATE_KEY_COOLDOWN_S=0 (R631, 地板)
- NVU_FORCE_STREAM_UPGRADE_TIMEOUT=40 (R694)
- NVU_FORCE_STREAM_UPGRADE=0 (R692)

## 决策：零变更
- dsv4p_nv primary function 74f02205 持续死亡 → NVCF 上游问题，非配置可修
- Auto-switch 8915fd28 健康度 0.091-0.125 仍低 → 上游问题
- glm5_2→dsv4p fallback 已于 09:03 UTC 自愈 (74f02205 健康度回升至 0.167 > 0.10)
- Post-restart 所有 ATE 均为 tiers_tried_count=2 (双 tier NVCF 真正耗尽) — 非配置可修
- 所有参数已达最优或地板，无变更空间
- UPSTREAM_TIMEOUT=40 已足够 (edge binding 仅边缘个例)
- FASTBREAK=1 已验证最优 (R709 从 2→1)
- FALLBACK_HEALTH_THRESHOLD=0.10 已是地板
- Post-restart fallback 8/8 = 100% SR 证明 fallback 链路正常
- 单参数每轮；铁律：只改 HM1 不改 HM2

## ⏳ 轮到HM1优化HM2