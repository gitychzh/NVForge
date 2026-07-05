# R719: HM2→HM1 — 零变更轮（NVCF dsv4p_nv primary function 持续死亡，auto-switch 8915fd28 低健康度，所有参数已达最优/地板，无需配置变更）

## TL;DR
dsv4p_nv primary NVCF function `74f02205` 持续死亡 (health=0.0) 整个6h窗口。Auto-switch 到 `8915fd28` 但健康度仅 0.111-0.333。dsv4p_nv SR 55.9% vs glm5_2_nv 93.0%。Fallback 42/42 100% SR。glm5_2_nv→dsv4p_nv fallback 于 08:33 UTC 消失（HEALTH_THRESHOLD=0.10 排除 health=0.0 的 primary function，auto-switch 仅对主 tier 生效不对 fallback target 生效）。所有参数已达最优或地板：UPSTREAM=40(R716), BUDGET=110(R706), FASTBREAK=1(R709), FALLBACK_HEALTH_THRESHOLD=0.10(R708), KEY_COOLDOWN=25, TIER_COOLDOWN=25, CONNECT_RESERVE=0, MIN_OUTBOUND=0。零变更。单参数每轮；铁律：只改 HM1 不改 HM2。

## 6h 整体数据
- **387 req / 277 OK (71.6%) / 110 ATE (28.4%)**
- dsv4p_nv: 222 req / 124 OK (55.9%) / avg 50,553ms
- glm5_2_nv: 157 req / 146 OK (93.0%) / avg 13,988ms
- kimi_nv: 8 req / 7 OK (87.5%) / avg 9,368ms

## ATE 分类
- tiers_tried_count=1: 70 ATE, avg 47,103ms — **全部 fallback_actually_attempted=f**
  - start_tier_idx=1 (dsv4p_nv): 58, avg 50,383ms
  - start_tier_idx=3 (glm5_2_nv): 11, avg 33,847ms
  - start_tier_idx=0: 1, avg 2,682ms
- tiers_tried_count=2: 40 ATE, avg 95,964ms — 双 tier 真正耗尽

## Fallback 统计
- fallback_occurred=t: 42 OK, avg 57,093ms, max 99,088ms — **100% SR**
- fallback_occurred=f: 235 OK, avg 16,852ms

## NVCFPexecTimeout (dsv4p_nv, 失败尝试)
- 5 keys 均匀分布: 11-15 timeouts each
- avg 29,835-32,475ms, max 36,475-40,492ms
- **UPSTREAM_TIMEOUT=40 binding on edge** (max=40,492ms ≈ 40+~500ms overhead)

## 健康度状态
- dsv4p_nv primary `74f02205`: **health=0.0 (DEAD)**, 整个窗口
- dsv4p_nv auto-switch `8915fd28`: health=0.111→0.333 (递减趋势)
- glm5_2_nv primary `3b9748d8`: health=0.375→0.5 (稳定)

## 关键发现：glm5_2_nv→dsv4p_nv fallback 消失 (R708 模式)
- 08:03 UTC: glm5_2_nv tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback, health={}) — MIN_SAMPLES 保护
- 08:03 UTC: health={'3b9748d8...': 1.0} — 样本不足，dsv4p function 未评估
- **08:33 UTC**: glm5_2_nv tier_chain=['glm5_2_nv'] **(no fallback, 3model)** — 样本积累后 dsv4p_nv primary function health=0.0 < 0.10 → 被 HEALTH_THRESHOLD 排除
- dsv4p_nv→glm5_2_nv fallback 仍正常 (tier_chain=['dsv4p_nv', 'glm5_2_nv'] 持续到 08:58)
- **根因**: auto-switch 仅对主 tier 生效，fallback target 的 health check 只看 primary function 不看 auto-switch function。这是代码级问题，非配置可修。

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
| 08:00 | 22 | 12 | 10 | 54.5 |

## 当前配置 (全部已达最优/地板)
- UPSTREAM_TIMEOUT=40 (R716, edge binding, max=40,492ms)
- TIER_TIMEOUT_BUDGET_S=110 (R706, 充足余量)
- NVU_PEXEC_TIMEOUT_FASTBREAK=1 (R709, 省60s/ATE)
- FALLBACK_HEALTH_THRESHOLD=0.10 (R708, 地板值)
- KEY_COOLDOWN_S=25, TIER_COOLDOWN_S=25
- NVU_CONNECT_RESERVE_S=0 (R657)
- MIN_OUTBOUND_INTERVAL_S=0 (R638)
- NV_INTEGRATE_KEY_COOLDOWN_S=0 (R631)
- NVU_FORCE_STREAM_UPGRADE_TIMEOUT=40 (R694)

## 决策：零变更
- dsv4p_nv primary function 74f02205 持续死亡 → NVCF 上游问题，非配置可修
- Auto-switch 8915fd28 健康度 0.111-0.333 仍低 → 上游问题
- 所有参数已达最优或地板，无变更空间
- UPSTREAM_TIMEOUT=40 已足够（edge binding 仅边缘个例）
- FASTBREAK=1 已验证最优（R709 从 2→1）
- FALLBACK_HEALTH_THRESHOLD=0.10 已是地板（0.0 允许真正死函数更危险）
- Fallback 100% SR (42/42) 证明 fallback 链路正常
- 单参数每轮；铁律：只改 HM1 不改 HM2

## ⏳ 轮到HM1优化HM2