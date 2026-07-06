#!/usr/bin/env python3
"""ChatCompletions 透传 + fallback + circuit (标准库 http.client, 同步).

不持 key, 不做 key 轮转. 转发到 nv_gw(40006)/ms_gw(40007), 由它们处理 key.
与 cx4102 的区别: 不做 Responses↔ChatCompletions 转换, 直接透传 chat 响应.
fallback 时 reminder 插入 chat 响应 (非流: content 前缀; 流: 首 delta 前缀).
"""
import json
import time
import threading
import socket
import http.client
from urllib.parse import urlparse
from .config import (
    PRIMARY_URL, FALLBACK_URL, PRIMARY_MODEL, FALLBACK_MODEL,
    FALLBACK_TIMEOUT_S, PRIMARY_STREAM_TIMEOUT_S, CIRCUIT_FAILURE_THRESHOLD,
    CIRCUIT_OPEN_S, FALLBACK_RECOVER_S, NV_GW_API_KEY, MS_GW_API_KEY,
    FALLBACK_NOTICE, FALLBACK_ENABLED,
    PROMPT_TOKEN_LIMIT, SUPPLEMENT_REASONING_AS_CONTENT,
)
from .logger import _log

# R763: connect timeout 与 read timeout 分离.
#   改前: HTTPConnection(timeout=PRIMARY_STREAM_TIMEOUT_S=90s) 同时管 connect+read.
#   问题: nv_gw 瞬时网络抖动时 connect 卡 90s 才报 TimeoutError 切 fallback, 浪费 90s.
#   修复: connect 用短 timeout (默认 10s, env CC_CONNECT_TIMEOUT_S 可调),
#         read 用 PRIMARY_STREAM_TIMEOUT_S / FALLBACK_TIMEOUT_S.
#   实现: socket.create_connection(connect_timeout) 预连, 再交给 HTTPConnection.sock,
#         getresponse 前 settimeout(read_timeout).
CC_CONNECT_TIMEOUT_S = float(__import__("os").environ.get("CC_CONNECT_TIMEOUT_S", "10"))


class CircuitState:
    def __init__(self):
        self._lock = threading.Lock()
        self.consecutive_failures = 0
        self.circuit_open_until = 0.0
        self.last_fallback_at = 0.0

    def should_try_primary(self):
        with self._lock:
            now = time.time()
            if now < self.circuit_open_until:
                return False
            if now - self.last_fallback_at < FALLBACK_RECOVER_S:
                return False
            return True

    def record_primary_failure(self):
        with self._lock:
            self.consecutive_failures += 1
            self.last_fallback_at = time.time()
            if self.consecutive_failures >= CIRCUIT_FAILURE_THRESHOLD:
                self.circuit_open_until = time.time() + CIRCUIT_OPEN_S
                _log("CIRCUIT-OPEN",
                     f"primary 连续 {self.consecutive_failures} 次故障, circuit 打开 {CIRCUIT_OPEN_S}s",
                     failures=self.consecutive_failures)

    def record_primary_success(self):
        with self._lock:
            self.consecutive_failures = 0


_circuit = CircuitState()



def _estimate_tokens(oai_body):
    """粗略估算请求 token 数 (chars/4). 用于 prompt 超限预检."""
    n = 0
    for m in oai_body.get("messages", []):
        if isinstance(m, dict):
            c = m.get("content", "")
            if isinstance(c, list):
                for part in c:
                    if isinstance(part, dict):
                        n += len(str(part.get("text", "")))
            else:
                n += len(str(c))
            # tool_calls / function args 也算
            for k in ("tool_calls", "function_call"):
                if m.get(k):
                    n += len(json.dumps(m[k], ensure_ascii=False))
    for t in oai_body.get("tools", []) or []:
        n += len(json.dumps(t, ensure_ascii=False))
    return n // 4


def _prompt_too_large(oai_body):
    """R766: prompt token 超限预检. 返回 (True, est_tokens) 或 (False, 0)."""
    if PROMPT_TOKEN_LIMIT <= 0:
        return False, 0
    est = _estimate_tokens(oai_body)
    return est > PROMPT_TOKEN_LIMIT, est


def _is_primary_failure(status, body):
    """自包含判定: 5xx / all_tiers_exhausted / None(连接失败)."""
    if status is None:
        return True
    if status >= 500:
        return True
    if isinstance(body, dict):
        err = body.get("error", {})
        msg = ""
        if isinstance(err, dict):
            msg = str(err.get("message", "")) + " " + str(err.get("type", ""))
        elif isinstance(err, str):
            msg = err
        if "all_tiers_exhausted" in msg or "exhausted" in msg.lower():
            return True
    return False


def _post_upstream(base_url, model, api_key, oai_body, stream, timeout_s):
    """同步 POST 到上游, 返回 (resp, conn) 或 (None, error_str).

    R763: connect 与 read timeout 分离.
      connect: CC_CONNECT_TIMEOUT_S (默认 10s) — TCP 建连阶段, 短.
      read:    timeout_s (PRIMARY_STREAM_TIMEOUT_S 或 FALLBACK_TIMEOUT_S) — 读响应阶段, 长.
    改前 HTTPConnection(timeout=timeout_s) 把两阶段混用, 抖动时 connect 卡 90s.
    """
    p = urlparse(base_url)
    is_https = (p.scheme == "https")
    port = p.port or (443 if is_https else 80)
    path = p.path.rstrip("/") + "/chat/completions"
    if not path.startswith("/"):
        path = "/" + path
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream" if stream else "application/json",
    }
    body = dict(oai_body)
    body["model"] = model
    body["stream"] = stream
    body_bytes = json.dumps(body).encode("utf-8")
    try:
        # R763: 先用短 connect_timeout 做 TCP 建连, 避免抖动时卡 90s.
        sock = socket.create_connection((p.hostname, port), timeout=CC_CONNECT_TIMEOUT_S)
        # 建连成功后, read 阶段用完整 timeout_s
        sock.settimeout(timeout_s)
        if is_https:
            import ssl
            ctx = ssl.create_default_context()
            sock = ctx.wrap_socket(sock, server_hostname=p.hostname)
            sock.settimeout(timeout_s)
        conn = http.client.HTTPConnection(p.hostname, port, timeout=timeout_s)
        conn.sock = sock
        conn.request("POST", path, body=body_bytes, headers=headers)
        resp = conn.getresponse()
        return resp, conn
    except Exception as e:
        _log("UPSTREAM-ERR", f"connect to {base_url} failed: {type(e).__name__}: {e}")
        return None, str(e)


def _read_body(resp):
    try:
        raw = resp.read()
        return json.loads(raw.decode("utf-8"))
    except Exception as e:
        _log("READ-ERR", f"read upstream body failed: {e}")
        return {"_raw_read_error": str(e)}


def _iter_sse_chunks(resp):
    """从 http.client resp 读 SSE, yield 每个 data: 行解析后的 dict.
    遇到 [DONE] 停止. 出错抛异常."""
    buffer = ""
    while True:
        chunk = resp.read(8192)
        if not chunk:
            return
        buffer += chunk.decode("utf-8", errors="replace")
        while "\n\n" in buffer:
            event_str, buffer = buffer.split("\n\n", 1)
            for line in event_str.split("\n"):
                if not line.startswith("data:"):
                    continue
                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    return
                try:
                    yield json.loads(data_str)
                except Exception:
                    continue


def _inject_notice_non_stream(chat_body, notice):
    """fallback reminder 插入非流式 chat 响应的 content 前缀."""
    try:
        choices = chat_body.get("choices", [])
        if choices:
            msg = choices[0].get("message", {})
            content = msg.get("content", "")
            msg["content"] = notice + "\n\n" + content if content else notice
    except Exception:
        pass
    return chat_body


def forward_non_stream(oai_body, request_model):
    """非流透传 + fallback. 返回 (chat_completions_dict, status_code)."""
    try_primary = _circuit.should_try_primary() if FALLBACK_ENABLED else True

    if try_primary:
        resp, conn = _post_upstream(PRIMARY_URL, PRIMARY_MODEL, NV_GW_API_KEY,
                                    oai_body, False, FALLBACK_TIMEOUT_S)
        if resp is not None:
            status = resp.status
            body = _read_body(resp)
            try:
                conn.close()
            except Exception:
                pass
            if not _is_primary_failure(status, body):
                _circuit.record_primary_success()
                return body, status
            _log("PRIMARY-FAIL", f"nv_gw status={status}, 触发 fallback",
                 status=status, err=str(body)[:200])
        else:
            _log("PRIMARY-FAIL", "nv_gw 连接失败, 触发 fallback")
        _circuit.record_primary_failure()

    if not FALLBACK_ENABLED:
        return {"error": {"message": "primary 不可用且 fallback 已禁用",
                          "type": "primary_down_no_fallback"}}, 503

    # fallback
    resp, conn = _post_upstream(FALLBACK_URL, FALLBACK_MODEL, MS_GW_API_KEY,
                                oai_body, False, FALLBACK_TIMEOUT_S)
    if resp is None:
        _log("FALLBACK-FAIL", "ms_gw 连接失败")
        return {"error": {"message": "primary 和 fallback 均不可用",
                          "type": "all_backends_down"}}, 503
    status = resp.status
    body = _read_body(resp)
    try:
        conn.close()
    except Exception:
        pass
    if status >= 400:
        return body, status
    _log("FALLBACK", "从 primary 切到 ms_gw, 提醒插入 content 前缀")
    return _inject_notice_non_stream(body, FALLBACK_NOTICE), 200


def _stream_from_upstream(resp, conn, notice, fallback_used):
    """从上游 SSE 读 chat-completions chunk → 原样 yield (event_name, raw_dict).
    fallback_used 时在第一个 content delta 前插 notice.
    流结束/异常时尽量闭环 ([DONE]).

    R766: 若 SUPPLEMENT_REASONING_AS_CONTENT 开启, 且整流没发过 content delta 但
    累积了 reasoning_content (glm5_2_nv thinking 模式: 只发 reasoning 不发 content),
    流末补一个 content chunk = reasoning 全文, 让客户端 (openclaw) 收到 content 不超时.
    """
    notice_sent = not fallback_used  # primary 模式不插 notice
    reasoning_buf = []  # R766: 累积 reasoning_content
    content_seen = False  # R766: 是否发过 content delta
    last_finish_reason = None
    last_chunk_template = None  # R766: 留最后一个 chunk 做模板, 补 content 用
    try:
        for chunk_data in _iter_sse_chunks(resp):
            try:
                choices = chunk_data.get("choices", [])
                if choices:
                    d = choices[0].get("delta", {})
                    rc = d.get("reasoning_content")
                    if rc:
                        reasoning_buf.append(str(rc))
                    # R766c: content="" (空字符串) 不算有 content (ms_gw 返回 content="" + reasoning)
                    c_val = d.get("content")
                    if isinstance(c_val, str) and c_val:
                        content_seen = True
                    fr = choices[0].get("finish_reason")
                    if fr:
                        last_finish_reason = fr
                        last_chunk_template = chunk_data
            except Exception:
                pass
            # fallback 模式: 在第一个有 choices[].delta.content 的 chunk 前插 notice
            if not notice_sent:
                try:
                    choices = chunk_data.get("choices", [])
                    # R766d: content 非空字符串才插 notice (ms_gw content="" 不触发)
                    _c = choices[0].get("delta", {}).get("content") if choices else None
                    if isinstance(_c, str) and _c:
                        notice_sent = True
                        notice_chunk = json.loads(json.dumps(chunk_data))  # deep copy
                        d = notice_chunk["choices"][0]["delta"]
                        d["content"] = notice + "\n\n"
                        yield ("message", notice_chunk)
                except Exception:
                    pass
            yield ("message", chunk_data)
        # R766: 流末补 content (thinking 模式只发 reasoning, content=null)
        if SUPPLEMENT_REASONING_AS_CONTENT and not content_seen and reasoning_buf:
            full_reasoning = "".join(reasoning_buf)
            _log("SUPPLEMENT-CONTENT",
                 f"流末补 content: 整流无 content delta, reasoning {len(full_reasoning)} chars, "
                 f"finish={last_finish_reason}")
            tmpl = json.loads(json.dumps(last_chunk_template)) if last_chunk_template else {
                "choices": [{"index": 0, "delta": {}, "finish_reason": None}]
            }
            ch = tmpl["choices"][0]
            d = ch.setdefault("delta", {})
            d.pop("reasoning_content", None)
            d["content"] = full_reasoning
            ch["finish_reason"] = "stop"  # 补完 content 标记 stop
            yield ("message", tmpl)
        # 正常结束: 发 done (不在 finally 里, 避免 GeneratorExit 时 yield 报错)
        yield ("done", None)
    except Exception as e:
        _log("STREAM-UPSTREAM-ERR", f"上游流读取失败: {type(e).__name__}: {e}")
        # R790: 流中途异常 (timeout 等) 时, 若已累积 reasoning 但未发 content,
        # 补一个 content chunk = reasoning 全文, 避免客户端 (openclaw) 收空 content 卡死.
        # 复用 supplement 语义 (仅 SUPPLEMENT_REASONING_AS_CONTENT 开启时生效).
        if SUPPLEMENT_REASONING_AS_CONTENT and not content_seen and reasoning_buf:
            full_reasoning = "".join(reasoning_buf)
            _log("SUPPLEMENT-CONTENT-ON-ERR",
                 f"流中途异常补 content: reasoning {len(full_reasoning)} chars, finish={last_finish_reason}")
            tmpl = json.loads(json.dumps(last_chunk_template)) if last_chunk_template else {
                "choices": [{"index": 0, "delta": {}, "finish_reason": None}]
            }
            ch = tmpl["choices"][0]
            d = ch.setdefault("delta", {})
            d.pop("reasoning_content", None)
            d["content"] = full_reasoning
            ch["finish_reason"] = "stop"
            yield ("message", tmpl)
        yield ("done", None)
    finally:
        try:
            conn.close()
        except Exception:
            pass


def forward_stream(oai_body, request_model):
    """流式透传 + fallback. 生成器, yield (event_name, payload).

    策略:
      - primary 首字节前失败 (连接失败 / 5xx / 首响应超时) → 静默切 fallback
      - primary 流中途失败 → 已发部分流无法回溯, 直接收尾 (不切 fallback)
      - 走 fallback 时在首个 content delta 前插 notice (不污染 reasoning)
    """
    try_primary = _circuit.should_try_primary() if FALLBACK_ENABLED else True

    if try_primary:
        resp, conn = _post_upstream(PRIMARY_URL, PRIMARY_MODEL, NV_GW_API_KEY,
                                    oai_body, True, PRIMARY_STREAM_TIMEOUT_S)
        if resp is None:
            _log("PRIMARY-FAIL-STREAM", "nv_gw 流式连接失败, 切 fallback")
            _circuit.record_primary_failure()
        elif resp.status >= 500:
            _log("PRIMARY-FAIL-STREAM",
                 f"nv_gw 流式 5xx: status={resp.status}, 切 fallback")
            try:
                conn.close()
            except Exception:
                pass
            _circuit.record_primary_failure()
        else:
            # primary 正常 (2xx/4xx): 原样透传, 流中途失败不切 fallback
            for ev in _stream_from_upstream(resp, conn, FALLBACK_NOTICE, False):
                yield ev
            _circuit.record_primary_success()
            return

    if not FALLBACK_ENABLED:
        # fallback 禁用: 发一个错误 chunk + done
        err_chunk = {
            "choices": [{"index": 0, "delta": {"content": "⚠️ primary 不可用且 fallback 已禁用"},
                          "finish_reason": None}]
        }
        yield ("message", err_chunk)
        yield ("done", None)
        return

    # fallback 流 (circuit 打开 / primary 首字节前失败)
    resp, conn = _post_upstream(FALLBACK_URL, FALLBACK_MODEL, MS_GW_API_KEY,
                                oai_body, True, FALLBACK_TIMEOUT_S)
    if resp is None:
        _log("FALLBACK-FAIL-STREAM", "ms_gw 流式连接失败")
        err_chunk = {
            "choices": [{"index": 0, "delta": {
                "content": "⚠️ primary 和 fallback 均不可用, 请稍后重试."
            }, "finish_reason": None}]
        }
        yield ("message", err_chunk)
        yield ("done", None)
        return

    if resp.status >= 400:
        body = _read_body(resp)
        try:
            conn.close()
        except Exception:
            pass
        err_msg = json.dumps(body, ensure_ascii=False)[:500]
        _log("FALLBACK-STREAM-ERR", f"ms_gw status={resp.status}: {err_msg[:200]}")
        err_chunk = {
            "choices": [{"index": 0, "delta": {
                "content": f"⚠️ [fallback 错误] {err_msg}"
            }, "finish_reason": None}]
        }
        yield ("message", err_chunk)
        yield ("done", None)
        return

    _log("FALLBACK-STREAM", "从 primary 切到 ms_gw 流式, 提醒插入首 delta 前")
    for ev in _stream_from_upstream(resp, conn, FALLBACK_NOTICE, True):
        yield ev
