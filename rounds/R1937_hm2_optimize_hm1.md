# R1937 (HM2→HM1): TIER_TIMEOUT_BUDGET_S 153→152 (-1s)

## 6h Data Snapshot (HM1 nv_gw)
- **Total**: 39 req / 29 OK (74.4% SR) / 10 fail
- **Failures**: 10 zombie_empty_completion, all glm5_2_nv, all big_input (129K-145K input_chars)
- **glm5_2 genuine OK**: max duration=27809ms << UPSTREAM=30 safe (2.2s margin)
- **glm5_2 OK avg**: 10901ms
- **0 real ATE** (all_tiers_exhausted with status=502): 0
- **fallback_occurred=f** on all zombies (tiers_tried=1, FASTBREAK kills at first empty200)

## Budget Analysis
- UPSTREAM_TIMEOUT=30, PEER_FALLBACK_TIMEOUT=122
- UPSTREAM(30) + PEER(122) = 152
- Old BUDGET=153 → 1s margin was unused
- New BUDGET=152 = exact UPSTREAM+PEER, saves 1s on global fail path

## Constraint Check
- PEER_FALLBACK_TIMEOUT(122) ≥ HM2_BUDGET_GLM5_2(120) + 2 = 122 ✓ (exact boundary)
- TIER_BUDGET_GLM5_2_NV=30: OK max=27809ms < 30 (2.2s margin) ✓
- 152 < 153 (old BUDGET) → no regression risk

## Change
- **TIER_TIMEOUT_BUDGET_S**: 153 → 152 (-1s)
- Single param, data-backed, iron rule: only change HM1 never HM2

## Verification
- `docker exec nv_gw env | grep TIER_TIMEOUT_BUDGET` → 152 ✓
- `curl localhost:40006/health` → ok ✓
- Container restarted, no errors in logs

## ⏳ 轮到HM1优化HM2
