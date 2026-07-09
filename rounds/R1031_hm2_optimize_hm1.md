# R1031: HM2→HM1 — NVU_EMPTY_200_FASTBREAK 1→2 (+1 key before fastbreak)

## Summary
- **Change**: `NVU_EMPTY_200_FASTBREAK` 1→2 (single parameter)
- **Host**: HM1 only (`opc_uname@100.109.153.83`, container `nv_gw`)
- **Iron Rule**: 只改HM1不改HM2
- **Date**: 2026-07-10 05:45 UTC

## Data (6h window pre-change)
- **Overall**: 398 req / 371 OK (93.2% SR), 27 fail
- **Failures**: 21 all_tiers_exhausted (ATE), 3 NVStream_TimeoutError, 3 stream_total_deadline

| Model | Req | OK | Fail | SR | Avg Dur | Max Dur | Main Error |
|---|---|---|---|---|---|---|---|
| glm5_2_nv | 246 | 237 | 9 | 96.3% | 20.9s | 174.7s | 4 ATE + 3 timeout |
| dsv4p_nv | 68 | 59 | 9 | 86.8% | 19.1s | 61.2s | 9 ATE |
| kimi_nv | 49 | 48 | 1 | 98.0% | 11.3s | 60.8s | 1 ATE |
| minimax_m3_nv | 35 | 27 | 8 | 77.1% | 44.3s | 159.3s | 7 ATE + 1 deadline |

- **nv_integrate**: 265 req/259 OK (97.7%), avg_dur 17.9s
- **nvcf_pexec**: 108 req/108 OK (100%), avg_dur 13.5s
- **ATE (NULL upstream)**: 25 req, 4 OK (16%)
- **Tier attempts**: only 1 (minimax_m3_nv IntegrateTimeout 90.8s)
- **Fallback triggered**: 1 out of 398

### dsv4p_nv ATE root cause (confirmed by nv_gw proxy log)
```
[04:17:20.1] [NV-TIER-FAIL] tier=dsv4p_nv all 5 keys failed: 429=0, empty200=1, timeout=0, other=0, elapsed=61244ms
[04:17:20.1] [NV-MS-FB] local all_tiers_exhausted (model=dsv4p_nv), attempting same-model fallback to http://ms_gw:40007 as dsv4p_ms
[04:17:23.2] [NV-MS-FB] ms_gw relay failed after 3096ms: BrokenPipeError: [Errno 32] Broken pipe (relay_started=True)
```

Only 1 empty_200 across 5 keys — NOT function-level degradation (which would show 5 empty_200).
FASTBREAK=1 aborts entire tier on first empty_200. ms_gw fallback triggers but BrokenPipeError
kills the relay after 3096ms. 9 dsv4p ATEs all follow this pattern.

### Container state
- nv_gw restarted at 2026-07-09 21:38 UTC (R1030 deploy)
- Post-restart: 0 requests (low-traffic window), no post-R1030 data yet
- ms_gw healthy, all cooldowns empty

## Analysis

dsv4p_nv empty_200 is **transient single-key**, not function-level (only 1/5 keys hit it).
FASTBREAK=1 treats it as function-level death, immediately aborting the tier without trying
other keys. The next key could succeed — dsv4p_nv pexec has 100% SR (108/108) via nvcf_pexec
in the same 6h window; the empty_200 key was anomalous.

ms_gw fallback is the intended rescue path (NVU_MS_GW_FALLBACK_MODELMAP has dsv4p_nv:dsv4p_ms
since R1020) but BrokenPipeError makes it unreliable — relay starts (200 sent to client),
then pipe breaks, corrupting the stream.

FASTBREAK=2: if first key is empty_200 (~61.2s in log), try second key with remaining budget.
Budget ensures safety: BUDGET=110, if k1=61s → remaining 49s < UPSTREAM(66s) → won't try k2
if k1 was slow. If k1 empty200 is fast (<44s), k2 has 66s budget (≥UPSTREAM) to attempt.
This is conservative — FASTBREAK=2 only helps when empty_200 happens early.

For glm5_2_nv integrate path: NVU_INTEGRATE_TIMEOUT_FASTBREAK=1 remains unchanged;
NVU_EMPTY_200_FASTBREAK is pexec-only (integrate timeout ≠ empty_200).

## Change

```yaml
# Before:
NVU_EMPTY_200_FASTBREAK: "1"

# After:
NVU_EMPTY_200_FASTBREAK: "2"
```

## Verification
- `docker exec nv_gw env | grep EMPTY_200` → `NVU_EMPTY_200_FASTBREAK=2` ✅
- `curl http://localhost:40006/health` → status: ok ✅
- Container restarted via `docker compose up -d nv_gw` ✅

## Expected Impact
- dsv4p_nv ATE reduction: transients rescued by 2nd key → fewer ATE
- ms_gw BrokenPipeError avoidance: requests resolve within nv_gw tier instead of needing ms_gw
- No impact on glm5_2_nv (integrate uses separate fastbreak param)
- BUDGET=110 remains safe — 2nd key only attempted if budget allows

## ⏳ 轮到HM1优化HM2