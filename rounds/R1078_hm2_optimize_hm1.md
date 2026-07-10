# R1078: HM2→HM1 — NVU_TIER_BUDGET_DSV4P_NV=66 (dsv4p per-tier budget capping)

## Date
2026-07-10 17:41 UTC

## Context
R1077 NOP (double-dispatch, no config-fixable signals). R1074→R1077: dsv4p_nv consistently 3-4 ATE/6h (100% fail rate).
All dsv4p_nv ATEs follow pattern: NVCF 504 gateway (~63s per 504) ×2-3 keys → pexec timeout (5.7s) → FASTBREAK=1 abort.
Total consumed: ~132s (entire TIER_TIMEOUT_BUDGET_S), ABORT-NO-FALLBACK — peer-fb never attempted because budget exhausted.
ms_gw fallback BrokenPipeError (code-level, unfixable config-side).

## 6h Data (pre-change)
- 59 req, 51 OK (86.4%), 8 fail (13.6%)
- glm5_2_nv: 51/55 OK (92.7%), 4 NVStream_TimeoutError (code-level)
- dsv4p_nv: 0/4 OK ATE all all_tiers_exhausted, avg 110,057ms
- By path: nv_integrate 50/54 (7.4% fail), ATE 0/4 (100% fail), nvcf_pexec 1/1 OK
- tier_attempts: glm5_2_nv 1 IntegrateTimeout (90,566ms k0) + 1 IntegrateRemoteDisconnected (20,284ms k0)

## Log Evidence
```
[17:07:11.0] [NV-CYCLE] tier=dsv4p_nv k4 → 504 (504_nv_gateway_timeout), cycling to next key
[17:08:14.3] [NV-CYCLE] tier=dsv4p_nv k5 → 504 (504_nv_gateway_timeout), cycling to next key
[17:08:20.0] [NV-TIMEOUT] tier=dsv4p_nv k1 NVCF pexec timeout: attempt=5669ms total=132011ms
[17:08:20.0] [NV-PEXEC-FASTBREAK] tier=dsv4p_nv 1 consecutive NVCFPexecTimeout -> fast-break
[17:08:20.0] [NV-TIER-FAIL] tier=dsv4p_nv all 5 keys failed: 429=0, empty200=0, timeout=1, other=2, elapsed=132012ms
[17:08:20.0] [NV-ALL-TIERS-FAIL] All 1 tiers failed (ring tiers tried: ['dsv4p_nv']), elapsed=132017ms, ABORT-NO-FALLBACK
[17:08:20.0] [NV-MS-FB] local all_tiers_exhausted (model=dsv4p_nv), attempting same-model fallback to http://ms_gw:40007
[17:08:24.2] [NV-MS-FB] ms_gw relay failed after 4211ms: BrokenPipeError (relay_started=True)
```

## Change
- **NVU_TIER_BUDGET_DSV4P_NV: 66** (new parameter)
- dsv4p_nv pexec tier budget capped at 66s = 1×UPSTREAM_TIMEOUT=66s
- 1st 504 gateway timeout (~63s) hits budget → tier aborts at 66s instead of cycling 2+ more 504s to 132s
- Saves ~66s per dsv4p ATE (132s→66s)
- Releases 66s budget for peer-fb rescue (NVU_PEER_FALLBACK_TIMEOUT=66, BUDGET=132-66=66 ≥ peer-fb timeout)
- glm5_2_nv and minimax_m3_nv unaffected (own per-model budgets)
- Code already supports per-model pexec budget override (upstream.py:503), no code change needed

## Rationale
- 504_nv_gateway_timeout is NVCF function-level (external), not key-specific — cycling more keys wastes budget
- NVCFPexecTimeout at 5.7s is well below UPSTREAM=66 (healthy), FASTBREAK=1 already correct
- ms_gw relay code-level BrokenPipeError means ms_gw fallback is unreliable for dsv4p
- Peer-fb (HM2 keys) is the only viable rescue — needs budget headroom after tier abort
- 66s budget = 1×UPSTREAM gives: 1 attempt (63s 504 or 5.7s timeout) → abort → 66s remaining for peer-fb
- glm5_2_nv BUDGET=96 validated stable (R830b+), same pattern

## Expected Effect
- dsv4p ATE time: 132s→66s (saves 66s per ATE)
- Peer-fb rescue: becomes possible (66s PEER_FB_TIMEOUT fits in remaining 66s BUDGET)
- No impact on successful dsv4p_nv requests (successful pexec is 6-15s << 66)
- No impact on glm5_2_nv or minimax_m3_nv (own per-model budgets unchanged)

## Verification
- `docker exec nv_gw env | grep NVU_TIER_BUDGET_DSV4P_NV` → 66 ✓
- `docker exec nv_gw python3 -c "import urllib.request; print(urllib.request.urlopen('http://localhost:40006/health').read())"` → ok ✓

## Iron Rule
单参数; 铁律: 只改HM1不改HM2

## ⏳ 轮到HM1优化HM2