# R2371: HM2→HM1 — NOP — post-R2369 insufficient evaluative data

## Change
- **Parameter**: None
- **Action**: NOP (No Operation)
- **Location**: `-` (no HM1 config change)
- **Single param delta**: N/A (iron law: only HM1, but no change this round)

## Rationale
- R2369 (HM2→HM1): `KEY_COOLDOWN_S=30→20` deployed at 01:10 UTC.
- Since deployment, only 4 requests entered the nv_gw database (post-01:10 UTC, excluding the deploy-time 01:10 request itself):

| Model | Status | Duration | Notes |
|-------|--------|----------|-------|
| kimi_nv | 200 ✅ | 31,998ms | Post-deploy (01:10:44) |
| glm5_2_nv | 200 ✅ | 50,528ms | Post-restart (01:33:21) |
| glm5_2_nv | 502 ❌ | 51,160ms | **zombie_empty_completion** (01:34:12) — NVCF content-filter empty completion (12 chars, stop), not key-cooldown issue |
| kimi_nv | 200 ✅ | 214,601ms | Post-restart (01:37:59), key_cycle_429s=3 |
| kimi_nv | 200 ✅ | 63,485ms | Post-restart (01:41:58), key_cycle_429s=1 |

- **kimi_nv since R2369**: 3 requests, all 200 success. Zero ATEs. Historically, kimi_nv had `tiers_tried=1+0-attempt` ATE before R2369 (e.g., 00:39: ate 222,632ms, budget ceiling). With only 3 post-deploy requests, there is **insufficient evaluative data** to confirm whether KEY_COOLDOWN_S=20 widened key availability.
- **glm5_2_nv ATE**: The single post-restart ATE was `zombie_empty_completion` at 51s — an NVCF content-filter rejection (input_chars=371,467, output_chars=12, stop). This is an upstream NVCF quality issue, NOT a gateway-budget/key-cooldown issue. No HM1 parameter can fix NVCF content-filter zombies.
- **Post-restart zero-traffic pattern**: After the nv_gw container restart at ~01:21 UTC (19 min before observation), only 4 new requests arrived. Per «Zero-traffic NOP discipline», changing parameters without enough evaluative data risks compounding unmeasured effects.

## Data (4h window, 21:41 UTC → 01:41 UTC)
| Model | Total | Success | Error | SR | Avg Duration | Max Duration |
|-------|-------|---------|-------|----|-------------|-------------|
| kimi_nv | 41 | 35 | 6 | 85.4% | 87,432 ms | 222,632 ms |
| glm5_2_nv | 27 | 20 (21 incl 01:33) | 7 (6 pre-R2371) | 74.1% | 16,504 ms | 51,160 ms |
| dsv4p_nv | 7 | 2 | 5 | 28.6% | 81,024 ms | 210,041 ms |

### Post-R2369 traffic (01:10+)
- kimi_nv: 3 requests, 3 success (100% SR) — too few to validate KEY_COOLDOWN_S=20 effect
- glm5_2_nv: 2 requests, 1 success, 1 zombie (50% SR) — zombie = upstream, not fixable

### Pre-existing patterns (unchanged)
- **dsv4p_nv**: 5/7 ATE in 8h, all upstream (NVCF cluster issues), 0% SR during peak damage (14:00-18:00). Per R2361, budget raised to 240s; still insufficient because NVCF upstream itself is failing. Not HM1-fixable.
- **glm5_2_nv**: Recent ATE at 01:34 is `zombie_empty_completion` (big_input breaker NOT triggered — this was a passthrough request, check: the log shows passthrough zombie, not breaker path). Budget 210s not exhausted (duration 51s vs budget 210s). Not a budget issue.

## Deployment
- No HM1 config change this round.
- `docker exec nv_gw env` unchanged from R2369.

## Iron Law
- No HM1 config change.
- HM2 local not modified.

## ⏳ 轮到HM1优化HM2
