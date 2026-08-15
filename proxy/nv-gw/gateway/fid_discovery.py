#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FID Auto-Discovery for dsv4f_nv (R-dsv4f-dynamic, 2026-08-04).

Background thread that periodically queries NVCF functions list API,
discovers new ACTIVE function IDs for deepseek-v4-flash, probes them,
and replaces the in-memory config if a new FID is healthy.

Design:
- Thread-safe: uses threading.Lock to protect config replacement
- Non-persistent: restart resets to config.py defaults (cold start)
- Non-blocking: failures are silently logged, no impact on request path
- Safety: only replaces NVCF_PEXEC_MODELS["dsv4f_nv"]["function_ids"][0] in memory
  (does not touch the config.py file on disk)
- func_health automatically tracks new FID health after replacement

Env vars:
  NVU_FID_DISCOVERY_ENABLED   = "1" to enable (default: off)
  NVU_FID_DISCOVERY_INTERVAL_S = seconds between discovery cycles (default: 1800=30min)
  NVU_FID_DISCOVERY_MODEL     = model key to target (default: "dsv4f_nv")
  NVU_FID_DISCOVERY_NAME_MATCH = name substring to match (default: "deepseek-v4-flash")
  NVU_FID_DISCOVERY_PROBE_KEY  = which key to use for probing (1-5, default: 1)
"""

import os
import sys
import json
import http.client
import ssl
import socket
import threading
import time
import subprocess
import re

# Lazy imports (avoid circular import at module load)
_discovery_thread = None
_discovery_lock = threading.Lock()
_stop_event = threading.Event()

DISCOVERY_ENABLED = os.environ.get("NVU_FID_DISCOVERY_ENABLED", "0") == "1"
DISCOVERY_INTERVAL_S = int(os.environ.get("NVU_FID_DISCOVERY_INTERVAL_S", "1800"))
DISCOVERY_MODEL = os.environ.get("NVU_FID_DISCOVERY_MODEL", "dsv4f_nv")
DISCOVERY_NAME_MATCH = os.environ.get("NVU_FID_DISCOVERY_NAME_MATCH", "deepseek-v4-flash")
DISCOVERY_PROBE_KEY = int(os.environ.get("NVU_FID_DISCOVERY_PROBE_KEY", "1")) - 1  # 0-based
DISCOVERY_PROBE_TIMEOUT = 15
DISCOVERY_PROBE_HOST = os.environ.get("NVCF_BASE_URL", "api.nvcf.nvidia.com")


def _log(tag, msg):
    """Lazy log through gateway logger."""
    try:
        from .logger import _log
        _log(tag, msg)
    except Exception:
        print(f"[{tag}] {msg}", file=sys.stderr, flush=True)


def _get_keys():
    """Get NV API keys from the gateway's in-memory key list."""
    try:
        from . import upstream
        return upstream.NVU_KEYS
    except Exception:
        return []


def _get_current_fid():
    """Get the current primary FID for the target model from in-memory config."""
    try:
        from . import config
        model_cfg = config.NVCF_PEXEC_MODELS.get(DISCOVERY_MODEL, {})
        fids = model_cfg.get("function_ids", [])
        return fids[0] if fids else None
    except Exception:
        return None


def _set_current_fid(new_fid):
    """Replace the primary FID in the in-memory config (not on disk).

    Only replaces function_ids[0]; preserves any secondary FIDs.
    Thread-safe via the discovery lock.
    """
    with _discovery_lock:
        try:
            from . import config
            model_cfg = config.NVCF_PEXEC_MODELS.get(DISCOVERY_MODEL, {})
            fids = model_cfg.get("function_ids", [])
            if fids:
                old = fids[0]
                if old == new_fid:
                    return False  # no change
                fids[0] = new_fid
                # Also update the convenience "function_id" field
                model_cfg["function_id"] = new_fid
                _log("NV-FID-DISCOVERY-REPLACE",
                     f"Replaced FID for {DISCOVERY_MODEL}: {old[:12]}... → {new_fid[:12]}... (in-memory)")
                return True
            else:
                model_cfg["function_ids"] = [new_fid]
                model_cfg["function_id"] = new_fid
                _log("NV-FID-DISCOVERY-REPLACE",
                     f"Set new FID for {DISCOVERY_MODEL}: {new_fid[:12]}... (was empty, in-memory)")
                return True
        except Exception as e:
            _log("NV-FID-DISCOVERY-ERR", f"Failed to replace FID: {e}")
            return False


def _get_probe_proxy_url():
    """Get the socks5 proxy URL for the discovery probe key (via nvcf_conn proxy path).

    R1253: discovery probe must traverse the per-key mihomo US egress like the real request
    path does — NVCF rejects direct (no-proxy) connections. Falls back to empty (direct) when
    unavailable; caller treats empty as acceptable only as a last resort.
    """
    try:
        from .config import NVU_PROXY_URLS
        if 0 <= DISCOVERY_PROBE_KEY < len(NVU_PROXY_URLS):
            return NVU_PROXY_URLS[DISCOVERY_PROBE_KEY]
    except Exception:
        pass
    return ""


def _probe_model():
    """Resolve the pexec body model name for the discovery target model.

    R1253: uses NV_MODEL_IDS[DISCOVERY_MODEL] (e.g. glm5_2_nv → z-ai/glm-5.2) instead of
    the old hardcoded dsv4f model which made glm discovery probes 404.
    """
    try:
        from .config import NV_MODEL_IDS
        m = NV_MODEL_IDS.get(DISCOVERY_MODEL)
        if m:
            return m
    except Exception:
        pass
    return "deepseek-ai/deepseek-v4-flash"  # legacy default (dsv4f_nv)


def _make_probe_conn():
    """Build an HTTPSConnection for the probe (socks5-proxied when possible).

    Reuses nvcf_conn._make_nvcf_proxy_conn so the probe shares the same SOCKS5 → SSL → NVCF
    egress as real requests. Empty proxy falls back to direct (legacy behavior).
    """
    from .nvcf_conn import _make_nvcf_proxy_conn
    return _make_nvcf_proxy_conn(_get_probe_proxy_url(), DISCOVERY_PROBE_HOST,
                                 timeout=DISCOVERY_PROBE_TIMEOUT)


def _list_functions(key):
    """Query NVCF functions list API. Returns list of function dicts or empty list on error."""
    try:
        conn = _make_probe_conn()
        conn.request("GET", "/v2/nvcf/functions",
                     headers={"Authorization": f"Bearer {key}", "Accept": "application/json"})
        resp = conn.getresponse()
        data = resp.read()
        conn.close()
        if resp.status == 200:
            j = json.loads(data)
            return j.get("functions", [])
        else:
            _log("NV-FID-DISCOVERY-LIST-ERR",
                 f"Functions list API returned {resp.status}: {data[:200].decode(errors='replace')}")
            return []
    except Exception as e:
        _log("NV-FID-DISCOVERY-LIST-ERR", f"Functions list API failed: {e}")
        return []


def _probe_fid(key, fid):
    """Probe a single FID via pexec. Returns True if 200 and non-empty content."""
    try:
        conn = _make_probe_conn()
        body = json.dumps({
            "model": _probe_model(),
            "messages": [{"role": "user", "content": "Hi"}],
            "max_tokens": 8,
            "stream": False,
            "temperature": 0.7,
        })
        conn.request("POST", f"/v2/nvcf/pexec/functions/{fid}",
                     body=body,
                     headers={
                         "Authorization": f"Bearer {key}",
                         "Content-Type": "application/json",
                         "Accept": "application/json",
                     })
        resp = conn.getresponse()
        data = resp.read()
        conn.close()
        if resp.status == 200:
            j = json.loads(data)
            choices = j.get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content", "")
                if content:
                    _log("NV-FID-DISCOVERY-PROBE-OK",
                         f"FID {fid[:12]}... probe SUCCESS (200, content={content[:20]!r})")
                    return True
                else:
                    _log("NV-FID-DISCOVERY-PROBE-EMPTY",
                         f"FID {fid[:12]}... probe 200 but empty content")
                    return False
        else:
            err = data[:100].decode(errors="replace")
            _log("NV-FID-DISCOVERY-PROBE-FAIL",
                 f"FID {fid[:12]}... probe {resp.status}: {err}")
            return False
    except Exception as e:
        _log("NV-FID-DISCOVERY-PROBE-ERR", f"FID {fid[:12]}... probe exception: {e}")
        return False


def _discover_cycle():
    """Run one discovery cycle: list functions → filter → probe → replace if better."""
    keys = _get_keys()
    if not keys or DISCOVERY_PROBE_KEY >= len(keys):
        _log("NV-FID-DISCOVERY", f"No keys available for discovery (need key {DISCOVERY_PROBE_KEY+1})")
        return

    probe_key = keys[DISCOVERY_PROBE_KEY]
    current_fid = _get_current_fid()

    _log("NV-FID-DISCOVERY", f"Starting discovery cycle: model={DISCOVERY_MODEL} "
                              f"current_fid={current_fid[:12] if current_fid else 'none'}... "
                              f"match={DISCOVERY_NAME_MATCH}")

    # Step 1: List all functions
    functions = _list_functions(probe_key)
    if not functions:
        _log("NV-FID-DISCOVERY", "No functions returned (API error or empty)")
        return

    _log("NV-FID-DISCOVERY", f"Functions list returned {len(functions)} functions")

    # Step 2: Filter for deepseek-v4-flash + ACTIVE
    candidates = []
    for f in functions:
        name = f.get("name", "")
        status = f.get("status", "")
        fid = f.get("id", "")
        if DISCOVERY_NAME_MATCH in name and status == "ACTIVE":
            candidates.append((fid, name))
            _log("NV-FID-DISCOVERY-CANDIDATE",
                 f"Found ACTIVE candidate: {fid[:12]}... name={name}")

    if not candidates:
        _log("NV-FID-DISCOVERY", f"No ACTIVE candidates matching '{DISCOVERY_NAME_MATCH}'")
        return

    # Step 3: Check if current FID is still ACTIVE
    current_active = False
    for fid, name in candidates:
        if current_fid and fid == current_fid:
            current_active = True
            _log("NV-FID-DISCOVERY", f"Current FID {current_fid[:12]}... still ACTIVE")
            break

    if current_active:
        # Current FID still works — check if any new candidates are also healthy
        # but don't replace unless current is failing (func_health will handle that)
        # Just probe new candidates that are different from current
        new_candidates = [(fid, name) for fid, name in candidates if fid != current_fid]
        if not new_candidates:
            _log("NV-FID-DISCOVERY", "Current FID active, no new candidates. Done.")
            return

        # Probe new candidates; if any succeeds AND current is unhealthy, switch
        for fid, name in new_candidates:
            if _probe_fid(probe_key, fid):
                # New FID works! Check if current is unhealthy
                try:
                    from . import func_health
                    if not func_health.is_healthy(current_fid):
                        _log("NV-FID-DISCOVERY",
                             f"Current FID unhealthy, switching to new healthy FID {fid[:12]}...")
                        _set_current_fid(fid)
                        return
                    else:
                        _log("NV-FID-DISCOVERY",
                             f"New FID {fid[:12]}... works but current still healthy, keeping current")
                except Exception:
                    # If func_health check fails, don't switch (conservative)
                    _log("NV-FID-DISCOVERY",
                         f"New FID {fid[:12]}... works, can't check current health, keeping current")
                return  # Only probe first successful new candidate
        _log("NV-FID-DISCOVERY", "No new candidates passed probe. Keeping current.")
        return

    # Step 4: Current FID is NOT active (or not in list) — must replace
    _log("NV-FID-DISCOVERY",
         f"Current FID {current_fid[:12] if current_fid else 'none'}... NOT ACTIVE, searching for replacement")

    for fid, name in candidates:
        if _probe_fid(probe_key, fid):
            _log("NV-FID-DISCOVERY",
                 f"Found working replacement FID {fid[:12]}... (name={name})")
            _set_current_fid(fid)
            return

    _log("NV-FID-DISCOVERY", "No replacement FID found (all candidates failed probe)")


def _discovery_loop():
    """Background discovery loop."""
    _log("NV-FID-DISCOVERY-START",
         f"FID discovery thread started: interval={DISCOVERY_INTERVAL_S}s "
         f"model={DISCOVERY_MODEL} match={DISCOVERY_NAME_MATCH}")

    # Run first cycle immediately on startup
    while not _stop_event.is_set():
        try:
            _discover_cycle()
        except Exception as e:
            _log("NV-FID-DISCOVERY-ERR", f"Discovery cycle exception: {e}")

        # Wait for next cycle
        _stop_event.wait(DISCOVERY_INTERVAL_S)


def start():
    """Start the FID discovery background thread."""
    global _discovery_thread
    if not DISCOVERY_ENABLED:
        return
    if _discovery_thread and _discovery_thread.is_alive():
        return
    _stop_event.clear()
    _discovery_thread = threading.Thread(target=_discovery_loop, daemon=True, name="fid-discovery")
    _discovery_thread.start()
    _log("NV-FID-DISCOVERY-INIT", f"FID discovery thread launched (interval={DISCOVERY_INTERVAL_S}s)")


def stop():
    """Stop the FID discovery background thread."""
    _stop_event.set()
    if _discovery_thread:
        _discovery_thread.join(timeout=5)


def snapshot():
    """Return current discovery state for /health endpoint."""
    return {
        "enabled": DISCOVERY_ENABLED,
        "interval_s": DISCOVERY_INTERVAL_S,
        "model": DISCOVERY_MODEL,
        "name_match": DISCOVERY_NAME_MATCH,
        "current_fid": (_get_current_fid() or "")[:12] + "...",
        "thread_alive": _discovery_thread.is_alive() if _discovery_thread else False,
    }
