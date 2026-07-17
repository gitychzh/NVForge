# R1665: HM2→HM1 — PEXEC_TIMEOUT_FASTBREAK 2→3 (+1 key)

## 24h Data (HM1 DB)
- glm5_2_nv: 168 OK / 142 fail (54.2% SR)
  - 126 zombie_empty_completion (88.7% of failures)
  - 16 all_tiers_exhausted
- dsv4p_nv: 18 OK / 17 fail (51.4% SR) — all ATE single-key ~62-64s
- 429 cascading: 285 requests with key_cycle_429s (92% of all requests)
- Tier attempts: pexec_success 284, pexec_429 90 (22.4%), pexec_SSLEOFError 13

## Analysis
R1664 1→2 reduced zombie rate from 79.2% to ~40% (2/5 per hour), proving FASTBREAK increase helps.
But 126 zombies in 24h still means ~40% of glm5_2_nv requests hit zombie — the NVCF function is heavily degraded.
HM2 runs stable at FASTBREAK=3 without zombie cascading.
Budget check: 3 keys × ~9s zombie + UPSTREAM=66s = 93s << BUDGET=120 ✓.

## Change
- Parameter: NVU_PEXEC_TIMEOUT_FASTBREAK
- Old: 2
- New: 3
- Line: 619 in `/opt/cc-infra/docker-compose.yml`
- Container: nv_gw restarted, env verified `NVU_PEXEC_TIMEOUT_FASTBREAK=3` ✓
- Health: `{"status":"ok"}` ✓

## Budget
- glm5_2_nv: 3×9+66=93 < 120 ✓
- dsv4p_nv: FASTBREAK=2 (EMPTY_200_FASTBREAK), pexec path unchanged
- TIER_COOLDOWN_S=65, KEY_COOLDOWN_S=65, TIER_TIMEOUT_BUDGET=195 ✓
- PEER_FALLBACK_TIMEOUT=72 ✓

## Other params unchanged
- BUDGET_GLM5=120, BUDGET_DSV4P=70, PEER_FB_TIMEOUT=72 ✓
- 铁律:只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
