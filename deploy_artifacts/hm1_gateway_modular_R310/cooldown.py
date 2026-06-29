#!/usr/bin/env python3
"""429 per-key cooldown state machine.

Extracted from config.py (Reng modularization). Logic is byte-for-byte
equivalent to the original; no behavioral change. Tracks per-(tier,key)
429 cooldown with exponential backoff (capped 30s) and an all-tier
cooldown for the TIER_COOLDOWN_S window when every key in a tier 429s.

Public API (re-exported by config.py for backward compatibility):
  is_key_cooling(tier_model, key_idx) -> bool
  mark_key_cooling(tier_model, key_idx, duration_s=None)
  reset_key429_count(tier_model, key_idx)
  KEY_COOLDOWN_S, TIER_COOLDOWN_S
"""
import os
import threading
import time

KEY_COOLDOWN_S = float(os.environ.get("KEY_COOLDOWN_S", "15.0"))
TIER_COOLDOWN_S = float(os.environ.get("TIER_COOLDOWN_S", "15"))  # R7: when all keys in a tier get 429, mark tier cooling for this duration

_key_cooldown_map = {}
_key_cooldown_lock = threading.Lock()

_key429_count = {}
_key429_lock = threading.Lock()

def is_key_cooling(tier_model, key_idx):
    """Check if a key is in cooldown (recently got 429)."""
    with _key_cooldown_lock:
        cooldown_until = _key_cooldown_map.get((tier_model, key_idx), 0)
        if cooldown_until > time.monotonic():
            return True
        return False

def mark_key_cooling(tier_model, key_idx, duration_s=None):
    """Mark a key as cooling after receiving 429. Exponential backoff, capped at 30s."""
    with _key429_lock:
        _key429_count[(tier_model, key_idx)] = _key429_count.get((tier_model, key_idx), 0) + 1
        consecutive = _key429_count[(tier_model, key_idx)]
    import math
    effective_duration = min(KEY_COOLDOWN_S * (2 ** (consecutive - 1)), 30) if duration_s is None else duration_s
    with _key_cooldown_lock:
        _key_cooldown_map[(tier_model, key_idx)] = time.monotonic() + effective_duration

def reset_key429_count(tier_model, key_idx):
    """Reset consecutive 429 count when a key succeeds."""
    with _key429_lock:
        _key429_count.pop((tier_model, key_idx), None)
