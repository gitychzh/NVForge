# R1240: HM2→HM1 — NOP (false trigger, double-dispatch)

## 数据 (2026-07-13, 容器 10:44 UTC restart)
```
6h: 112req/86OK(76.8%)/26fail
  pre-restart:  98req/75OK(76.5%)/23fail
  post-restart: 14req/11OK(78.6%)/3fail
```

| upstream_type | cnt | ok | err | avg_dur |
|---------------|-----|----|-----|---------|
| nv_integrate | 92 | 78 | 14 | 33,212ms |
| (ATE NULL) | 11 | 0 | 11 | 136,850ms |
| nvcf_pexec | 9 | 8 | 1 | 99,082ms |

| mapped_model | cnt | ok | err | sr_pct |
|--------------|-----|----|-----|--------|
| glm5_2_nv | 104 | 83 | 21 | 79.8% |
| dsv4p_nv | 8 | 3 | 5 | 37.5% |

| error_type | cnt |
|------------|-----|
| zombie_empty_completion | 14 |
| all_tiers_exhausted | 11 |
| NVStream_IncompleteRead | 1 |

## 分段分析
- **Post-restart (10:44→20:25, ~9.7h)**: 14req/11OK(78.6%)/3fail
  - 3 fail = zombie_empty_completion (NVCF content-filter, code-level fast abort, not config-fixable)
  - ZERO all_tiers_exhausted — system healthy
  - glm5_2_nv only; dsv4p_nv zero traffic post-restart

- **Pre-restart**: 98req/75OK(76.5%)/23fail
  - 11 all_tiers_exhausted: 5 dsv4p_nv (08:17-09:09, NVCF function degradation, old config) + 6 glm5_2_nv
  - dsv4p_nv: 8req/3OK(37.5%), 5 ATE all pre-restart, 3 success at 10:06-10:07 (pre-restart)
  - glm5_2_nv: 90req/72OK(80%), 18 fail (11+ zombie_empty + 6? all_tiers_exhausted + 1 NVStream_IncompleteRead)

## 诊断
1. **zombie_empty_completion (14)**: NVCF content-filter, code-level fast-abort feature (R1107). content_chars=12 < 50 with finish_reason=stop → sends content_filter SSE → openclaw fallback. 3-26s vs old 96s hang. NOT config-fixable. ✓ system is correctly detecting and fast-aborting.
2. **all_tiers_exhausted (11)**: ALL pre-restart. Post-restart zero ATE. Old config state, not current.
3. **NVStream_IncompleteRead (1)**: Pre-restart. Not recurrent.
4. **dsv4p_nv 37.5% SR**: ALL 5 ATEs pre-restart (08:17-09:09). 3 successes pre-restart (10:06-10:07). Zero post-restart traffic. Not actionable — no current data.
5. **ms_gw 0/16 OK**: BrokenPipeError code-level defect, not config-fixable. Same pattern as R1235-R1239.
6. **glm5_2_nv IntegrateTimeout**: 6 tier_attempts, avg 91,331ms, max 93,529ms. THINKING_TIMEOUT=90 → buffer=3.5s ≥ 3s rule (R751). All pre-restart. Acceptable.
7. **tier_chain=['glm5_2_nv'] (no fallback, 3model)**: Expected per R832. FALLBACK_GRAPH intentionally {}.
8. **NVU_PEER_FB_SKIP_MODELS=glm5_2_nv**: glm5_2_nv ATEs can't get peer fallback, but zero glm5_2_nv ATEs post-restart.

## 决策: NOP — 零参数改动
- Post-restart system healthy: 78.6% SR, only zombie_empty (code-level, not config-fixable)
- All all_tiers_exhausted pre-restart — old config state, resolved by container restart at 10:44
- All params at floor/optimal: UPSTREAM=66, FASTBREAK=1 (pexec+integrate), TIER_COOLDOWN=15, BUDGET=210, THINKING_TIMEOUT=90, EMPTY_200_FASTBREAK=2, TIER_BUDGET_DSV4P_NV=72, TIER_BUDGET_GLM5_2_NV=96
- NVCFPexecTimeout max << UPSTREAM=66 (no binding edge)
- dsv4p_nv zero post-restart traffic — no data to tune
- This is R1240: 6th consecutive NOP (R1235-R1240), all false triggers/double-dispatch from HM1 self-commits

## 参数不变 (0 param)
铁律:只改HM1不改HM2

## ⏳ 轮到HM1优化HM2