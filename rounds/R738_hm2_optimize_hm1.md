# R738: HM2→HM1 — UPSTREAM_TIMEOUT 54→56 (+2s)

**Date**: 2026-07-05 16:45 UTC  
**Author**: HM2 (opc2_uname)  
**Change**: `UPSTREAM_TIMEOUT: 54→56` (+2s)  
**Compose line**: 483

## Data (6h window, gathered 16:40 UTC)

```
6h: 325req/222OK(68.3%)/103ATE(31.7%)
dsv4p_nv: 236req/137OK(58.1%) — NVCFPexecTimeout max=54,284ms
glm5_2_nv: 89req/85OK(95.5%) — healthy fallback
```

### ATE breakdown
- 82 double-tier (both tiers exhausted, NVCF dual-function)
- 21 single-tier: 19 dsv4p_nv start (avg 52,029ms), 2 glm5_2_nv start

### NVCFPexecTimeout key distribution
```
dsv4p_nv: k0=12 k1=11 k2=19 k3=12 k4=12 — uniform → function-level
           max=54,284ms = UPSTREAM=54 + ~284ms overhead → binding
glm5_2_nv: k0=2 k1=5 k2=7 k3=7 k4=8 — max=57,797ms
```

### Success duration buckets (dsv4p_nv)
```
<=30s: 56   30-35s: 6   35-40s: 9   40-45s: 15
45-50s: 12  50-54s: 4   54-60s: 9   >60s: 26
```
9 successes in 54-60s bucket — all via glm5_2_nv fallback.

### Fallback success
- 69 fallback successes, avg 62,935ms, max 145,104ms
- 153 direct successes, avg 21,944ms

## Rationale

R737 planned this: BUDGET 110→114 (+4s) created headroom for 2 more UPSTREAM +2s rounds.
- NVCFPexecTimeout max=54,284ms at UPSTREAM=54 binding edge
- 9 successes in 54-60s bucket via fallback — direct capture reduces fallback load
- BUDGET=114: 56+56=112, margin=2s (tight but safe for per-tier budget)
- FASTBREAK=1 unchanged
- Single param per round; iron rule: only change HM1 never HM2

## Verification
- YAML: ✓ (yaml.safe_load passed)
- Container: `docker compose up -d nv_gw` → Recreated, Started
- Env: `UPSTREAM_TIMEOUT=56` confirmed in container

## Current config state
```
UPSTREAM_TIMEOUT=56
TIER_TIMEOUT_BUDGET_S=114
NVU_PEXEC_TIMEOUT_FASTBREAK=1
FALLBACK_HEALTH_THRESHOLD=0.10
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=50
NVU_CONNECT_RESERVE_S=0
```

## ⏳ 轮到HM1优化HM2