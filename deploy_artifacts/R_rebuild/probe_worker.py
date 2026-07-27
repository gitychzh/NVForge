#!/usr/bin/env python3
"""R-rebuild Phase 3: 后台 ProbeWorker — 异步探测 cooling key 恢复状态。

每 NVU_PROBE_INTERVAL 秒扫描所有 cooling key，发轻量 probe 请求。
probe 成功 → KeyManager.mark_success + set Event 通知 WaitQueue。
probe 失败 → 保持 cooling 状态。

probe 请求：用最小 input（"hi"），非 stream，走该 key 绑定的 mihomo 代理端口。
NVCF 正常返回 200 = 恢复。429 = 仍在冷却。conn error = 仍然间歇故障。
"""

import os
import threading
import time
import json
import http.client
import ssl

# ─── 配置 ───
PROBE_INTERVAL = float(os.environ.get("NVU_PROBE_INTERVAL", "15"))
PROBE_TIMEOUT = float(os.environ.get("NVU_PROBE_TIMEOUT", "10"))
PROBE_ENABLED = os.environ.get("NVU_PROBE_ENABLED", "0") == "1"

_probe_lock = threading.Lock()
_probe_thread = None
_stop_event = threading.Event()
_recovery_event = threading.Event()  # set when any key recovers


def _probe_log(msg):
    """Lazy import logger to avoid circular import."""
    try:
        from .logger import _log
        _log("NV-PROBE", msg)
    except Exception:
        pass


def _get_probe_config(key_idx):
    """获取 key 的 probe 配置：proxy_url, function_id, api_key."""
    try:
        from .config import (
            NVU_KEYS, NVU_NUM_KEYS,
            NVU_PROXY_URLS,
            NVCF_PEXEC_MODELS, NVCF_BASE_URL,
            NV_GLM52_RR_US_PROXIES,
        )
        if key_idx >= NVU_NUM_KEYS:
            return None

        # 获取该 key 的代理 URL
        # glm5.2 用 NV_GLM52_RR_US_PROXIES (7894-7899)
        if key_idx < len(NV_GLM52_RR_US_PROXIES):
            proxy_url = NV_GLM52_RR_US_PROXIES[key_idx]
        elif key_idx < len(NVU_PROXY_URLS):
            proxy_url = NVU_PROXY_URLS[key_idx]
        else:
            proxy_url = ""

        # 从 NVCF_PEXEC_MODELS 获取 function_id (不用模块级变量)
        glm52_cfg = NVCF_PEXEC_MODELS.get("glm5_2_nv", {})
        function_id = glm52_cfg.get("function_ids", [None])[0]

        return {
            "key": NVU_KEYS[key_idx],
            "proxy_url": proxy_url,
            "function_id": function_id,
            "host": NVCF_BASE_URL,
        }
    except Exception as e:
        _probe_log(f"config error: {e}")
        return None


def _make_probe_request(config):
    """发轻量 probe 请求。返回 (success: bool, status: int)."""
    try:
        from .nvcf_conn import _make_nvcf_proxy_conn

        host = config["host"]
        proxy_url = config["proxy_url"]
        api_key = config["key"]
        function_id = config["function_id"]

        # 最小请求体
        body = json.dumps({
            "model": "z-ai/glm-5.2",
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 1,
            "stream": False,
        })

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "Content-Length": str(len(body)),
            "Connection": "close",
            "User-Agent": "Mozilla/5.0",
        }

        path = f"/nim/v1/{function_id}/chat/completions"

        conn = _make_nvcf_proxy_conn(proxy_url, nvcf_host=host, timeout=PROBE_TIMEOUT)
        if conn.sock:
            conn.sock.settimeout(PROBE_TIMEOUT)

        conn.request("POST", path, body=body, headers=headers)
        resp = conn.getresponse()
        status = resp.status
        resp.read()  # drain
        conn.close()

        return status == 200, status

    except Exception as e:
        return False, -1


def _probe_loop():
    """主循环：每 PROBE_INTERVAL 秒扫描 cooling keys。"""
    _probe_log(f"ProbeWorker started, interval={PROBE_INTERVAL}s timeout={PROBE_TIMEOUT}s")

    while not _stop_event.is_set():
        try:
            from .key_manager import KeyManager, _key_state, _lock
            from .config import NVU_NUM_KEYS

            # 找出所有 cooling 的 key（跨所有 tier）
            cooling_keys = set()
            with _lock:
                for (tier_model, key_idx), state in _key_state.items():
                    if state.get("cooldown_until", 0) > time.monotonic():
                        if "glm5_2" in tier_model:  # 只 probe glm5.2
                            cooling_keys.add(key_idx)

            if not cooling_keys:
                _stop_event.wait(PROBE_INTERVAL)
                continue

            _probe_log(f"scanning {len(cooling_keys)} cooling keys: {sorted(cooling_keys)}")

            for key_idx in sorted(cooling_keys):
                if _stop_event.is_set():
                    break

                config = _get_probe_config(key_idx)
                if not config:
                    continue

                success, status = _make_probe_request(config)

                if success:
                    # 恢复！标记 healthy
                    KeyManager.mark_success("glm5_2_nv", key_idx)
                    _probe_log(f"k{key_idx+1} RECOVERED (status=200), marked healthy")
                    # 通知 WaitQueue
                    _recovery_event.set()
                else:
                    if status == 429:
                        _probe_log(f"k{key_idx+1} still 429")
                    elif status > 0:
                        _probe_log(f"k{key_idx+1} status={status}, not ready")
                    else:
                        _probe_log(f"k{key_idx+1} conn error, not ready")

        except Exception as e:
            _probe_log(f"probe loop error: {e}")

        _stop_event.wait(PROBE_INTERVAL)


def start_probe_worker():
    """启动后台 ProbeWorker 线程。"""
    global _probe_thread, _stop_event, _recovery_event

    if not PROBE_ENABLED:
        return

    if _probe_thread and _probe_thread.is_alive():
        return

    _stop_event = threading.Event()
    _recovery_event = threading.Event()
    _probe_thread = threading.Thread(target=_probe_loop, daemon=True, name="ProbeWorker")
    _probe_thread.start()
    _probe_log(f"ProbeWorker thread started (enabled={PROBE_ENABLED})")


def stop_probe_worker():
    """停止 ProbeWorker。"""
    global _stop_event
    _stop_event.set()
    _probe_log("ProbeWorker stopped")


def wait_for_recovery(timeout_s=120):
    """等待任意 key 恢复。返回 True=有 key 恢复, False=超时。"""
    _recovery_event.clear()
    recovered = _recovery_event.wait(timeout_s)
    if recovered:
        _recovery_event.clear()
    return recovered


def clear_recovery_event():
    """清除 recovery event（WaitQueue 入口调用）。"""
    _recovery_event.clear()
