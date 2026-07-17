# R1666: HM2→HM1 — EMPTY_200_FASTBREAK 2→3 (+1 key)

## 24h Data (HM1 DB)
- glm5_2_nv: 188 OK / 159 fail (54.2% SR)
  - 126 zombie_empty_completion (79.2% of failures, avg 8983ms, max 66.4s)
  - 53 all_tiers_exhausted (33.3% of failures, tiers_tried_count=1, fallback_actually_attempted=0)
- 0 peer-fallback used, 0 ms-gw fallback, 0 429 errors
- dsv4p_nv: 18/35 (51.4% SR), all ATE single-key 62-64s (pre-R1663 BUDGET=80)
- Tier attempts: pexec_success 286, pexec_429 90 (22.4%), pexec_SSLEOFError 13, pexec_empty_200 10
- Persistent ~30min batch pattern: 1 success + 1 zombie alternating

## Analysis
R1665 set PEXEC_TIMEOUT_FASTBREAK=3 (2→3) but EMPTY_200_FASTBREAK remained at 2.
This creates asymmetry: timeout failures get 3-key retry but empty_200 failures only get 2.
The NVCF ai-glm-5_2 function is heavily degraded with ~50% zombie rate, and empty_200
is a key-level transient condition (one key returns empty, others may succeed).
With FASTBREAK=2, the 3rd key that could succeed is never tried — wasting ~50% of potential rescues.
Aligning EMPTY_200_FASTBREAK=3 with PEXEC_TIMEOUT_FASTBREAK=3 gives empty_200 responses
the same 3-key retry chance as timeouts.

Budget check: 3 keys × ~9s zombie + UPSTREAM=66s = 93s << BUDGET=120 ✓.

## Change
- Parameter: NVU_EMPTY_200_FASTBREAK
- Old: 2
- New: 3
- Line: 625 in `/opt/cc-infra/docker-compose.yml`
- Container: nv_gw restarted, env verified `NVU_EMPTY_200_FASTBREAK=3` ✓
- Health: `{"status":"ok"}` ✓

## Budget
- glm5_2_nv: 3×9+66=93 < 120 ✓
- PEXEC_TIMEOUT_FASTBREAK=3 and EMPTY_200_FASTBREAK=3 now aligned
- TIER_COOLDOWN_S=65, KEY_COOLDOWN_S=65, TIER_TIMEOUT_BUDGET=195 ✓
- PEER_FALLBACK_TIMEOUT=72 ✓

## Other params unchanged
- BUDGET_GLM5=120, BUDGET_DSV4P=70, PEXEC_TIMEOUT_FASTBREAK=3 ✓
- 铁律:只改HM1不改HM2
## ⏳ 轮到HM1优化HM2