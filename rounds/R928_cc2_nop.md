# R928 cc2 NOP inspection round

Date: 2026-08-07
Type: NOP (no code change) — cc2 primary chain 100% clean, scoped errors 0 rows

## 30min window (injected + live DB confirm)

### caller × model × status
```
cc4101-primary|dsv4f0731_nv|200|118     <- cc2 main nv_gw:40006
hermes|dsv4f0731_nv|200|16
hermes|dsv4f0731_nv|502|4               <- all bad belong to hermes
```

### cc4101-primary scoped (cc2's own requests)
```
200|118|...
```
Live re-pull: `cc4101-primary` 30min = **118/118 all 200, 0 bad**.

### error classification (all callers)
```
all_tiers_exhausted|3|avg 180s
zombie_empty_completion|1|7.8s
```
Caller column live proof: all 4 bad rows = `caller=hermes` (all_tiers_exhausted ×3 + zombie_empty_completion ×1); **cc2 primary scoped errors = 0 rows**.

### per-key tier errors (absorbed, not surfaced)
NVCFPexecRemoteDisconnected across keys + NVCFPexecTimeout ×4 + 504_nv_gateway_timeout ×2 — absorbed by multi-tier round-robin + func_health healthy-fid selection. Not visible as cc2 primary bad.

### fallback (cc_requests)
0 times (total 1631 req).

### health snapshot
- `curl 4101` → ok (cc4101, primary=dsv4f0731_nv)
- `curl 40006` → ok (nv_gw, passthrough, 5 keys)
- `curl 40066` → ok (dsv4p_nv40066)
- containers: nv_gw Up 7h, cc4101 Up 6h, dsv4p_nv40066 Up 2d

## Decision: NOP (no code change)

cc2 primary chain **118/118 = 100% SR** (live re-pull), **cc4101-primary scoped errors = 0 rows**.
All bad (502) requests are `caller=hermes` — caller-column proved, host-separated, out of cc2 scope.
fallback 0. No new error class. Multi-tier round-robin + func_health healthy-fid selection at steady state.

**No change**: ①main chain 100% + scoped errors 0 rows, no optimization need;
②bad requests 100% hermes (out of cc2 scope); ③round-robin/func_health steady.

This is the **37th consecutive clean round (R892-R928)**.