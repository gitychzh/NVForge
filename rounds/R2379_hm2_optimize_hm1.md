# R2379 — HM2 Optimizes HM1

## Metadata
- **Round**: R2379
- **Author**: opc2_uname (HM2)
- **Target**: HM1 (opc_uname @ 100.109.153.83)
- **Timestamp**: 2026-07-26 15:16 UTC
- **Status**: NOP — insufficient data

## Observation Window (12min post-R2379 deploy)

### Container State
- nv_gw: Up 12 minutes (healthy), freshly deployed with R2376/2377/2378 params
- TIER_COOLDOWN_S=0, FASTBREAK=4, FAIL_N=5, COOLDOWN=180 all active
- All 5 keys healthy, 5 egress IPs, 5 proxy URLs

### Requests (2 total, both kimi_nv)
| # | Time | Model | Key Path | Result | Duration | Notes |
|---|------|-------|-----------|--------|----------|-------|
| 1 | 15:07:50 | kimi_nv | k3 (1st) | SUCCESS→ZOMBIE | ~27s | content=0, reasoning=639, input=160K |
| 2 | 15:13:49 | kimi_nv | k4→k5→k1 (3rd) | SUCCESS→ZOMBIE | ~105s | k4 conn-error, k5 empty_200, k1 succeed |

### Zombie-Empty Pattern (Both Requests)
```
NV-ZOMBIE-EMPTY (kimi_nv): finish_reason=stop
  content_chars=0, reasoning_chars=639
  input_chars=159631 (>= 5000 threshold)
  content-only mode (R852b), no real tool_calls
  → aborting stream to trigger fallback
```

### Key Observations
1. **NVCF upstream is healthy**: Both requests eventually succeeded (finish_reason=stop). k3 1st attempt; k1 after 2 cycles.
2. **Zombie-empty detection is correct**: content_chars=0 with finish_reason=stop is a genuine zombie — the model produced reasoning but no visible output. These are correctly aborted.
3. **Empty_200 on k5**: NVCF returned 200 Content-Length:0 on stream. Handled correctly by empty_200 cycle logic (KEY_COOLDOWN_S=20, EMPTY_200_FASTBREAK=3).
4. **Connection error on k4**: "Remote end closed connection without response" — NVCF transient. Handled by key cycling.
5. **Very large inputs**: Both requests had ~160K char inputs. May correlate with zombie behavior (model overwhelmed by context).

### Why NOP
- Only 2 requests in 12-minute window. Per zero-traffic NOP discipline (<20 reqs), no parameter change.
- Both failures are upstream NVCF model behavior (content=0 is not a gateway issue).
- Zombie-empty detection is code-level logic (content_chars threshold), not configurable via env vars.
- All gateway mechanisms (key cycling, empty_200 handling, fast-break, tier budget) functioned correctly.
- No glm5_2_nv or dsv4p_nv traffic to evaluate R2376-2378 effectiveness.

### Single Parameter, Iron Law: only HM1
No HM1 changes. No HM2 changes.

## ⏳ 轮到HM1优化HM2