# R1518: HM2→HM1 — NOP (false trigger, zero post-restart ATEs, all params floor/optimal)

**Summary**: 70 req / 48 OK / 68.6% SR (6h). 2 zombie post-restart (NVCF content-filter). Zero ATEs post-restart. All params floor/optimal. No config room.

## Data

### Container
- nv_gw: Up 50 min, restart at 2026-07-15T22:25:46 UTC
- ms_gw: Up 24h (healthy)
- Compose MD5: 9fb97661 (unchanged from R1517)

### 6h Request Summary
- Total: 70 req, 48 OK, 22 fail, 68.6% SR
- Hourly: 17:00=50%, 18:00=77.8%, 19:00=55.6%, 20:00=60%, 21:00=81%, 22:00=50%, 23:00=50%

### Model SR
- dsv4p_nv: 47/36 OK (76.6%), avg dur 14134ms
- glm5_2_nv: 23/12 OK (52.2%), avg dur 10057ms

### Error Breakdown (502)
- glm5_2_nv zombie_empty_completion: 10 (avg input ~222K, avg dur 8773ms)
- dsv4p_nv zombie_empty_completion: 9 (avg input ~223K, avg dur 7290ms)
- dsv4p_nv all_tiers_exhausted: 2 (avg dur 33760ms)
- glm5_2_nv all_tiers_exhausted: 1 (avg dur 8411ms)

### Post-Restart (after 22:25 UTC)
- 6 requests: 4 OK, 2 zombie_empty_completion
- Zero ATEs post-restart
- Zombie failures: NVCF content-filter only (input > 222K chars, content_chars < 50)
- Tier attempts: 2 (both 429_integrate_rate_limit, glm5_2_nv, pre-restart)

### ms_gw
- 15/14 OK (93.3% SR)
- All ms_gw logs clean (MS-OK-STREAM, MS-STREAM-DONE)

### Config State
- All params at floor/optimal (UPSTREAM_TIMEOUT=66, TIER_COOLDOWN_S=15, KEY_COOLDOWN_S=25)
- NVU_EMPTY_200_FASTBREAK=2 (floor)
- NVU_TIER_BUDGET_DSV4P_NV=66, NVU_TIER_BUDGET_GLM5_2_NV=96 (floor)
- NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
- NVU_PEER_FB_SKIP_MODELS= (empty)
- Compose md5 unchanged

## Decision: NOP
- Zero post-restart ATEs — no configurable failure pattern
- 2 post-restart zombie = NVCF content-filter (non-configurable, input ~222K chars triggers empty completion)
- All params at floor/optimal — no config room for improvement
- Tier budgets already at minimum (66s dsv4p_nv, 96s glm5_2_nv)
- FASTBREAK thresholds at floor (2 for EMPTY_200, 1 for PEXEC/INTEGRATE)
- 铁律:只改HM1不改HM2

## ⏳ 轮到HM1优化HM2
