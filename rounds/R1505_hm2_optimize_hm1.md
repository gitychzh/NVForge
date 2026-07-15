# R1505: HM2→HM1 — NOP (zero ATE in 3h post-restart, zombie-only, 2 integrate-429 tier attempts, all params floor/optimal)

## 数据收集 (HM1, 6h window)
- **6h**: 61req/38OK 62.3%SR, 23 fail
- **失败分解**: 20 zombie_empty_completion (NVCF content-filter, 不可配置), 6 all_tiers_exhausted (全部 pre-restart, avg 39,951ms), 2 tier_attempts (429_integrate_rate_limit on glm5_2_nv K1/K2)
- **Post-restart (3h)**: 0 ATE, 0 tier cycling, 0 peer-fb, 0 ms-gw fallback, 0 key_cycle_429s
- **Pexec 路径**: dsv4p_nv 100% SR (31/31 OK), glm5_2_nv 100% SR (12/12 OK)
- **Integrate 路径**: glm5_2_nv K1 success 3.3s, K2 success 2.6s — 快速正常
- **2 tier_attempts**: 429_integrate_rate_limit — NVCF 侧 per-key RPM, NV_INTEGRATE_KEY_COOLDOWN_S=0 已 floor, 不可再降

## 分析
- Zombie 是唯一失败源 (20/23=87%), NVCF content-filter 行为, 不可配置
- 6 ATE 全部 pre-restart (旧 regime 留存量), post-restart 零 ATE
- 2 integrate 429 tier attempts: cooldown 已 floor, 不可配置
- All FASTBREAK/Cooldown/Timeout/Budget 已 floor/optimal
- compose md5 ba4f2871 unchanged

## 变更: NOP (无变更)
- 所有参数已在 floor/optimal
- 无配置可优化空间
- 铁律: 只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
