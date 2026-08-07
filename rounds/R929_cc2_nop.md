# R929 cc2 NOP inspection round

Date: 2026-08-07
Type: NOP (no code change) — cc2 primary chain 100% clean, scoped errors 0 rows

## 30min window (injected + live DB confirm)

### caller × model × status
```
cc4101-primary|dsv4f0731_nv|200|113     <- cc2 main nv_gw:40006 (injected)
hermes|dsv4f0731_nv|200|17
hermes|dsv4f0731_nv|502|5               <- injected bad attribution to hermes
```
Live re-pull: `cc4101-primary` 30min = **114/114 all 200, 0 bad** (SR 100%).

### cc4101-primary scoped (cc2's own requests)
```
status | count
  200  |  114
```
Live scoped-error re-pull (caller='cc4101-primary' AND status!=200) = **0 rows**.

### All bad (502) live attribution
```
 caller | error_type            | status | count
 hermes | all_tiers_exhausted   |    502 |   3
 hermes | zombie_empty_completion|    502 |   1
```
All 4 bad = caller=hermes; **0 leak into cc2 primary** (host-separated).

### Fallback (cc_requests 30min)
```
 total | fb
  115  |  0
```
0 fallback triggered.

### per-key tier attempts (dsv4f0731)
NVCFPexecRemoteDisconnected × ~22 + NVCFPexecTimeout × ~5 + 504_nv_gateway_timeout ×2 across keys —
all absorbed by multi-tier round-robin + func_health healthy-fid selection; NOT surfaced as cc2 primary bad.

## Decision: NOP (no code change)

- cc2 primary (cc4101-primary) = **114/114 = 100% SR, 0 bad** (live).
- cc2 primary scoped errors = **0 rows**.
- all bad 100% caller=hermes (caller-column live proof), not in cc2 scope.
- fallback = 0 > nothing to tune.
- no new error class; containers stable.

## Health
- `curl localhost:4101/health` → ok (cc4101, primary=dsv4f0731_nv)
- `curl localhost:40006/health` → ok (nv_gw, passthrough, 5 keys)
- `curl localhost:40066/health` → ok (dsv4p_nv40066)
- containers: cc4101 Up 7h, nv_gw Up 7h, dsv4p_nv40066 Up 2d, nv_gw_stable Up 5d

## Next
- Continue monitoring; next round re-pull 30min window.
- If cc2 primary scoped errors > 0 or SR < 99%, investigate root cause before any change.