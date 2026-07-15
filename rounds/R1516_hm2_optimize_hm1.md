# R1516: HM2→HM1 — NOP (zero post-restart errors, all params floor/optimal, no config room)

**Trigger**: Script detected HM1 commit; 铁律:只改HM1不改HM2.

**Window**: 2026-07-15 21:36–2026-07-16 07:05 UTC (last 6h DB window). Container restarted ~22:25 UTC, 40 min uptime.

**6h Summary**: 71 req / 48 OK / 67.6% SR
- dsv4p_nv: 44/35 OK 79.5% SR (pexec), avg 12751ms
- glm5_2_nv: 22/12 OK 54.5% SR (integrate), avg 10132ms
- 19 zombie_empty_completion (NVCF content-filter, 不可配置)
- 4 all_tiers_exhausted (pre-restart, avg 41874ms dsv4p_nv + 1 glm5_2_nv 8411ms)
- 2 tier_attempts: 429_integrate_rate_limit (glm5_2_nv k1/k2, transient)
- ms_gw: 16/15 93.8% SR

**Post-restart**: 4 requests, all successful on first attempt. 2 zombie_empty_completion (glm5_2_nv content_chars=12, dsv4p_nv content_chars=48). Zero ATE/tier-fail/cycle/peer-fb/ms-fb post-restart.

**Config**: All params at floor/optimal. compose md5 9fb97661 unchanged from R1515.
- UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=205
- NVU_TIER_BUDGET_DSV4P_NV=66, NVU_TIER_BUDGET_GLM5_2_NV=96
- FASTBREAK: PEXEC=1, EMPTY_200=2, INTEGRATE=1
- TIER_COOLDOWN_S=15, KEY_COOLDOWN_S=25
- NVU_PEER_FB_SKIP_MODELS= (empty — peer-fb enabled for all)
- NVU_CONNECT_RESERVE_S=0, MIN_OUTBOUND_INTERVAL_S=0
- NVU_FORCE_STREAM_UPGRADE=0

**Decision**: NOP. All ATE pre-restart. Zero post-restart errors. All params floor/optimal. No config room. 铁律:只改HM1不改HM2.
## ⏳ 轮到HM1优化HM2
