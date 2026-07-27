#!/usr/bin/env python3
"""R-rebuild: 全局 KeyManager — per-key 健康状态管理。

替代 cooldown.py 的简单 per-key 冷却，提供：
  - 429 长冷却（递增式，120s→600s，匹配实际 20-50min streak）
  - 连接异常短冷却（30s，连续 3 次→120s 长冷却）
  - 成功时重置该 key 所有计数
  - get_healthy_keys() 返回当前可用 key 列表

Phase 1: 作为 cooldown.py 底层实现，不改调用方逻辑。
Phase 2+: 调用方直接使用 KeyManager API。
"""

import os
import threading
import time

# ─── 配置 ───
_429_BASE_COOLDOWN = float(os.environ.get("NVU_KEYMGR_429_BASE_COOLDOWN", "120"))
_429_MAX_COOLDOWN = float(os.environ.get("NVU_KEYMGR_429_MAX_COOLDOWN", "600"))
_CONN_BASE_COOLDOWN = float(os.environ.get("NVU_KEYMGR_CONN_BASE_COOLDOWN", "30"))
_CONN_MAX_COOLDOWN = float(os.environ.get("NVU_KEYMGR_CONN_MAX_COOLDOWN", "60"))
_CONN_FAIL_THRESHOLD = int(os.environ.get("NVU_KEYMGR_CONN_FAIL_THRESHOLD", "3"))
_CONN_LONG_COOLDOWN = float(os.environ.get("NVU_KEYMGR_CONN_LONG_COOLDOWN", "120"))

# 兼容旧 env
KEY_COOLDOWN_S = float(os.environ.get("KEY_COOLDOWN_S", "60.0"))
TIER_COOLDOWN_S = float(os.environ.get("TIER_COOLDOWN_S", "180"))

# ─── Key 状态 ───
HEALTHY = "healthy"
COOLING_429 = "cooling_429"
COOLING_CONN = "cooling_conn"
AUTH_FAILED = "auth_failed"

_lock = threading.Lock()
_key_state = {}
_key429_count = {}

# auth-fail (跨 tier)
_key_authfail_map = {}
_key_authfail_lock = threading.Lock()
KEY_AUTHFAIL_COOLDOWN_S = float(os.environ.get("KEY_AUTHFAIL_COOLDOWN_S", "600"))

# tier-level degraded
_tier_degraded_map = {}
_tier_degraded_lock = threading.Lock()
TIER_DEGRADED_COOLDOWN_S = float(os.environ.get("NVU_TIER_DEGRADED_COOLDOWN_S", "60"))


def _km_log(msg):
    """Lazy import logger to avoid circular import."""
    try:
        from .logger import _log
        _log("NV-KEYMGR", msg)
    except Exception:
        pass


class KeyManager:
    """全局 5-key 健康状态管理。进程内单例。"""

    @staticmethod
    def mark_429(tier_model, key_idx, duration_s=None):
        with _lock:
            state = _key_state.setdefault((tier_model, key_idx), {
                "429_count": 0, "conn_count": 0,
                "cooldown_until": 0, "cooldown_type": HEALTHY
            })
            state["429_count"] += 1
            consecutive = state["429_count"]
            _key429_count[(tier_model, key_idx)] = consecutive

            if duration_s is not None:
                effective = duration_s
            else:
                effective = min(
                    _429_BASE_COOLDOWN * (2 ** (consecutive - 1)),
                    _429_MAX_COOLDOWN
                )
            state["cooldown_until"] = time.monotonic() + effective
            state["cooldown_type"] = COOLING_429

            _km_log(f"429 tier={tier_model} k{key_idx+1} count={consecutive} cooldown={effective:.0f}s")

    @staticmethod
    def mark_conn_error(tier_model, key_idx, error_type="conn"):
        with _lock:
            state = _key_state.setdefault((tier_model, key_idx), {
                "429_count": 0, "conn_count": 0,
                "cooldown_until": 0, "cooldown_type": HEALTHY
            })
            state["conn_count"] += 1
            consecutive = state["conn_count"]

            if consecutive >= _CONN_FAIL_THRESHOLD:
                effective = _CONN_LONG_COOLDOWN
                state["conn_count"] = 0
            else:
                effective = min(
                    _CONN_BASE_COOLDOWN * (2 ** (consecutive - 1)),
                    _CONN_MAX_COOLDOWN
                )
            state["cooldown_until"] = time.monotonic() + effective
            state["cooldown_type"] = COOLING_CONN

            _km_log(f"conn_err tier={tier_model} k{key_idx+1} type={error_type} count={consecutive} cooldown={effective:.0f}s")

    @staticmethod
    def mark_success(tier_model, key_idx):
        with _lock:
            state = _key_state.get((tier_model, key_idx))
            if state:
                state["429_count"] = 0
                state["conn_count"] = 0
                state["cooldown_until"] = 0
                state["cooldown_type"] = HEALTHY
            _key429_count.pop((tier_model, key_idx), None)

    @staticmethod
    def is_available(tier_model, key_idx):
        with _lock:
            state = _key_state.get((tier_model, key_idx))
            if not state:
                return True
            return state["cooldown_until"] <= time.monotonic()

    @staticmethod
    def get_healthy_keys(tier_model, num_keys=5):
        now = time.monotonic()
        healthy = []
        cooling = []
        with _lock:
            for k in range(num_keys):
                state = _key_state.get((tier_model, k))
                if not state or state["cooldown_until"] <= now:
                    healthy.append(k)
                else:
                    cooling.append(k)
        cooling.sort(key=lambda k: _key_state.get((tier_model, k), {}).get("cooldown_until", 0))
        return healthy + cooling

    @staticmethod
    def get_state(tier_model, key_idx):
        with _lock:
            state = _key_state.get((tier_model, key_idx), {})
            now = time.monotonic()
            cooldown_remaining = max(0, state.get("cooldown_until", 0) - now)
            return {
                "429_count": state.get("429_count", 0),
                "conn_count": state.get("conn_count", 0),
                "cooldown_type": state.get("cooldown_type", HEALTHY) if cooldown_remaining > 0 else HEALTHY,
                "cooldown_remaining_s": int(cooldown_remaining),
            }


_km = KeyManager()


# ─── 向后兼容 cooldown.py 旧 API ───

def is_key_cooling(tier_model, key_idx):
    return not _km.is_available(tier_model, key_idx)

def mark_key_cooling(tier_model, key_idx, duration_s=None):
    """旧 API：Phase 1 兼容，统一走 mark_429 逻辑。"""
    _km.mark_429(tier_model, key_idx, duration_s=duration_s)

def reset_key429_count(tier_model, key_idx):
    _km.mark_success(tier_model, key_idx)

def is_key_auth_failed(key_idx):
    with _key_authfail_lock:
        expiry = _key_authfail_map.get(key_idx, 0)
        return expiry > time.monotonic()

def mark_key_auth_failed(key_idx, duration_s=None):
    effective = KEY_AUTHFAIL_COOLDOWN_S if duration_s is None else float(duration_s)
    with _key_authfail_lock:
        _key_authfail_map[key_idx] = time.monotonic() + effective

def mark_tier_degraded(tier_model, duration_s=None):
    effective = TIER_DEGRADED_COOLDOWN_S if duration_s is None else float(duration_s)
    with _tier_degraded_lock:
        _tier_degraded_map[tier_model] = time.monotonic() + effective
    return effective

def is_tier_degraded(tier_model):
    with _tier_degraded_lock:
        expiry = _tier_degraded_map.get(tier_model, 0)
        if expiry > time.monotonic():
            return True
        if tier_model in _tier_degraded_map:
            _tier_degraded_map.pop(tier_model, None)
        return False
