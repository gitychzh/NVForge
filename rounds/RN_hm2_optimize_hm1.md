# R741: HM2→HM1 — UPSTREAM_TIMEOUT 60→62 (+2s)

## 6h Data (2026-07-05 ~11:43–17:43 UTC)

### Overall
- 328 req / 225 OK / 103 ATE → **68.6% SR**

### Per-Model
| model | total | ok | SR |
|-------|-------|-----|-----|
| dsv4p_nv | 233 | 135 | **57.9%** |
| glm5_2_nv | 95 | 90 | **94.7%** |

### ATE Breakdown
- tiers_tried_count=1: **19** (18.4%) — all dsv4p_nv (start_tier_idx=1), fallback NOT attempted
- tiers_tried_count=2: **84** (81.6%) — both tiers exhausted (NVCF dual-function)

### Single-tier ATE Detail
All 19 single-tier ATEs: dsv4p_nv → fallback to glm5_2 NOT attempted. 
- 6 pre-restart (04:36-05:23 UTC, ~60s): R740 container had glm5_2 health=0.0 → FALLBACK_HEALTH_THRESHOLD=0.10 killed fallback
- 10 clustered (10:38-10:58 UTC, ~42s): unknown FALLBACK_GRAPH transient disappearance
- 3 clustered (17:03-17:05 UTC, ~56s): post-R740 container, glm5_2 health=0.0

### NVCFPexecTimeout Binding
| tier | cnt | avg_ms | max_ms |
|------|-----|--------|--------|
| dsv4p_nv | 63 | 37,826 | **59,596** |
| glm5_2_nv | 49 | 46,486 | **57,797** |

dsv4p_nv max=59,596ms → UPSTREAM=60 binding (+~400ms overhead). Uniform across 5 keys: [11,12,18,12,10] → function-level timeout, not key-specific.

### Success Duration Buckets (dsv4p_nv)
- ≤20s: 33, 20-30s: 21, 30-40s: 17, 40-50s: 26, **50-60s: 11**, **60-65s: 5**, >65s: 23
- 47/135 dsv4p_nv successes via fallback (avg 61,668ms, max 96,582ms)

### Fallback Health
- Log: `tier_chain=['dsv4p_nv', 'glm5_2_nv'] (dynamic fallback, health={'3b9748d8': 0.0, '74f02205': 1.0})`
- glm5_2 function 3b9748d8 health=0.0 (dead) → FALLBACK_HEALTH_THRESHOLD=0.10 blocks it
- dsv4p_nv function 74f02205 health=1.0 (healthy)
- FALLBACK_GRAPH bidirectional working when glm5_2 health > 0.10

### BUDGET Safety
- BUDGET=114. New: 62+62=124 > 114 → **tight** (no budget for 2-key exhaustion on single tier)
- But FASTBREAK=1 means only 1 key attempt per tier → 62+62=124s for 2-tier ATE, 10s over budget
- Actually: per-tier budget is 114. Single tier: 1 key × 62s = 62s << 114s for fallback. Double tier: each tier gets 114s → 62+62=124s still within 2×114. Safe.

## Decision: UPSTREAM_TIMEOUT 60→62 (+2s)

**Rationale:** dsv4p_nv NVCFPexecTimeout max=59,596ms at UPSTREAM=60 binding edge. +2s captures the 60-62s edge directly, reducing fallback load on dead glm5_2 (health=0.0). The 19 single-tier ATEs where glm5_2 fallback was blocked by health=0.0 make direct capture on dsv4p_nv even more critical.

- BUDGET=114 >> 62s safe (per-tier)
- FASTBREAK=1 unchanged (FASTBREAK=2 would need 2×62=124 > BUDGET=114)
- Single param per round; iron rule: only change HM1 never HM2

## Execution
1. `sed -i '483s/"60"/"62"/' docker-compose.yml` → line 483 UPSTREAM=62
2. Python `lines.insert(484, ...)` → R741 comment inserted
3. YAML validation: OK
4. `docker compose up -d nv_gw` → Recreated, Started
5. Verified: `docker exec nv_gw env | grep UPSTREAM` → 62

## ⏳ 轮到HM1优化HM2