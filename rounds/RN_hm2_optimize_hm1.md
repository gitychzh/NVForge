# R701: HM2→HM1 — UPSTREAM_TIMEOUT 25→30 (+5s)

**Date**: 2026-07-05 02:45 UTC
**Trigger**: HM1 commit de8bfdd (R700: dsv4p_nv→glm5_2_nv 跨model fallback启用)
**Host**: HM2 (opc2_uname) → SSH 改 HM1 (opc_uname @ 100.109.153.83)

## Data Summary (6h window, container StartedAt=2026-07-04T18:44 UTC, pre-R701)

### DB 6h Summary
- Total: 218, OK: 159 (72.9%), Fail: 59 (27.1%)
- All errors: all_tiers_exhausted (upstream_type=NULL)

### Per-Model (6h)
| Model | Total | OK | Fail | SR | avg_ttfb_ok | avg_dur_ok |
|-------|-------|-----|------|----|-------------|------------|
| glm5_2_nv | 111 | 102 | 9 | 91.9% | 14385ms | 14599ms |
| dsv4p_nv | 99 | 50 | 49 | **50.5%** | 30519ms | 31169ms |
| kimi_nv | 8 | 7 | 1 | 87.5% | 4554ms | 10323ms |

### Failure Analysis
- 49/49 dsv4p_nv failures = pexec timeout at 25s UPSTREAM_TIMEOUT ceiling
- dsv4p_nv direct success avg_ttfb=26523ms > 25s — barely making it
- R700 fallback works: 13/13 fallback successes (100%), but 0 failures had fallback_attempted=true (fastbreak killed before reaching fallback)
- avg failure duration: 52510ms (2 × 25s + fastbreak overhead)

### Container Logs
- [NV-TIMEOUT] dsv4p_nv k1/k2/k3 pexec timeout: attempt=~25300ms (at ceiling)
- [NV-PEXEC-FASTBREAK] 2 consecutive timeouts → fast-break
- [NV-FALLBACK-SUCCESS] glm5_2_nv fallback saves requests when given budget
- [NV-ALL-TIERS-FAIL] both dsv4p+glm5_2 timeout when budget exhausted

## Optimization Decision

**Parameter**: `UPSTREAM_TIMEOUT` 25→30 (+5s)

**Rationale**: dsv4p_nv direct success avg_ttfb=26523ms > 25s UPSTREAM_TIMEOUT. Requests in 25-30s range timeout and trigger key cycling/fastbreak. 30s gives 5s headroom, letting more k1 attempts succeed without cycling. glm5_2_nv avg=14385ms << 30s zero impact. TIER_TIMEOUT_BUDGET_S=82 accommodates 2×30=60s with 22s margin. R652 traj 34→31→28→25 was too aggressive for dsv4p_nv (R694 already recognized for thinking timeout). 30 is moderate between 25 and 40.

## Execution
- Compose line 483: `UPSTREAM_TIMEOUT: "25"` → `"30"` (full line rewrite via SCP + Python)
- `docker compose up -d nv_gw` → Container Recreated → Started
- 3-way verified: compose line ✅, docker compose config ✅, container env UPSTREAM_TIMEOUT=30 ✅
- Container healthy, clean startup, StartedAt=2026-07-04T18:45:20Z

## Iron Rule Compliance
- ✅ Single parameter per round (UPSTREAM_TIMEOUT only)
- ✅ Only changed HM1, never HM2
- ✅ Data-driven: 6-layer verification
- ✅ Full line rewrite avoids R688 trajectory corruption

## Expected Effect
- dsv4p_nv: 50.5% → ~70-80% SR
- Overall: 72.9% → ~85%+ SR
- glm5_2_nv: no impact (avg 14s << 30s)

## ⏳ 轮到HM1优化HM2
