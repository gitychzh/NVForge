#!/usr/bin/env python3
"""R-rebuild Phase 1: cooldown.py → key_manager.py 代理层.

旧 API 完全保留，底层转调 KeyManager。
所有外部调用方（config.py, upstream.py, handlers.py）无需改动。
"""
from .key_manager import (
    is_key_cooling,
    mark_key_cooling,
    reset_key429_count,
    KEY_COOLDOWN_S,
    TIER_COOLDOWN_S,
    is_key_auth_failed,
    mark_key_auth_failed,
    KEY_AUTHFAIL_COOLDOWN_S,
    is_tier_degraded,
    mark_tier_degraded,
    TIER_DEGRADED_COOLDOWN_S,
    KeyManager,
)

# 公开 KeyManager 供 Phase 2+ 使用
__all__ = [
    "is_key_cooling", "mark_key_cooling", "reset_key429_count",
    "KEY_COOLDOWN_S", "TIER_COOLDOWN_S",
    "is_key_auth_failed", "mark_key_auth_failed", "KEY_AUTHFAIL_COOLDOWN_S",
    "is_tier_degraded", "mark_tier_degraded", "TIER_DEGRADED_COOLDOWN_S",
    "KeyManager",
]
