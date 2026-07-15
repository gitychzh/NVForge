# R1515: HM2→HM1 — NOP (false trigger, zero post-restart traffic, no HM1 commit)

**Trigger**: Script detected existing commit `4fc6f66` already processed; "等待新提交" — no new HM1 commit to respond to.

**Window**: 2026-07-15 17:00–23:03 UTC (6h, pre-restart at 22:25 UTC)

**6h Summary**: 70 req / 48 OK / 68.6% SR
- dsv4p_nv: 47/36 OK 76.6% SR, avg 16162ms
- glm5_2_nv: 23/12 OK 52.2% SR, avg 10025ms
- 18 zombie_empty_completion (NVCF content-filter, 不可配置)
- 5 all_tiers_exhausted (pre-restart, avg 35181ms)
- 2 tier_attempts: 429_integrate_rate_limit (k1/k2, transient)
- ms_gw: 16/15 93.8% SR

**Post-restart**: Container restarted 22:25 UTC. Zero traffic since. 14 docker log lines — 2 successful glm5_2_nv integrate requests (k1: 5149ms, k2: 6116ms). No errors.

**Config**: All params at floor/optimal. compose md5 9fb97661 unchanged from R1514.
- UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=205
- NVU_TIER_BUDGET_DSV4P_NV=66, NVU_TIER_BUDGET_GLM5_2_NV=96
- FASTBREAK: PEXEC=1, EMPTY_200=2, INTEGRATE=1
- TIER_COOLDOWN_S=15, KEY_COOLDOWN_S=25
- NVU_PEER_FB_SKIP_MODELS= (empty — peer-fb enabled for all)
- NVU_CONNECT_RESERVE_S=0, MIN_OUTBOUND_INTERVAL_S=0
- NVU_FORCE_STREAM_UPGRADE=0

**Decision**: NOP. 铁律:只改HM1不改HM2. 无HM1新commit, 零重启后流量, 所有参数floor/optimal.

## ⏳ 轮到HM1优化HM2
