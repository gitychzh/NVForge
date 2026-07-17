# R1662: HM2→HM1 — BUDGET_DSV4P 90→80 (-10s)

## 6h Summary
- **Total**: 42 req, 23 OK (54.8%), 19 fail (45.2%)
- **glm5_2_nv**: 16 OK, 14 zombie_empty_completion (53.3% fail) — model-level NVCF issue, not config-fixable
- **dsv4p_nv**: 7 OK, 5 all_tiers_exhausted (41.7% fail) — all 5 ATE in a 5-min burst at 18:00 UTC
- **Zero fallback**: fallback_occurred=false for ALL requests
- **Zero peer-fallback**: no peer-fb attempts in 1000+ log lines

## dsv4p_nv ATE Analysis
All 5 dsv4p ATE: single-key (tiers_tried=1), durations 61.5-64.3s, all during 18:00-18:05 UTC burst. FASTBREAK=1 (R1661) means only 1 key attempted. BUDGET=90 allows k1 to consume ~62s, remaining 28s wasted. k2 never starts because 28s < UPSTREAM=66.

## glm5_2_nv Zombie Analysis
14 zombie_empty_completion, pattern: content_chars=14 < 50, input_chars >= 5000. R852b zombie detector triggers on model-level empty responses. Not config-fixable; NVCF ai-glm-5_2 function issue.

## Peer-Fallback Status
PEER_FB_SKIP_MODELS="" (R1646 cleared), PEER_FALLBACK_TIMEOUT=72 ≥ HM2 BUDGET=70+2 ✓, code path confirmed in handlers.py. But no dsv4p ATE since R1661 restart to test peer-fb. The 5 ATE at 18:00 UTC were pre-R1661 restart.

## ms_gw Fallback Gap
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms — dsv4p_nv NOT in the map. ms_gw has dsv4p_ms available but nv_gw code doesn't map dsv4p_nv → dsv4p_ms. This is a code-level gap (current handlers.py doesn't import MS_GW_FALLBACK_MODELMAP). Peer-fallback is the only rescue path for dsv4p_nv.

## Optimization
**NVU_TIER_BUDGET_DSV4P_NV: 90 → 80** (-10s)

Rationale:
- FASTBREAK=1: only 1 key attempted per tier. BUDGET=90 allocates 24s beyond UPSTREAM=66 that is never used.
- 80s: k1 gets full UPSTREAM=66 + 14s budget headroom. Still generous for 62s actual max.
- Budget check: 80 + 72 = 152 < 195 ✓ (peer-fb safe)
- Saves 10s/ATE on dsv4p_nv failure path, releases 10s for peer-fallback to start sooner.
- Single param; iron rule: only change HM1 never HM2.

## Verification
- Container `nv_gw` restarted, health OK
- `docker exec nv_gw env` confirms: NVU_TIER_BUDGET_DSV4P_NV=80 ✓
- All other params unchanged: UPSTREAM=66, BUDGET_GLM5_2=120, PEER_FALLBACK=72, KEY_COOLDOWN=65, TIER_COOLDOWN=65, FASTBREAK_PEXEC=1, EMPTY_200_FASTBREAK=2, SSLEOF=0.5, CONNECT_RESERVE=0, MIN_OUTBOUND=0
- 铁律: 只改HM1不改HM2 ✓
## ⏳ 轮到HM1优化HM2
