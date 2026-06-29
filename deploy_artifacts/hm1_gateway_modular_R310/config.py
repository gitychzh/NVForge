#!/usr/bin/env python3
"""Configuration for Hermes NV proxy — single-model dsv4p (R274 cleanup).

R274: Removed kimi dead code. The proxy now serves exactly one model —
      deepseek_hm_nv (deepseek-v4-pro) — via NVCF pexec. No tier fallback.
      Prior R50.0 left a two-model (deepseek + kimi) skeleton; this collapses
      it to match the live single-model hermes config and the HM2 side (R263).
      Hermes config has no kimi alias, so kimi_hm_nv was never reachable from
      hermes — this just removes the orphan container-side path.

Chain: Hermes → hm40006 → NVCF pexec (orion-deepseek-v4-pro, ACTIVE)
       → per-key SOCKS5 proxy → mihomo → NV API.

5 keys (k1→k5) round-robin with a persistent RR counter. A request fails
only when all 5 keys are exhausted (429 / empty 200 / timeout) within the
tier budget — there is no model fallback.

Reng (HM1 self-change, authorized): modularized for long-term maintainability.
RR counter state machine → gateway/rr_counter.py; 429 cooldown state machine
→ gateway/cooldown.py; NVCF connection layer → gateway/nvcf_conn.py; pexec
request construction/validation → gateway/pexec.py. This file now holds pure
configuration + throttle_outbound only. Logic is byte-for-byte equivalent;
all downstream `from .config import ...` statements keep working via re-export.
"""
import os
import sys
import time
import threading

# ─── Network ──────────────────────────────────────────────────────────────
LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = int(os.environ.get("LISTEN_PORT", "40006"))
PROXY_TIMEOUT = int(os.environ.get("PROXY_TIMEOUT", "300"))
UPSTREAM_TIMEOUT = int(os.environ.get("UPSTREAM_TIMEOUT", "45"))  # R38.5: 60→45 (NV p95<30s)

# ─── Proxy Role ────────────────────────────────────────────────────────────
# "passthrough" — serves /v1/chat/completions (OpenAI format)
PROXY_ROLE = os.environ.get("PROXY_ROLE", "passthrough")

# ─── Logging ──────────────────────────────────────────────────────────────
LOG_DIR = os.environ.get("LOG_DIR", "/app/logs")

# ─── NVCF pexec configuration (single model: deepseek) ────────────────────
# R274: kimi entry removed — proxy is single-model deepseek_hm_nv.
NVCF_BASE_URL = os.environ.get("NVCF_BASE_URL", "api.nvcf.nvidia.com")
NVCF_PEXEC_MODELS = {
    "deepseek_hm_nv": {
        "function_id": os.environ.get("NVCF_DEEPSEEK_FUNCTION_ID",
                                      "4e533b45-dc54-4e3a-a69a-6ff24e048cb5"),  # orion-deepseek-v4-pro (ACTIVE)
        "strip_params": ["thinking_budget"],  # R277: strip thinking_budget — empty_200 root cause (cf. HM2 glm5.1)
    },
}

# ─── NV API keys for NVCF pexec (all models use same 5 keys) ──────────────
HM_NV_KEYS = []
for i in range(1, 6):
    key = os.environ.get(f"HM_NV_KEY{i}", "")
    if key:
        HM_NV_KEYS.append(key)
HM_NUM_KEYS = len(HM_NV_KEYS)

# ─── Per-key mihomo SOCKS5 proxy URLs ──────────────────────────────────────
# K1→7894, K2→direct, K3→7896, K4→direct, K5→7899  (Rproxy: empty=direct)
HM_NV_PROXY_URLS = []
for i in range(1, 6):
    url = os.environ.get(f"HM_NV_PROXY_URL{i}", "")
    HM_NV_PROXY_URLS.append(url)  # Rproxy: keep ALL slots incl. empty for correct index alignment

if HM_NUM_KEYS < 5:
    print(f"[HM-CONFIG] WARN: only {HM_NUM_KEYS} NV keys configured (expected 5)", file=sys.stderr, flush=True)

# ─── R40 removed: no more LiteLLM glm5.1 HTTP containers ───

# ─── Single-model tier (R274: deepseek only, no fallback) ────────────────
NV_MODEL_TIERS = ["deepseek_hm_nv"]

NV_MODEL_IDS = {
    "deepseek_hm_nv": "deepseek-ai/deepseek-v4-pro",
}

DEFAULT_NV_MODEL = "deepseek_hm_nv"  # R274: single-model dsv4p

# ─── Tier timeout budget ──────────────────────────────────────────────────
TIER_TIMEOUT_BUDGET_S = float(os.environ.get("TIER_TIMEOUT_BUDGET_S", "60"))

# ─── Agent suffix ──────────────────────────────────────────────────────────
AGENT_SUFFIXES = {
    "_hm_nv": {"name": "HermesNV", "format": "openai"},
}
DEFAULT_AGENT_SUFFIX = "_hm_nv"

# ─── Model name mapping (R274: all aliases → deepseek_hm_nv) ─────────────
MODEL_MAP = {
    "deepseek_hm_nv": "deepseek_hm_nv",
    "deepseek_nv": "deepseek_hm_nv",
    "deepseek": "deepseek_hm_nv",
    "deepseek-v4-pro": "deepseek_hm_nv",
    "deepseek-ai/deepseek-v4-pro": "deepseek_hm_nv",
    "deepseek_hm": "deepseek_hm_nv",
    "dsv4p": "deepseek_hm_nv",
}

def detect_nv_model(model_id: str) -> str:
    """Map a frontend model name to the internal NV model key.

    Returns: deepseek_hm_nv (the only supported model). Falls back to
    DEFAULT_NV_MODEL for unrecognized names.
    """
    mapped = MODEL_MAP.get(model_id, None)
    if mapped and mapped in NV_MODEL_IDS:
        return mapped
    return DEFAULT_NV_MODEL

def get_tier_index(mapped_model: str) -> int:
    """Get the tier index for a mapped model."""
    try:
        return NV_MODEL_TIERS.index(mapped_model)
    except ValueError:
        return 0

# ─── Token estimation ──────────────────────────────────────────────────────
CHARS_PER_TOKEN_ESTIMATE = float(os.environ.get("CHARS_PER_TOKEN_ESTIMATE", "3.0"))

# ─── Outbound throttle ──────────────────────────────────────────────────────
MIN_OUTBOUND_INTERVAL_S = float(os.environ.get("MIN_OUTBOUND_INTERVAL_S", "1.5"))
_outbound_last_sent = 0.0
_outbound_throttle_lock = threading.Lock()

def throttle_outbound():
    """Enforce MIN_OUTBOUND_INTERVAL_S between consecutive outbound requests."""
    if MIN_OUTBOUND_INTERVAL_S <= 0:
        return
    global _outbound_last_sent
    with _outbound_throttle_lock:
        now = time.monotonic()
        elapsed = now - _outbound_last_sent
        wait = MIN_OUTBOUND_INTERVAL_S - elapsed
        if wait > 0:
            time.sleep(wait)
            now = time.monotonic()
        _outbound_last_sent = now

# ─── Context window (R274: deepseek only) ────────────────────────────────
MODEL_INPUT_TOKEN_SAFETY = {
    "deepseek_hm_nv": 131072,
}
DEFAULT_CONTEXT_FALLBACK = 131072

# ─── Thread locks for logging ────────────────────────────────────────────
_log_lock = threading.Lock()
_metrics_lock = threading.Lock()
_error_detail_lock = threading.Lock()

# ─── Re-exports for backward compatibility (Reng modularization) ──────────
# These state machines were extracted to their own modules. Re-export here so
# all existing `from .config import _next_hm_nv_key / is_key_cooling / ...`
# statements in handlers.py and upstream.py keep working unchanged.
# NOTE: imported at end-of-file so LOG_DIR / HM_NUM_KEYS (needed by rr_counter)
# are already defined when the import resolves.
from .rr_counter import (  # noqa: E402
    _next_hm_nv_key,
    _save_rr_counter,
)
from .cooldown import (  # noqa: E402
    is_key_cooling,
    mark_key_cooling,
    reset_key429_count,
    KEY_COOLDOWN_S,
    TIER_COOLDOWN_S,
)
