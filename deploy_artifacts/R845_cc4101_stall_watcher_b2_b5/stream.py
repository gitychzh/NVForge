#!/usr/bin/env python3
"""Streaming SSE conversion and non-stream collect+synthesize for cc4101.

R684: Adapted from legacy-cc/gateway/stream.py. Two modes:
  1. stream_to_anth — real-time SSE: OpenAI streaming chunk → Anthropic SSE event.
     Handles reasoning_content → thinking block, content → text block,
     tool_calls → tool_use block. Used when CC requests stream=true.
  2. collect_stream_to_anth — collect streaming chunks → synthesize non-stream
     Anthropic response. Used when CC requests stream=false (but upstream is
     still stream — glm5.2 non-stream is broken on both backends).

Simplified vs legacy-cc: no prefill_buffer / NV peek (cc4101's upstreams are
nv_gw/ms_gw, not raw NVCF; they handle their own empty-stream detection).
"""
import json
import uuid
import time
import datetime
import http.client
import socket

from .config import THINKING_SIGNATURE_DEFAULT, UPSTREAM_TIMEOUT, UPSTREAM_IDLE_TIMEOUT, \
    CC4101_STREAM_TOTAL_DEADLINE_S, CC4101_STREAM_IDLE_GAP_S, CC4101_STREAM_POLL_S
from .logger import _log, _log_metrics, _log_error_detail


def stream_to_anth(handler, resp, request_model, target_model, conn, metrics, t_start):
    """Real-time SSE conversion: OpenAI streaming chunks → Anthropic SSE events."""
    # R845 B5: send_response 阶段在主 try 之外, CC 早断会 BrokenPipe 冒泡致上游 conn 泄漏 + metrics 漏记.
    try:
        handler.send_response(200)
        handler.send_header("Content-Type", "text/event-stream")
        handler.send_header("Cache-Control", "no-cache")
        handler.send_header("Connection", "close")
        handler.close_connection = True
        handler.end_headers()
    except (BrokenPipeError, ConnectionResetError, OSError) as e:
        _log("ERR", f"client gone before SSE headers after {int((time.time()-t_start)*1000)}ms: {e}")
        metrics["error_type"] = "client_gone_pre_stream"
        metrics["status"] = 499
        metrics["duration_ms"] = int((time.time() - t_start) * 1000)
        _log_metrics(metrics)
        try:
            conn.close()
        except Exception:
            pass
        return

    message_start_sent = False
    message_delta_sent = False
    ttfb_recorded = False
    buffer = ""
    next_block_idx = 0
    active_block_type = None  # "thinking" | "text" | "tool_use"
    streaming_input_tokens = 0
    streaming_output_tokens = 0
    pending_stop_reason = None
    # R844 F5: 自身空僵尸检测累积量. cc4101 一旦开始 stream_to_anth 就无法切 fallback
    # (SSE 头已发), 唯一出路是检测空僵尸后 emit api_error 让 Claude Code 重试整个请求
    # (下次大概率命中 fallback ms_gw 或 nv_gw 不同 mode/IP). 不依赖 nv_gw 的 content_filter
    # 信号 — cc4101 自己也要能抓 "大 input + 少 content + 无真 tool_call" 的空壳.
    stream_content_chars = 0
    stream_reasoning_chars = 0
    stream_saw_real_tool_call = False  # tool_calls 带 id 且 arguments 非空才算真工具调用
    stream_zombie = False  # 命中空僵尸 → 走 api_error 路径, 不发 end_turn
    # R845 B7: stream stall-watcher 双门槛状态.
    stream_total_deadline = None  # ttfb 后设 = ttfb + CC4101_STREAM_TOTAL_DEADLINE_S
    last_progress_time = None  # 最近一次收到真内容(content/reasoning/tool_call)的时刻; idle间隙超限即stall

    def _emit_message_start(msg_id=None, input_tokens_est=0):
        nonlocal message_start_sent
        handler._send_sse("message_start", {
            "type": "message_start",
            "message": {
                "id": msg_id or f"msg_{uuid.uuid4().hex[:24]}",
                "type": "message", "role": "assistant",
                "model": request_model, "content": [],
                "stop_reason": None, "stop_sequence": None,
                "usage": {"input_tokens": input_tokens_est, "output_tokens": 0,
                          "cache_creation_input_tokens": 0,
                          "cache_read_input_tokens": 0},
            },
        })
        message_start_sent = True

    def _emit_graceful_end(stop_reason="end_turn", output_tokens=0, input_tokens_real=0, interrupted=False, zombie=False):
        nonlocal message_start_sent, message_delta_sent, active_block_type, pending_stop_reason
        if next_block_idx == 0:
            _log("WARN", f"empty_stream_response: stream ended with no content "
                         f"(model={metrics.get('mapped_model','?')} output_tokens={streaming_output_tokens})")
            _log_error_detail({
                "request_id": metrics.get("request_id", "?"),
                "timestamp": datetime.datetime.now().isoformat(),
                "error_subcategory": "empty_stream_response",
                "upstream_status": 200,
                "mapped_model": metrics.get("mapped_model", "?"),
                "upstream_used": metrics.get("upstream_used", "?"),
                "streaming_output_tokens": streaming_output_tokens,
                "finish_reason": pending_stop_reason,
            })
            metrics["empty_stream_response"] = True
        if active_block_type is not None:
            handler._send_sse("content_block_stop",
                           {"type": "content_block_stop", "index": next_block_idx - 1})
            active_block_type = None
        if not message_start_sent:
            _emit_message_start(input_tokens_est=metrics.get("estimated_input_tokens", 0))
        # R844 F4/F5: zombie 空响应 (content_filter from nv_gw, 或自身检测的空壳) → emit api_error
        # 让 Claude Code 重试整个请求 (下次命中 fallback 或不同 mode/IP). 不发 end_turn — 否则 CC
        # 认为正常完成不重试. 与 interrupted 路径同形但 zombie 不要求 pending_stop_reason is None.
        if zombie:
            _log("ERR", f"zombie empty stream — emitting api_error SSE so CC retries "
                        f"(req={metrics.get('request_id','?')} model={metrics.get('mapped_model','?')})")
            handler._send_sse("error", {
                "type": "error",
                "error": {"type": "api_error",
                          "message": "upstream returned empty/filtered completion, please retry"},
            })
            handler._send_sse("message_stop", {"type": "message_stop"})
            metrics["status"] = 502
            if not metrics.get("error_type"):
                metrics["error_type"] = "zombie_empty_completion"
            metrics["duration_ms"] = int((time.time() - t_start) * 1000)
            _log_metrics(metrics)
            try:
                conn.close()
            except Exception:
                pass
            return
        # R690 cc2 red-team: if the stream was interrupted mid-flight (socket error / timeout)
        # AND we never saw a real finish_reason, do NOT fake stop_reason=end_turn — CC would
        # treat the truncated response as a complete one and not retry. Instead emit an
        # Anthropic error SSE (api_error) so CC retries the whole request.
        if interrupted and pending_stop_reason is None:
            _log("ERR", f"stream interrupted without finish_reason — emitting api_error SSE so CC retries "
                        f"(req={metrics.get('request_id','?')})")
            handler._send_sse("error", {
                "type": "error",
                "error": {"type": "api_error",
                          "message": "upstream stream interrupted before completion"},
            })
            handler._send_sse("message_stop", {"type": "message_stop"})
            metrics["status"] = 502
            if not metrics.get("error_type"):
                metrics["error_type"] = "StreamInterrupted"
            metrics["duration_ms"] = int((time.time() - t_start) * 1000)
            _log_metrics(metrics)
            try:
                conn.close()
            except Exception:
                pass
            return
        if not message_delta_sent:
            real_output = streaming_output_tokens or output_tokens or metrics.get("output_tokens", 0)
            real_input = streaming_input_tokens or input_tokens_real or metrics.get("input_tokens", 0)
            metrics["output_tokens"] = real_output
            metrics["input_tokens"] = real_input
            final_stop = pending_stop_reason or stop_reason
            usage_delta = {"output_tokens": real_output}
            if real_input > 0:
                usage_delta["input_tokens"] = real_input
            handler._send_sse("message_delta", {
                "type": "message_delta",
                "delta": {"stop_reason": final_stop, "stop_sequence": None},
                "usage": usage_delta,
            })
            message_delta_sent = True
        handler._send_sse("message_stop", {"type": "message_stop"})
        if metrics.get("error_type") and metrics["error_type"] not in (None, "empty_stream_response"):
            metrics["status"] = 502
        elif metrics.get("empty_stream_response"):
            metrics["status"] = 502
            metrics["error_type"] = "empty_stream_response"
        else:
            metrics["status"] = 200
        metrics["duration_ms"] = int((time.time() - t_start) * 1000)
        _log_metrics(metrics)
        try:
            conn.close()
        except Exception:
            pass

    try:
        while True:
            # R845 B7: stall-watcher 双门槛检查点 (chunk 之间). per-read 用短轮询
            # CC4101_STREAM_POLL_S, read 阻塞最多 POLL_S 就抛 socket.timeout 进 except,
            # 非致命时 except 内 continue 回到这里再检查 — 让双门槛在纯静默期也能生效.
            if ttfb_recorded and stream_total_deadline and time.time() > stream_total_deadline:
                metrics["error_type"] = "stream_total_deadline"
                _log("STREAM-DEADLINE", f"({request_model}) stream total deadline "
                    f"{CC4101_STREAM_TOTAL_DEADLINE_S}s after ttfb exceeded (stall-watcher)")
                raise socket.timeout("stream_total_deadline")
            if last_progress_time is not None and time.time() - last_progress_time > CC4101_STREAM_IDLE_GAP_S:
                metrics["error_type"] = "stream_idle_stall"
                _log("STREAM-IDLE-STALL", f"({request_model}) no real content for "
                    f"{CC4101_STREAM_IDLE_GAP_S}s (stall-watcher, last_progress_age="
                    f"{int(time.time()-last_progress_time)}s)")
                raise socket.timeout("stream_idle_stall")
            try:
                chunk = resp.read(8192)
            except socket.timeout:
                # per-read 短轮询超时 — 非致命, 上面的双门槛会在下一轮循环判定是否真 stall.
                # 若已达双门槛上限, 上面已 raise 了带 error_type 的 socket.timeout, 会落到下面的 except.
                continue
            if not chunk:
                break
            buffer += chunk.decode("utf-8", errors="replace")

            while "\n\n" in buffer:
                event_str, buffer = buffer.split("\n\n", 1)
                lines = event_str.split("\n")
                event_type = None
                data_str = ""
                for line in lines:
                    if line.startswith("event:"):
                        event_type = line[6:].strip()
                    elif line.startswith("data:"):
                        data_str = line[5:].strip()

                if not data_str or data_str == "[DONE]":
                    _emit_graceful_end()
                    return

                if event_type and event_type != "chunk":
                    continue

                try:
                    chunk_data = json.loads(data_str)
                except json.JSONDecodeError:
                    _log("WARN", f"malformed SSE chunk: {data_str[:200]}")
                    continue

                choices = chunk_data.get("choices") or [{}]
                delta = choices[0].get("delta") or {}
                finish_reason = choices[0].get("finish_reason")

                chunk_usage = chunk_data.get("usage") or {}
                if chunk_usage:
                    pt = chunk_usage.get("prompt_tokens", 0)
                    ct = chunk_usage.get("completion_tokens", 0)
                    if pt > 0:
                        streaming_input_tokens = pt
                        metrics["input_tokens"] = pt
                    if ct > 0:
                        streaming_output_tokens = ct
                        metrics["output_tokens"] = ct

                if not message_start_sent:
                    _emit_message_start(chunk_data.get("id", f"msg_{uuid.uuid4().hex[:24]}"),
                                       input_tokens_est=metrics.get("estimated_input_tokens", 0))

                if not ttfb_recorded and (delta.get("content") or delta.get("reasoning_content") or delta.get("tool_calls")):
                    metrics["ttfb_ms"] = int((time.time() - t_start) * 1000)
                    ttfb_recorded = True
                    # R845 B7: ttfb 后启动 stall-watcher 双门槛计时
                    stream_total_deadline = time.time() + CC4101_STREAM_TOTAL_DEADLINE_S
                    last_progress_time = time.time()

                # R844 F5: 累积 content/reasoning 字符 + 标记真 tool_call (用于空僵尸判定)
                _delta_content = delta.get("content") or ""
                if _delta_content:
                    stream_content_chars += len(_delta_content)
                _delta_reasoning = delta.get("reasoning_content") or ""
                if _delta_reasoning:
                    stream_reasoning_chars += len(_delta_reasoning)
                for _tc in (delta.get("tool_calls") or []):
                    _fn = _tc.get("function", {}) or {}
                    if _tc.get("id") and _fn.get("arguments"):
                        stream_saw_real_tool_call = True
                # R845 B7: 收到真内容即刷新 idle 间隙计时 (防 drip 绕过: 持续产出时 idle 不超限)
                if _delta_content or _delta_reasoning or (delta.get("tool_calls") or []):
                    last_progress_time = time.time()

                # ── Reasoning/thinking ──
                # R690 cc2 red-team: Anthropic spec requires thinking blocks come BEFORE
                # text/tool_use and cannot re-open after. Once we've started a text or
                # tool_use block, drop further reasoning_content deltas instead of
                # opening a new thinking block (which CC would reject).
                reasoning = delta.get("reasoning_content")
                if reasoning and active_block_type not in (None, "thinking"):
                    reasoning = None
                if reasoning:
                    if active_block_type != "thinking":
                        if active_block_type is not None:
                            handler._send_sse("content_block_stop",
                                           {"type": "content_block_stop", "index": next_block_idx - 1})
                        handler._send_sse("content_block_start", {
                            "type": "content_block_start", "index": next_block_idx,
                            "content_block": {"type": "thinking", "thinking": "",
                                              "signature": THINKING_SIGNATURE_DEFAULT},
                        })
                        next_block_idx += 1
                        active_block_type = "thinking"
                    handler._send_sse("content_block_delta", {
                        "type": "content_block_delta", "index": next_block_idx - 1,
                        "delta": {"type": "thinking_delta", "thinking": reasoning},
                    })

                # ── Text ──
                text_delta = delta.get("content")
                if text_delta and active_block_type != "text":
                    if active_block_type is not None:
                        handler._send_sse("content_block_stop",
                                           {"type": "content_block_stop", "index": next_block_idx - 1})
                    handler._send_sse("content_block_start", {
                        "type": "content_block_start", "index": next_block_idx,
                        "content_block": {"type": "text", "text": ""},
                    })
                    next_block_idx += 1
                    active_block_type = "text"
                if text_delta:
                    handler._send_sse("content_block_delta", {
                        "type": "content_block_delta", "index": next_block_idx - 1,
                        "delta": {"type": "text_delta", "text": text_delta},
                    })

                # ── Tool calls ──
                tool_calls = delta.get("tool_calls") or []
                for tc in tool_calls:
                    fn = tc.get("function", {})
                    if tc.get("id"):
                        if active_block_type is not None:
                            handler._send_sse("content_block_stop",
                                           {"type": "content_block_stop", "index": next_block_idx - 1})
                        handler._send_sse("content_block_start", {
                            "type": "content_block_start", "index": next_block_idx,
                            "content_block": {
                                "type": "tool_use",
                                "id": tc["id"],
                                "name": fn.get("name", ""),
                                "input": {},
                            },
                        })
                        next_block_idx += 1
                        active_block_type = "tool_use"
                        if fn.get("arguments"):
                            handler._send_sse("content_block_delta", {
                                "type": "content_block_delta", "index": next_block_idx - 1,
                                "delta": {"type": "input_json_delta", "partial_json": fn["arguments"]},
                            })
                    elif fn.get("arguments") and active_block_type == "tool_use":
                        handler._send_sse("content_block_delta", {
                            "type": "content_block_delta", "index": next_block_idx - 1,
                            "delta": {"type": "input_json_delta", "partial_json": fn["arguments"]},
                        })

                # ── Finish ──
                if finish_reason:
                    if active_block_type is not None:
                        handler._send_sse("content_block_stop",
                                           {"type": "content_block_stop", "index": next_block_idx - 1})
                        active_block_type = None
                    metrics["finish_reason"] = finish_reason
                    # R844 F4: nv_gw 死亡窗口 zombie 会发 finish_reason=content_filter 的 err_chunk (R840).
                    # 原代码把它当正常 end_turn → Claude Code 认为完成不重试, 吞掉 fallback. 改: emit api_error.
                    if finish_reason == "content_filter":
                        stream_zombie = True
                        metrics["error_type"] = "upstream_content_filter"
                        _log("ZOMBIE-CONTENT-FILTER", f"({request_model}) upstream sent finish_reason=content_filter "
                            f"(nv_gw zombie empty), emitting api_error so Claude Code retries (req={metrics.get('request_id','?')})")
                        _emit_graceful_end(zombie=True)
                        return
                    # R844 F5: 自身空僵尸检测. 大 input + content/reasoning 极少 + 无真 tool_call + finish in (stop,tool_calls)
                    # → NVCF 返空壳 (dsv4p 大 context 1793 例, glm5.2 死亡窗口). 不发 end_turn, emit api_error 让 CC 重试.
                    if (finish_reason in ("stop", "tool_calls")
                            and not stream_saw_real_tool_call
                            and (stream_content_chars + stream_reasoning_chars) < 50
                            and metrics.get("total_input_chars", 0) >= 5000):
                        stream_zombie = True
                        metrics["error_type"] = "zombie_empty_completion"
                        _log("ZOMBIE-EMPTY-STREAM", f"({request_model}) zombie empty stream: finish_reason={finish_reason} "
                            f"content={stream_content_chars}c reasoning={stream_reasoning_chars}c input="
                            f"{metrics.get('total_input_chars',0)}c no real tool_call — emitting api_error so CC retries "
                            f"(req={metrics.get('request_id','?')})")
                        _emit_graceful_end(zombie=True)
                        return
                    stop_reason = "end_turn"
                    if finish_reason == "length":
                        stop_reason = "max_tokens"
                    elif finish_reason == "tool_calls":
                        stop_reason = "tool_use"
                    pending_stop_reason = stop_reason

    except socket.timeout as e:
        elapsed_ms = int((time.time() - t_start) * 1000)
        # R845 B2: 区分 stall-watcher 命中 vs per-read 真 idle vs 上游断连伪装成 socket.timeout.
        # a1db6f13: 上游 120.8s 主动断连被 http.client read() 映射成 socket.timeout, 但 120.8 < 150s
        # 说明 per-read 不可能因 idle 触发 (150s 没到), 只能是上游断连 — 旧代码一律记 StreamSocketTimeout
        # 误导运维去调 timeout 治标不治本. 现按 error_type/elapsed 三分.
        if metrics.get("error_type") in ("stream_total_deadline", "stream_idle_stall"):
            error_subcat = metrics["error_type"]
            timeout_kind = "stall_watcher"
            log_lvl, log_tag = "STREAM-STALLED", "stall-watcher"
            metrics["error_type"] = "StreamStallWatcher"
        elif elapsed_ms >= UPSTREAM_IDLE_TIMEOUT * 1000 - 500:
            # 接近/超过 per-read 预算 (旧 150s 语义) = 真 idle, 上游静默
            error_subcat = "stream_socket_timeout"
            timeout_kind = "idle"
            log_lvl, log_tag = "TIMEOUT", "idle"
            metrics["error_type"] = "StreamSocketTimeout"
        else:
            # elapsed < per-read 预算 = per-read 没到点就抛, 只能是上游主动 FIN/RST
            error_subcat = "stream_upstream_disconnect"
            timeout_kind = "upstream_disconnect"
            log_lvl, log_tag = "ERR", "upstream_disconnect"
            metrics["error_type"] = "StreamUpstreamDisconnect"
        _log_error_detail({
            "request_id": metrics.get("request_id", "?"),
            "timestamp": datetime.datetime.now().isoformat(),
            "error_subcategory": error_subcat,
            "upstream_timeout_setting_ms": UPSTREAM_IDLE_TIMEOUT * 1000,
            "upstream_timeout_kind": timeout_kind,
            "elapsed_since_request_start_ms": elapsed_ms,
            "mapped_model": metrics.get("mapped_model", "?"),
            "upstream_used": metrics.get("upstream_used", "?"),
            "error_message": str(e)[:200],
        })
        _log(log_lvl, f"stream {log_tag} after {elapsed_ms}ms "
            f"(UPSTREAM_IDLE_TIMEOUT={UPSTREAM_IDLE_TIMEOUT}s, POLL={CC4101_STREAM_POLL_S}s): {e}")
        _emit_graceful_end(interrupted=True)
        return
    except (http.client.RemoteDisconnected, ConnectionResetError,
            OSError, http.client.IncompleteRead) as e:
        elapsed_ms = int((time.time() - t_start) * 1000)
        error_class = type(e).__name__
        _log("ERR", f"stream {error_class} after {elapsed_ms}ms: {e}")
        _log_error_detail({
            "request_id": metrics.get("request_id", "?"),
            "timestamp": datetime.datetime.now().isoformat(),
            "error_subcategory": f"stream_{error_class}",
            "elapsed_since_request_start_ms": elapsed_ms,
            "mapped_model": metrics.get("mapped_model", "?"),
            "upstream_used": metrics.get("upstream_used", "?"),
            "error_message": str(e)[:300],
        })
        _emit_graceful_end(interrupted=True)
        return
    except Exception as e:
        _log("ERR", f"stream unexpected error: {e}")
        _emit_graceful_end(interrupted=True)
        return

    _emit_graceful_end()


def collect_stream_to_anth(handler, resp, request_model, target_model, conn, metrics, t_start):
    """Collect a streaming SSE response from upstream and synthesize a non-stream
    Anthropic-format response. Used when CC requests stream=false (upstream still
    streams — glm5.2 non-stream is broken on both backends)."""
    reasoning_text = ""
    content_text = ""
    tool_calls_data = []
    finish_reason = "stop"
    total_input_tokens = 0
    total_output_tokens = 0
    msg_id = f"msg_{uuid.uuid4().hex[:24]}"
    ttfb_recorded = False
    buffer = ""
    empty_stream = True  # assume empty until we see real content
    # R845 B7: stall-watcher 双门槛状态 (同 stream_to_anth)
    stream_total_deadline = None
    last_progress_time = None

    try:
        done = False
        while not done:
            # R845 B7: stall-watcher 双门槛检查点 (同 stream_to_anth)
            if ttfb_recorded and stream_total_deadline and time.time() > stream_total_deadline:
                metrics["error_type"] = "collect_stream_total_deadline"
                _log("STREAM-DEADLINE", f"({request_model}) collect stream total deadline "
                    f"{CC4101_STREAM_TOTAL_DEADLINE_S}s after ttfb exceeded (stall-watcher)")
                raise socket.timeout("collect_stream_total_deadline")
            if last_progress_time is not None and time.time() - last_progress_time > CC4101_STREAM_IDLE_GAP_S:
                metrics["error_type"] = "collect_stream_idle_stall"
                _log("STREAM-IDLE-STALL", f"({request_model}) collect no real content for "
                    f"{CC4101_STREAM_IDLE_GAP_S}s (stall-watcher)")
                raise socket.timeout("collect_stream_idle_stall")
            try:
                chunk = resp.read(8192)
            except socket.timeout:
                continue
            if not chunk:
                break
            buffer += chunk.decode("utf-8", errors="replace")

            while "\n\n" in buffer:
                event_str, buffer = buffer.split("\n\n", 1)
                lines = event_str.split("\n")
                event_type = None
                data_str = ""
                for line in lines:
                    if line.startswith("event:"):
                        event_type = line[6:].strip()
                    elif line.startswith("data:"):
                        data_str = line[5:].strip()

                if not data_str or data_str == "[DONE]":
                    # Stream complete. ms_gw keeps the socket open after [DONE]
                    # (no Connection: close), so we must actively close here —
                    # otherwise resp.read() blocks until UPSTREAM_TIMEOUT.
                    done = True
                    break

                if event_type and event_type != "chunk":
                    continue

                try:
                    chunk_data = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                if not ttfb_recorded:
                    metrics["ttfb_ms"] = int((time.time() - t_start) * 1000)
                    ttfb_recorded = True
                    # R845 B7: ttfb 后启动 stall-watcher 双门槛计时
                    stream_total_deadline = time.time() + CC4101_STREAM_TOTAL_DEADLINE_S
                    last_progress_time = time.time()

                msg_id = chunk_data.get("id", msg_id)
                choices = chunk_data.get("choices") or [{}]
                delta = choices[0].get("delta") or {}
                fr = choices[0].get("finish_reason")

                reasoning = delta.get("reasoning_content") or ""
                if reasoning:
                    reasoning_text += reasoning
                    empty_stream = False

                text = delta.get("content") or ""
                if text:
                    content_text += text
                    empty_stream = False

                # R845 B7: 收到真内容刷新 idle 计时
                if reasoning or text or (delta.get("tool_calls") or []):
                    last_progress_time = time.time()

                tool_calls = delta.get("tool_calls") or []
                for tc in tool_calls:
                    fn = tc.get("function", {})
                    if tc.get("id"):
                        tool_calls_data.append({
                            "id": tc["id"],
                            "name": fn.get("name", ""),
                            "arguments": fn.get("arguments", ""),
                        })
                        # R844 F6: 只有带 arguments 的真 tool_call 才算非空 (空壳 id+空args 不算)
                        if fn.get("arguments"):
                            empty_stream = False
                    elif fn.get("arguments") and tool_calls_data:
                        tool_calls_data[-1]["arguments"] += fn["arguments"]

                chunk_usage = chunk_data.get("usage") or {}
                if chunk_usage:
                    total_input_tokens = chunk_usage.get("prompt_tokens", total_input_tokens)
                    total_output_tokens = chunk_usage.get("completion_tokens", total_output_tokens)

                if fr:
                    finish_reason = fr

        conn.close()
    except socket.timeout as e:
        elapsed_ms = int((time.time() - t_start) * 1000)
        # R845 B2: collect 路径同样区分 stall-watcher / idle / 上游断连 (同 stream_to_anth)
        if metrics.get("error_type") in ("collect_stream_total_deadline", "collect_stream_idle_stall"):
            error_subcat = metrics["error_type"]
            timeout_kind = "stall_watcher"
            log_lvl, log_tag = "STREAM-STALLED", "stall-watcher"
            metrics["error_type"] = "CollectStreamStallWatcher"
        elif elapsed_ms >= UPSTREAM_IDLE_TIMEOUT * 1000 - 500:
            error_subcat = "collect_stream_socket_timeout"
            timeout_kind = "idle"
            log_lvl, log_tag = "TIMEOUT", "idle"
            metrics["error_type"] = "CollectStreamSocketTimeout"
        else:
            error_subcat = "collect_stream_upstream_disconnect"
            timeout_kind = "upstream_disconnect"
            log_lvl, log_tag = "ERR", "upstream_disconnect"
            metrics["error_type"] = "CollectStreamUpstreamDisconnect"
        _log_error_detail({
            "request_id": metrics.get("request_id", "?"),
            "timestamp": datetime.datetime.now().isoformat(),
            "error_subcategory": error_subcat,
            "upstream_timeout_kind": timeout_kind,
            "upstream_timeout_setting_ms": UPSTREAM_IDLE_TIMEOUT * 1000,
            "elapsed_since_request_start_ms": elapsed_ms,
            "mapped_model": metrics.get("mapped_model", "?"),
            "upstream_used": metrics.get("upstream_used", "?"),
            "error_message": str(e)[:200],
        })
        _log(log_lvl, f"collect_stream {log_tag} after {elapsed_ms}ms "
            f"(UPSTREAM_IDLE_TIMEOUT={UPSTREAM_IDLE_TIMEOUT}s, POLL={CC4101_STREAM_POLL_S}s): {e}")
        try:
            conn.close()
        except Exception:
            pass
    except Exception as e:
        elapsed_ms = int((time.time() - t_start) * 1000)
        error_class = type(e).__name__
        _log("ERR", f"collect_stream {error_class} after {elapsed_ms}ms: {e}")
        _log_error_detail({
            "request_id": metrics.get("request_id", "?"),
            "timestamp": datetime.datetime.now().isoformat(),
            "error_subcategory": f"collect_stream_{error_class}",
            "elapsed_since_request_start_ms": elapsed_ms,
            "error_message": str(e)[:300],
        })
        try:
            conn.close()
        except Exception:
            pass

    # R844 F4/F6: content_filter finish_reason (nv_gw R840 zombie err_chunk) → 空僵尸
    if finish_reason == "content_filter":
        _log("ZOMBIE-CONTENT-FILTER-COLLECT", f"({metrics.get('request_model','?')}) finish_reason=content_filter "
            f"from upstream (nv_gw zombie) — treating as empty (req={metrics.get('request_id','?')})")
        metrics["empty_stream_response"] = True
        metrics["error_type"] = "upstream_content_filter"
        _log_error_detail({
            "request_id": metrics.get("request_id", "?"),
            "timestamp": datetime.datetime.now().isoformat(),
            "error_subcategory": "upstream_content_filter",
            "upstream_used": metrics.get("upstream_used", "?"),
            "mapped_model": metrics.get("mapped_model", "?"),
            "finish_reason": finish_reason,
        })
    # Empty-stream detection (glm5.2 sometimes returns only reasoning then [DONE]
    # with no content; if BOTH reasoning and content and tool_calls are empty, that's empty)
    elif empty_stream and not reasoning_text and not content_text and not tool_calls_data:
        _log("WARN", f"empty_stream_response (collect): model={metrics.get('mapped_model','?')} "
                     f"output_tokens={total_output_tokens}")
        _log_error_detail({
            "request_id": metrics.get("request_id", "?"),
            "timestamp": datetime.datetime.now().isoformat(),
            "error_subcategory": "empty_stream_response",
            "upstream_used": metrics.get("upstream_used", "?"),
            "mapped_model": metrics.get("mapped_model", "?"),
            "total_output_tokens": total_output_tokens,
            "finish_reason": finish_reason,
        })
        metrics["empty_stream_response"] = True
    # R844 F5/F6: 大 input + 少 content + 无真 tool_call + finish in (stop,tool_calls) → 空壳僵尸
    # (dsv4p 大 context 空壳 tool_calls, glm5.2 死亡窗口). collect 路径返回 502 让 CC 重试.
    elif (finish_reason in ("stop", "tool_calls")
          and (len(reasoning_text) + len(content_text)) < 50
          and not any(tc.get("arguments") for tc in tool_calls_data)
          and metrics.get("total_input_chars", 0) >= 5000):
        _log("ZOMBIE-EMPTY-COLLECT", f"({metrics.get('request_model','?')}) zombie empty collect: "
            f"finish={finish_reason} content={len(content_text)}c reasoning={len(reasoning_text)}c "
            f"input={metrics.get('total_input_chars',0)}c no real tool_call (req={metrics.get('request_id','?')})")
        metrics["empty_stream_response"] = True
        metrics["error_type"] = "zombie_empty_completion"
        _log_error_detail({
            "request_id": metrics.get("request_id", "?"),
            "timestamp": datetime.datetime.now().isoformat(),
            "error_subcategory": "zombie_empty_completion",
            "upstream_used": metrics.get("upstream_used", "?"),
            "mapped_model": metrics.get("mapped_model", "?"),
            "finish_reason": finish_reason,
            "total_input_chars": metrics.get("total_input_chars", 0),
        })

    # Synthesize Anthropic non-stream response
    content = []
    if reasoning_text:
        content.append({"type": "thinking", "thinking": reasoning_text,
                        "signature": THINKING_SIGNATURE_DEFAULT})
    if content_text:
        content.append({"type": "text", "text": content_text})
    for tc_data in tool_calls_data:
        try:
            input_data = json.loads(tc_data["arguments"])
        except json.JSONDecodeError:
            input_data = {"raw": tc_data["arguments"]}
        content.append({"type": "tool_use", "id": tc_data["id"],
                        "name": tc_data["name"], "input": input_data})
    if not content:
        content.append({"type": "text", "text": ""})

    stop_reason = "end_turn"
    if finish_reason == "length":
        stop_reason = "max_tokens"
    elif finish_reason == "tool_calls":
        stop_reason = "tool_use"

    if metrics.get("error_type") and metrics["error_type"] not in (None, "empty_stream_response"):
        metrics["status"] = 502
    elif metrics.get("empty_stream_response"):
        metrics["status"] = 502
        metrics["error_type"] = "empty_stream_response"
    else:
        metrics["status"] = 200
    metrics["duration_ms"] = int((time.time() - t_start) * 1000)
    metrics["input_tokens"] = total_input_tokens
    metrics["output_tokens"] = total_output_tokens
    metrics["finish_reason"] = finish_reason
    _log_metrics(metrics)

    # R690 cc2 red-team: previously hardcoded _send_json(200, ...) even when
    # metrics status was 502 (empty stream / socket error). That made CC treat
    # truncated/empty responses as success and not retry. Now honor the real
    # status, and on error return a proper Anthropic error payload (so CC retries)
    # instead of an empty-content success message.
    client_status = metrics.get("status", 200)
    if client_status >= 400:
        from .error_mapping import convert_error
        error_payload = convert_error(
            {"error": {"message": metrics.get("error_message") or metrics.get("error_type") or "upstream stream failed"}},
            request_model,
        )
        handler._send_json(client_status, error_payload)
        return

    anth_response = {
        "id": msg_id,
        "type": "message",
        "role": "assistant",
        "model": request_model,
        "content": content,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        },
    }
    handler._send_json(client_status, anth_response)
