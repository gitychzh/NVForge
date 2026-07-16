# R1660 (HM2→HM1): NOP — zombie dominates, FASTBREAK=2 unevaluable, all params at floor

## Data: HM1 6h (2026-07-16 18:00–2026-07-17 00:00 UTC)

| Model | OK | Fail | Total | SR |
|---|---|---|---|---|
| glm5_2_nv | 15 | 13 | 28 | 53.6% |
| dsv4p_nv | 7 | 5 | 12 | 58.3% |
| **Total** | **22** | **18** | **40** | **55.0%** |

### Error Breakdown

| Model | Error Type | Count |
|---|---|---|
| glm5_2_nv | zombie_empty_completion | 13 |
| dsv4p_nv | all_tiers_exhausted | 5 |

### Key Observations

1. **zombie_empty_completion (13, 100% of glm5_2 fails)**: NVCF server-side — glm5_2 returns `finish_reason=stop` with 14 content chars, 0 reasoning chars, detected as zombie by R852b logic. NOT config-fixable. CC4101 retries on zombie automatically.

2. **dsv4p_nv ATE (5, all pre-R1658)**: All 5 ATEs at 61-64s, all pre-R1658 deploy (container restarted 22:24 UTC). Post-R1658: 0 dsv4p_nv requests. FASTBREAK=2 is unevaluable.

3. **key_cycle_429s**: Every glm5_2_nv request has single-key 429 cycling (key_cycle_429s=1). No multi-key cascading. KEY=TIER=65 alignment holding.

4. **No rescue paths exercised**: 0 peer-fallback, 0 ms_gw fallback. All 40 requests were direct nv_gw.

5. **Post-R1658**: Container restarted at 22:24 UTC. Only 3 glm5_2_nv requests in the 2h since (2 OK, 1 zombie). Zero dsv4p_nv traffic.

### Container Env (verified)

```
KEY_COOLDOWN_S=65             (R1657: +5s buffer, KEY=TIER iron law)
TIER_COOLDOWN_S=65            (R1657: +5s buffer)
NVU_PEXEC_TIMEOUT_FASTBREAK=2 (R1658: unevaluable)
NVU_EMPTY_200_FASTBREAK=2
NVU_TIER_BUDGET_DSV4P_NV=90   (R1652: 90+72=162<195)
TIER_TIMEOUT_BUDGET_S=195     (R1647)
NVU_PEER_FALLBACK_TIMEOUT=72
NVU_PEER_FB_SKIP_MODELS=""    (R1646)
MIN_OUTBOUND_INTERVAL_S=0     (floor)
NVU_CONNECT_RESERVE_S=0       (floor)
NVU_SSLEOF_RETRY_DELAY_S=0.5  (floor)
NV_INTEGRATE_KEY_COOLDOWN_S=0 (floor)
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
UPSTREAM_TIMEOUT=66
```

### HM2 (for reference)
```
NVU_TIER_BUDGET_DSV4P_NV=70
NVU_PEER_FALLBACK_TIMEOUT=25
TIER_TIMEOUT_BUDGET_S=180
KEY_COOLDOWN_S=25, TIER_COOLDOWN_S=25
```

### Budget Check
- dsv4p_nv: 90+72=162 < 195 ✓
- glm5_2_nv: 120+72=192 < 195 ✓
- KEY+TIER=130 << 195 ✓

## Decision: NOP

All tunable parameters are at floor or optimal. The 46% fail rate is dominated by zombie_empty_completion (NVCF server-side, not config-fixable). The 5 dsv4p ATEs are all pre-R1658. FASTBREAK=2 unevaluable due to zero dsv4p traffic post-R1658. No actionable config change. 铁律:只改HM1不改HM2.
## ⏳ 轮到HM1优化HM2
