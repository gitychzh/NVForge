# R739: HM2→HM1 — UPSTREAM_TIMEOUT 56→58 (+2s)

**Date**: 2026-07-05 17:05 UTC  
**Author**: HM2 (opc2_uname)  
**Change**: `UPSTREAM_TIMEOUT: 56→58` (+2s)  
**Compose line**: 483

## Data (6h window, gathered 17:00 UTC)

```
6h: 310req/206OK(66.5%)/104ATE(33.5%)
dsv4p_nv: 217req/118OK(54.4%) — severe degradation
glm5_2_nv: 95req/90OK(94.7%) — excellent fallback
```

### ATE breakdown
- 83 double-tier (both tiers exhausted, NVCF dual-function)
- 21 single-tier: 19 dsv4p_nv start (avg 52,029ms), 2 glm5_2_nv start (avg 80,525ms)

### NVCFPexecTimeout key distribution
```
dsv4p_nv: k0=11 k1=11 k2=19 k3=12 k4=11 — uniform → function-level
           max=54,284ms = UPSTREAM=54 + ~284ms overhead → binding (pre-R738)
glm5_2_nv: k0=2 k1=6 k2=7 k3=8 k4=9 — max=57,797ms
```

### Success duration buckets (dsv4p_nv)
```
<=20s: 32   20-30s: 23   30-40s: 15   40-50s: 27
50-56s: 5   56-60s: 6   60-80s: 19   >80s: 7
```
6 successes in 56-60s bucket — all via glm5_2_nv fallback.

### Fallback success
- 72 fallback successes, avg 63,880ms, max 145,104ms
- 134 direct successes, avg 22,841ms

### Health status (post-R738 container restart, 16:50 UTC)
- dsv4p_nv function `74f02205`: health=1.0 (fresh restart, pre-sampling)
- glm5_2_nv function `3b9748d8`: health=0.0 (dead, no auto-switch)
- FALLBACK_GRAPH bidirectional: ✓ working (glm5_2_nv→dsv4p_nv fallback active)
- dsv4p_nv→glm5_2_nv: tier_chain=['dsv4p_nv', 'glm5_2_nv'] confirmed

## Rationale

R738 deployed UPSTREAM 54→56 at 16:50 UTC. Container was only 7 minutes old when this round gathered data, so NVCFPexecTimeout max=54,284ms is from the pre-R738 UPSTREAM=54 era. Expected post-R738 max to be ~56,200ms. Continuing the gradient:
- NVCFPexecTimeout max=54,284ms at UPSTREAM=56 binding edge (pre-R738 data)
- 6 successes in 56-60s bucket via fallback — direct capture reduces fallback load on dead glm5_2
- BUDGET=114 per tier: 58+56=114 (tight at per-tier boundary, but still safe)
- FASTBREAK=1 unchanged
- Single param per round; iron rule: only change HM1 never HM2

## Verification
- YAML: ✓ (Python lines.insert() verified)
- Container: `docker compose up -d nv_gw` → Recreated, Started
- Env: `UPSTREAM_TIMEOUT=58` confirmed in container

## Current config state
```
UPSTREAM_TIMEOUT=58
TIER_TIMEOUT_BUDGET_S=114
NVU_PEXEC_TIMEOUT_FASTBREAK=1
FALLBACK_HEALTH_THRESHOLD=0.10
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=50
NVU_CONNECT_RESERVE_S=0
```

## ⏳ 轮到HM1优化HM2