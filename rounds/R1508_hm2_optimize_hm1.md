# R1508: HM2→HM1 — NOP (zero post-restart traffic, wait for R1507 validation)

## 数据收集 (HM1, 6h window)
- **6h**: 75req/52OK 69.3%SR, 23 fail
- **失败分解**: 21 zombie_empty_completion + 2 all_tiers_exhausted (ATE, all dsv4p_nv)
- **dsv4p_nv**: 51req/40OK 78.4%SR, 9 zombie + 5 ATE (DB: 5 rows, avg 35127ms)
- **glm5_2_nv**: 24req/12OK 50.0%SR, 12 zombie, 0 ATE
- **6h tier_attempts**: 2 (429_integrate_rate_limit, glm5_2_nv)
- **ms_gw**: 15req/14OK 93.3% SR
- **0 fallback_occurred in 6h DB**
- **Hourly SR**: 16:00 66.7% → 17:00 50.0% → 18:00 77.8% → 19:00 55.6% → 20:00 60.0% → 21:00 81.0%
- **⚠️ Container restart**: 2026-07-15 21:46 UTC (6 min ago) — zero post-restart traffic
- **Post-restart logs (tail 50)**: startup only, 0 NV-MS-FB, 0 NV-PEER-FB, 0 NV-TIER-FAIL
- **Compose md5**: f77f0381 (unchanged from R1507)
- **Container env**: all in sync with compose

## 分析
- R1507 刚部署 dsv4p_nv→dsv4p_ms 到 MS_GW_FALLBACK_MODELMAP, 容器重启 6 分钟, 零流量
- 所有 6h 数据均为 pre-restart (旧配置), 无法验证 R1507 效果
- Zombie (91% 失败) = NVCF content-filter 行为, 不可配置修复
- 5 ATE (all dsv4p_nv) 在 R1507 前, 预期 ms_gw 93.3% SR 可 rescue
- 所有参数在 floor/optimal 水平: BUDGET=66=UPSTREAM_TIMEOUT, FASTBREAK at floor, cooldowns at minimum
- glm5_2_nv 50% SR = zombie only (12/12), 无可配置修复
- 0 tier_attempts (仅 2 个 429, 非 key 耗尽)

## 决策: NOP
- 无可配置优化: zombie 不可修复, ATE 已由 R1507 覆盖, 所有参数在 floor
- 需等待流量验证 R1507 ms_gw fallback 效果
- 单参数纪律, 少改多轮

## 变更: 无
- 铁律: 只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
