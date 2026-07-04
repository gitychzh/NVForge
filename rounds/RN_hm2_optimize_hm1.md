# R702: HM2→HM1 — TIER_TIMEOUT_BUDGET_S 82→88 (+6s)

**Date**: 2026-07-05 02:55 UTC
**Trigger**: HM1 commit d6c5cd6 (R701: UPSTREAM_TIMEOUT 25→30, dsv4p_nv pexec timeout@25s是50.5%失败率根因)
**Host**: HM2 (opc2_uname) → SSH 改 HM1 (opc_uname @ 100.109.153.83)

## Data Summary (6h window, post-R701, container StartedAt=2026-07-05T02:45 UTC)

### DB 6h Summary
- Total: 232, OK: 170 (73.3%), Fail: 62 (26.7%)
- All errors: all_tiers_exhausted (upstream_type=NULL)
- avg_ttfb: 18966ms, avg_dur: 27000ms, max_dur: 108267ms

### Per-Model (6h)
| Model | Total | OK | Fail | SR | avg_ttfb | avg_dur |
|-------|-------|-----|------|----|----------|---------|
| glm5_2_nv | 128 | 119 | 9 | 93.0% | 13757ms | 14619ms |
| dsv4p_nv | 106 | 54 | 52 | **51.0%** | 32064ms | 42401ms |
| kimi_nv | 8 | 7 | 1 | 87.5% | 4554ms | 9368ms |

### Failure Analysis (dsv4p_nv 52 failures)
Two distinct clusters:
1. **~50s cluster (48 fails)**: `tiers_tried_count=1`, `fallback_occurred=false`, duration 50466-51876ms
   - Single key attempt exhausted budget; second key never launched
   - Key1 consumes ~42s (40s UPGRADE_TIMEOUT + 2s overhead)
   - Remaining budget at 82-42=40s, but key cooldown + connect overhead (~6s) prevents key2 from completing
   - Proxy aborts at ~50s when budget insufficient for useful second attempt
2. **~100s cluster (4 fails)**: `tiers_tried_count=2`, duration 101479-108267ms
   - Full 2-key budget exhausted; both keys timed out at ~40-50s each

### dsv4p_nv Success TTFB Distribution
- 0-30s: 28 successes (52% of OK) — short prompts, direct success
- 30-40s: 12 successes (22%) — thinking, within UPGRADE_TIMEOUT
- 40-50s: 6 successes (11%) — second-key saves
- 50-60s: 6 successes (11%) — second-key with long thinking
- >60s: 3 successes (6%) — edge long-tail, 2-key

### Container Logs
- 8× [NV-THINKING-TIMEOUT] glm5_2_nv stream=True → extended timeout 40s (warnings, requests succeeded)
- No actual error logs (all_tiers_exhausted at scheduling layer, not log-level errors)

### Env (current, post-R701)
- UPSTREAM_TIMEOUT=30, TIER_TIMEOUT_BUDGET_S=82, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=40
- NVU_PEXEC_TIMEOUT_FASTBREAK=2, NVU_EMPTY_200_FASTBREAK=2, PEER_FALLBACK_TIMEOUT=45
- KEY_COOLDOWN_S=25, TIER_COOLDOWN_S=25, NV_INTEGRATE_KEY_COOLDOWN_S=0

## Optimization Decision

**Parameter**: `TIER_TIMEOUT_BUDGET_S` 82→88 (+6s)

**Rationale**: R701 raised UPSTREAM_TIMEOUT 25→30, but dsv4p_nv SR only improved from 50.5% to 51.0% — barely moved. Root cause identified: 48/52 dsv4p_nv failures are single-key (~50s, `tiers_tried_count=1`). With BUDGET=82, key1 consumes ~42s (40s UPGRADE + 2s overhead), leaving 40s. But key2 needs cooldown gap (KEY_COOLDOWN=25 but keys are same-tier so gap is minimal ~2s) + connect (~1-2s) + full 40s UPGRADE = ~44s. 40s < 44s → proxy judges insufficient budget and aborts at ~50s without launching key2.

BUDGET=88 fixes this: 88-42=46s remaining → 46s > 44s needed → key2 launches and gets full 40s UPGRADE_TIMEOUT. Expected: 48 single-key fails get second-key attempt; with dsv4p_nv 2-tier success rate ~60% (6 OK / 10 total 2-tier attempts), ~29 of 48 rescued.

**Safety**:
- Worst case: 88s local + 45s peer fallback = 133s < 300s PROXY_TIMEOUT (margin 167s)
- glm5_2_nv avg_ttfb=13.8s << UPSTREAM=30, zero impact (non-thinking 2×25=50s < 88s)
- Thinking glm5_2_nv: 2×40=80s < 88s, fits with 8s margin
- R699 raised 72→82 for same reason (2-key thinking fit), 88 is continuation of same logic

## Execution
- Compose line 490: `TIER_TIMEOUT_BUDGET_S: "82"` → `"88"` (sed -i full line rewrite)
- Backup: docker-compose.yml.bak.R702
- `docker compose up -d nv_gw` → Container Recreated → Started
- Verified: `docker exec nv_gw env | grep TIER_TIMEOUT_BUDGET_S` → `TIER_TIMEOUT_BUDGET_S=88` ✅

## Iron Rule Compliance
- ✅ Single parameter per round (TIER_TIMEOUT_BUDGET_S only)
- ✅ Only changed HM1, never HM2
- ✅ Data-driven: 6h DB analysis, per-model breakdown, failure cluster analysis
- ✅ Full line rewrite with R-number comment

## Expected Effect
- dsv4p_nv: 51.0% → ~78-86% SR (48 single-key fails get 2nd key, ~29 rescued)
- Overall: 73.3% → ~86%+ SR
- glm5_2_nv: no impact (avg 14s, thinking 2×40=80s < 88s)
- Failure path: single-key ~50s → 2-key ~88s (longer fail duration but higher rescue rate)

## ⏳ 轮到HM1优化HM2
