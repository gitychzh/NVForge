#!/usr/bin/env python3
"""R1648c: nv→ms fallback circuit breaker for nv_gw.

Mirrors cc4101/gateway/circuit.py (R824d). When the NVCF 5key×mode chain for
glm5_2_nv is in a sustained degraded state (all_keys_exhausted storm), every
request waits the full chain budget (~120s for 5 keys) before falling back to
ms_gw — wasting ~120s/req and hammering an already-sick NVCF. A circuit
breaker short-circuits the chain after N consecutive all_keys_exhausted
failures, routing straight to ms_gw for a cooldown, then re-probes nv once.

States:
  CLOSED   — nv chain healthy, tried first (normal flow).
  OPEN     — nv chain degraded, SKIPPED; ms_gw serves directly. Expires after
             NVU_MS_FALLBACK_SKIP_S into HALF_OPEN.
  HALF_OPEN— cooldown expired; is_ms_fallback_open() returns False so the next
             request probes the nv chain once. success → CLOSED, all_keys_exhausted
             → re-OPEN (cooldown re-armed).

Only all_keys_exhausted counts (tier-chain-level failure). Per-key SSL/timeout
errors that the chain recovers from do NOT trip the breaker — those are the
chain's job. client_4xx (request-level) never reaches here.
"""
import threading
import time

from .config import (
    NVU_MS_FALLBACK_FAIL_THRESHOLD,
    NVU_MS_FALLBACK_SKIP_S,
)

_lock = threading.Lock()
_fail_count = 0          # consecutive all_keys_exhausted (resets on a successful nv probe)
_open_until = 0.0        # monotonic deadline; 0 = CLOSED. 0 < expired = HALF_OPEN.


def is_ms_fallback_open():
    """True iff the nv chain should be SKIPPED right now (circuit OPEN, within
    cooldown). Returns False when CLOSED or HALF_OPEN (probe allowed)."""
    with _lock:
        if _open_until == 0.0:
            return False
        return time.monotonic() < _open_until


def record_nv_success():
    """Call when an nv-chain attempt succeeds (chain returned real resp).
    Closes the circuit (CLOSED)."""
    global _fail_count, _open_until
    with _lock:
        _fail_count = 0
        _open_until = 0.0


def record_nv_failure():
    """Call when the nv chain returns all_keys_exhausted (chain-level failure).

    CLOSED: increments; on reaching threshold, opens for NVU_MS_FALLBACK_SKIP_S.
    HALF_OPEN / OPEN: a failure re-arms the cooldown immediately (probe failed)."""
    global _fail_count, _open_until
    with _lock:
        now = time.monotonic()
        _fail_count += 1
        if _open_until != 0.0:
            # already OPEN or HALF_OPEN (expired) — re-arm cooldown
            _open_until = now + NVU_MS_FALLBACK_SKIP_S
            if _fail_count < NVU_MS_FALLBACK_FAIL_THRESHOLD:
                _fail_count = NVU_MS_FALLBACK_FAIL_THRESHOLD
            return
        if _fail_count >= NVU_MS_FALLBACK_FAIL_THRESHOLD:
            _open_until = now + NVU_MS_FALLBACK_SKIP_S


def breaker_state():
    """Debug snapshot: (state, fail_count, seconds_left)."""
    with _lock:
        now = time.monotonic()
        if _open_until == 0.0:
            return "CLOSED", _fail_count, 0
        if now >= _open_until:
            return "HALF_OPEN", _fail_count, 0
        return "OPEN", _fail_count, int(_open_until - now)
