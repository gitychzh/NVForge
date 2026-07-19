# R1938 (HM2→HM1): NOP — false trigger (R1937 self-commit), 0 new data, 0 config-fixable

## 6h Data Snapshot (HM1 nv_gw)
- **Total**: 36 req / 27 OK (75.0% SR) / 9 fail
- **Failures**: 9 zombie_empty_completion, all glm5_2_nv, all big_input (130K–145K input_chars)
- **0 real ATE** (status=502, all_tiers_exhausted): 0
- **10 phantom ATE** (status=200, all_tiers_exhausted): BIG_INPUT breaker fast-reject / empty-200 rescue
- **glm5_2 genuine OK**: max duration=26165ms << TIER_BUDGET=30 safe (3.8s margin)
- **30min window**: 2/2 OK (100% SR)
- **10min window**: 0 req
- **fallback_occurred=f** on all — no peer-fallback triggered (breaker fresh after R1937 restart)

## Zombie Analysis
All 9 zombies are NVCF function-level degradation — glm5_2 systematically returns empty200 for large-input requests. This is NOT config-fixable on our side. Pattern unchanged from R1933–R1937.

## Parameter Status
All parameters at floor, no slack to tighten:

| Parameter | Value | Floor | Why floor |
|---|---|---|---|
| TIER_TIMEOUT_BUDGET_S | 152 | 152 | UPSTREAM(30)+PEER(122)=152 exact |
| UPSTREAM_TIMEOUT | 30 | 30 | glm5_2 OK max=26.2s, 3.8s margin |
| TIER_BUDGET_GLM5_2_NV | 30 | 30 | OK max=26.2s, 3.8s margin; 28 would leave 1.8s |
| TIER_BUDGET_DSV4P_NV | 25 | 25 | Severely degraded function, 0 genuine OK |
| KEY_COOLDOWN_S | 60 | 60 | =NVCF rate limit window, aligned with TIER_COOLDOWN |
| TIER_COOLDOWN_S | 60 | 60 | =KEY_COOLDOWN per iron law |
| MIN_OUTBOUND_INTERVAL_S | 0 | 0 | Absolute floor |
| CONNECT_RESERVE_S | 0 | 0 | Absolute floor |
| PEXEC_TIMEOUT_FASTBREAK | 1 | 1 | Absolute floor |
| EMPTY_200_FASTBREAK | 1 | 1 | Absolute floor |
| BIG_INPUT_COOLDOWN_S | 21600 | 21600 | 6h full window, already max |
| PEER_FALLBACK_TIMEOUT | 122 | 122 | =HM2_BUDGET+2 exact boundary |

## Intervention Criteria (四条介入)
1. **新错误类型** → NO (same zombie pattern R1933+)
2. **配置参数可收紧** → NO (all at floor, see table above)
3. **Breaker未覆盖的失败** → NO (all zombies caught by BIG_INPUT breaker)
4. **生产中断** → NO (30min 100% SR, 10min 0 req)

**NOP — 无据不改.**

## ⏳ 轮到HM1优化HM2
