# R828 nv_breaker: 5 consecutive NV failures → next request goes to ms_gw directly

**Date:** 2026-08-05  
**Host:** HM2 (primary deploy)  
**Model:** glm5_2_nv → glm5_2_ms fallback

## Background

2026-08-05 08:38-08:53 UTC window: cloudcli session `2ce97049` stalled for 15 minutes,
triggering R2254 stream-idle watchdog (900000ms) → `interrupt()`. Root cause: req `913ae22b`
(188KB input) hit 5×2 NVCF key attempts, all RemoteDisconnected/SSLEOFError, then 180s
buffer-wait, then recovery retry also failed — total 507s `buffer_exhausted`. cc4101
fallback to ms_gw then timed out at 300s×2 = 600s. Total ~1100s > 900s watchdog.

The existing `nv_breaker.py` (R1771) used time-window semantics (300s window, 5 failures).
But two problems:
1. `NVU_MS_FALLBACK_ENABLED=0` + `NVU_DISABLE_MS_FALLBACK=1` disabled the breaker entirely
   in `execute_request` (`not NVU_DISABLE_MS_FALLBACK` gate at upstream.py:2443).
2. `buffer_stream.py` (the cc4101-primary path) never imported or called `nv_breaker` —
   breaker was only checked/recorded in `handlers.py` execute_request path, not the
   buffer path that handles all cc4101-primary streaming requests.

## Change

### 1. `nv_breaker.py` — consecutive failure counter (R828)

Replaced R1771 time-window deque with simple consecutive counter:
- `record_nv_failure()`: `_consecutive_failures += 1`; trip OPEN at ≥ threshold (5)
- `record_nv_success()`: reset `_consecutive_failures = 0`, close circuit
- `is_ms_fallback_open()`: True when OPEN and within cooldown
- HALF_OPEN: cooldown expired, one probe allowed; success→CLOSED, failure→re-OPEN

### 2. `buffer_stream.py` — breaker check + record (R828)

- **run() start:** if `is_ms_fallback_open()` → skip NVCF entirely, call
  `_try_ms_gw_fallback()` directly. If ms succeeds → return True (ms_fallback served).
  If ms fails → record failure, fall through to NVCF chain (HALF_OPEN probe).
- **BUFFER-LAST-FAIL:** `_nv_breaker_record_failure()` after all retries exhausted.
- **Success verdict:** `_nv_breaker_record_success()` on any successful drain.

### 3. `handlers.py` — record failure on all_keys_exhausted (R828)

In the `_handle_openai_nv` all_keys_exhausted branch, added
`_nv_breaker_record_failure()` + log. Previously only the R1719 anthropic mid-stream
soft-fail path recorded; the direct all_keys_exhausted path did not.

### 4. `docker-compose.yml` — enable ms_gw fallback (R828)

- `NVU_MS_FALLBACK_ENABLED`: 0 → 1
- `NVU_DISABLE_MS_FALLBACK`: 1 → 0

## Param table

| Env | Before | After | Purpose |
|---|---|---|---|
| `NVU_MS_FALLBACK_ENABLED` | 0 | 1 | Enable nv_gw-internal ms_gw fallback |
| `NVU_DISABLE_MS_FALLBACK` | 1 | 0 | Remove the disable override |
| `NVU_MS_FALLBACK_FAIL_THRESHOLD` | 5 | 5 (unchanged) | Consecutive failures to trip OPEN |
| `NVU_MS_FALLBACK_SKIP_S` | 30 | 30 (unchanged) | Cooldown seconds (OPEN→HALF_OPEN) |

## Expected effect

- 5 consecutive NV all_keys_exhausted failures → breaker OPENs
- Next request skips NVCF entirely (~0s vs ~500s wasted), goes straight to ms_gw
- After 30s cooldown, one probe request tries NVCF; success→CLOSED, failure→re-OPEN
- Eliminates the 507s+300s+300s = ~1100s death loop that exceeds cloudcli 900s watchdog

## Verification

- [x] `py_compile` all 3 files pass
- [x] `docker compose up -d nv_gw` recreates container
- [x] `curl /health` returns ok, 5 keys
- [x] E2E cc4101 streaming: `Say hi in one word` → 200, content received
- [x] E2E nv_gw direct: `Say hi` → 200, `Hi! 👋 How can I help you today?`
- [x] Env vars: `NVU_MS_FALLBACK_ENABLED=1`, `NVU_DISABLE_MS_FALLBACK=0`
- [ ] Monitor: next NVCF storm should show `NV-BUFFER-BREAKER-OPEN` log + ms_gw serve
