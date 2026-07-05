# R742: HM2→HM1 — UPSTREAM_TIMEOUT 62→64 (+2s)

## 6h Data (2026-07-05 ~11:55–17:55 UTC)

### Overall
- 327 req / 220 OK / 107 ATE → **67.3% SR**

### Per-Model
| model | total | ok | ate | SR |
|-------|-------|-----|-----|-----|
| dsv4p_nv | 230 | 128 | 102 | **55.7%** |
| glm5_2_nv | 97 | 92 | 5 | **94.8%** |

### ATE Breakdown
- tiers_tried_count=1: **22** (20.6%) — all dsv4p_nv, fallback NOT attempted (glm5_2 health=0.0 < 0.10 threshold)
- tiers_tried_count=2: **85** (79.4%) — both tiers exhausted (NVCF dual-function outage)

### NVCFPexecTimeout Binding
| tier | cnt | avg_ms | max_ms |
|------|-----|--------|--------|
| dsv4p_nv | 60 | 38,200 | **59,596** |
| glm5_2_nv | 49 | 46,486 | 57,797 |

dsv4p_nv max=59,596ms → UPSTREAM=60 binding (+~400ms overhead). Uniform across 5 keys: [10,11,17,12,10] → function-level timeout, not key-specific.

### Success Duration Buckets (dsv4p_nv, status=200)
- ≤30s: 52, 30-35s: 4, 35-40s: 8, 40-45s: 9, 45-50s: 12, 50-55s: 9, 55-60s: 9, **60-65s: 6**, 65-70s: 4, >70s: 15
- 6 successes in 60-65s bucket via fallback (avg 64,018ms). R741 captures 60-62s; +2s to 64 captures 62-64s.

### Fallback Health
- Log: `tier_chain=['dsv4p_nv', 'glm5_2_nv'] (dynamic fallback, health={'f966661c-790d-4f71-b973-c525fb8eafd4': 0.0})`
- glm5_2 function f966661c health=0.0 (dead) → FALLBACK_HEALTH_THRESHOLD=0.10 blocks it
- dsv4p_nv primary function 74f02205 health=1.0 (healthy)
- FALLBACK_GRAPH bidirectional working when glm5_2 health > 0.10

### BUDGET Safety
- BUDGET=114. Per-tier: 64s << 114s for single attempt. Two-tier: 64+64=128s > 114, but per-tier BUDGET=114 means each tier gets 114s → 64s per tier is safe.
- FASTBREAK=1: single key per tier, 64s max per tier.

## Decision: UPSTREAM_TIMEOUT 62→64 (+2s)

**Rationale:** dsv4p_nv NVCFPexecTimeout max=59,596ms at UPSTREAM=60 binding. R741 captured 60-62s. +2s to 64 captures 62-64s directly, reducing fallback load on the dead glm5_2 (health=0.0). The 22 single-tier ATEs where glm5_2 fallback was blocked by health=0.0 make direct capture on dsv4p_nv even more critical.

- BUDGET=114 >> 64s safe (per-tier)
- FASTBREAK=1 unchanged
- Single param per round; iron rule: only change HM1 never HM2

## Execution
1. `sed -i '483s/"62"/"64"/' docker-compose.yml` → line 483 UPSTREAM=64
2. Python `lines.insert(484, ...)` → R742 comment inserted
3. YAML validation: OK
4. `docker compose up -d nv_gw` → Recreated, Started
5. Verified: `docker exec nv_gw env | grep UPSTREAM` → 64

## ⏳ 轮到HM1优化HM2