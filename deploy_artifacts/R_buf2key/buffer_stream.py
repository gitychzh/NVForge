#!/usr/bin/env python3
"""R-buffer: cc2 buffer-then-flush 模式 (2026-07-27)

对 cc4101-primary caller 的流式请求，不立即转发 chunks 给 CC，
buffer 在内存里直到 judge_stream() 判定三者齐全再一次性 flush。

核心逻辑：
  1. 发 SSE 200 headers 给 CC
  2. 每 30s 发 event:ping 占位符重置 SDK idle timer
  3. 从 NVCF 读流，feed 给 converter，buffer 输出 bytes（不转发给 CC）
  4. 流结束 → judge_stream() 判定
  5. 成功 → flush buffer + finish() 给 CC
  6. 失败 → 废弃 buffer，同 key 重试（150s→200s→200s）
  7. 3 次全败 → event:error 给 CC
  8. 总预算 580s，在 R2254 watchdog 600s 之内
"""

import json
import socket
import time

from .logger import _log, _log_metrics
from .format.oai_to_anth import OaiSseToAnthropicConverter, _sse_bytes
from .stream_success_judge import (
    StreamState, judge_stream, should_retry, verdict_summary,
    update_state_from_chunk, mark_done, mark_connection_closed,
)
from .upstream import execute_request, _try_glm52_mode_chain, _ms_fallback_request, UpstreamResult
import os

from .config import (
    NVU_BUFFER_MAX_RETRIES, NVU_BUFFER_TIMEOUT_STAIRS,
    NVU_BUFFER_PING_INTERVAL_S, NVU_BUFFER_TOTAL_DEADLINE_S,
    NVU_STREAM_POLL_S,
    NVU_CALLER_KEY_MAP,
)

# 预生成 ping bytes（不变量，复用）
_PING_BYTES = b"event: ping\ndata: {}\n\n"


class BufferStreamSession:
    """一次 buffer 会话，管理 1-3 次 NVCF 流的完整生命周期。

    用法：
        session = BufferStreamSession(handler, resp, conn, oai_body, metrics,
                                      t_start, request_model, converter)
        session.run()
    """

    def __init__(self, handler, resp, conn, oai_body, metrics,
                 t_start, request_model, converter):
        self.handler = handler
        self.resp = resp              # 首次的 NVCF HTTPResponse（已成功 peek）
        self.conn = conn              # 首次的 NVCF HTTPConnection
        self.oai_body = oai_body
        self.metrics = metrics
        self.t_start = t_start
        self.request_model = request_model
        self.converter = converter

        self.buffered_bytes = b""
        self.state = StreamState()
        self.attempt = 0
        self.max_retries = NVU_BUFFER_MAX_RETRIES
        self.timeout_stairs = NVU_BUFFER_TIMEOUT_STAIRS
        self.ping_interval_s = NVU_BUFFER_PING_INTERVAL_S
        self.total_deadline = time.time() + NVU_BUFFER_TOTAL_DEADLINE_S

    def _send_ping(self):
        """发 anthropic event:ping 占位符给 CC，重置 SDK idle timer。"""
        try:
            self.handler.wfile.write(_PING_BYTES)
            self.handler.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError) as e:
            _log("WARN", f"({self.request_model}) NV-BUFFER-PING-FAIL "
                f"CC gone during ping: {e} "
                f"(req={self.metrics.get('request_id', '?')})")
            return False
        return True

    def _send_sse_headers(self):
        """发 200 + SSE headers 给 CC（commit point）。"""
        try:
            self.handler.send_response(200)
            self.handler.send_header("Content-Type", "text/event-stream")
            self.handler.send_header("Cache-Control", "no-cache")
            self.handler.send_header("Connection", "close")
            self.handler.close_connection = True
            self.handler.end_headers()
        except (BrokenPipeError, ConnectionResetError, OSError) as e:
            _log("ERR", f"({self.request_model}) NV-BUFFER-HEADER-FAIL "
                f"CC gone before SSE headers: {e}")
            self.metrics["error_type"] = "client_gone_pre_stream"
            self.metrics["status"] = 499
            self.metrics["duration_ms"] = int((time.time() - self.t_start) * 1000)
            _log_metrics(self.metrics)
            return False
        return True

    def _drain_upstream(self, resp, conn, timeout_s):
        """
        从 NVCF 读流，feed 给 converter，buffer 输出 bytes，不转发给 CC。
        用 StreamState 跟踪，结束时 judge_stream() 判定。

        返回: (verdict, reason)
          verdict = StreamVerdict 枚举值
          reason = str | None（超时/异常信息）
        """
        # 设置 poll socket
        _poll_sock = None
        try:
            _poll_sock = conn.sock
            if _poll_sock is None and resp is not None:
                _poll_sock = resp.fp.raw._sock
        except Exception:
            _poll_sock = None
        if _poll_sock is not None:
            try:
                _poll_sock.settimeout(NVU_STREAM_POLL_S)
            except Exception:
                pass

        deadline = time.time() + timeout_s
        last_ping = time.time()
        sse_buffer = ""
        _rid = self.metrics.get("request_id", "?")

        while True:
            # 总 deadline 检查
            now = time.time()
            if now > deadline:
                return judge_stream(self.state), "total_deadline"
            if now > self.total_deadline:
                return judge_stream(self.state), "global_deadline"

            # 用 socket.timeout 的空隙发 ping
            if now - last_ping >= self.ping_interval_s:
                if not self._send_ping():
                    return judge_stream(self.state), "client_gone_ping"
                last_ping = now

            try:
                chunk = resp.read(8192)
            except socket.timeout:
                continue
            except OSError as _re:
                # R1704 recv-fallback：http.client fp 崩坏后用 sock.recv 取 buffer 数据
                if "timed out object" in str(_re) or "timeout" in str(_re).lower():
                    try:
                        _sc = resp.fp.raw._sock
                        _peek = _sc.recv(8192, socket.MSG_PEEK)
                    except Exception:
                        _peek = b''
                    if _peek:
                        try:
                            chunk = _sc.recv(8192)
                        except Exception:
                            chunk = b''
                        if not chunk:
                            continue
                    else:
                        continue
                else:
                    mark_connection_closed(self.state, _re)
                    return judge_stream(self.state), f"OSError:{type(_re).__name__}"
            except Exception as _e:
                mark_connection_closed(self.state, _e)
                return judge_stream(self.state), f"Exception:{type(_e).__name__}"

            if not chunk:
                # 连接正常关闭（可能是 NVCF 发完了但没发 [DONE]）
                mark_connection_closed(self.state)
                return judge_stream(self.state), "connection_closed"

            sse_buffer += chunk.decode("utf-8", errors="replace")

            # parse complete SSE events
            while "\n\n" in sse_buffer:
                event_str, sse_buffer = sse_buffer.split("\n\n", 1)
                data_str = ""
                for line in event_str.split("\n"):
                    if line.startswith("data:"):
                        data_str = line[5:].strip()

                if not data_str:
                    continue
                if data_str == "[DONE]":
                    mark_done(self.state)
                    continue

                try:
                    chunk_data = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                update_state_from_chunk(self.state, chunk_data)

                # feed converter, buffer output（不转发给 CC）
                out_bytes = self.converter.feed_chunk(chunk_data)
                if out_bytes:
                    self.buffered_bytes += out_bytes

            # 提前结束：已收到 finish_reason + [DONE]
            if self.state.finish_reason and self.state.saw_done:
                return judge_stream(self.state), None

    # R-buf5key: 5-key 轮转表 — 每项 = (caller_name, key_idx, proxy_desc)
    # key2=cc4101-primary(mihomo-7895), key3=hermes(7896), key4=openclaw(7897),
    # key5=opencode(7899), key1=未绑定(7894). 避开 key1(全局备用).
    _KEY_ROTATION = [
        ("cc4101-primary", 1, "k2"),   # 原始 key
        ("opencode",       4, "k5"),   # 不同代理 IP
        ("hermes",         2, "k3"),   # 第三个代理 IP
        ("openclaw",       3, "k4"),   # 第四个代理 IP
    ]

    def _execute_and_drain(self, timeout_s, is_first=False):
        """
        R-buf5key: 直接调 _try_glm52_mode_chain (NVCF only, 不经 ms_gw fallback).
        按轮转表依次试 4 个 key (k2→k5→k3→k4), 每个最多 150s.
        全部失败后, run() 会调 ms_gw fallback 作最后兜底.
        """
        _rid = self.metrics.get("request_id", "?")

        if is_first and self.resp is not None and self.conn is not None:
            # 复用外层已成功获取的 resp/conn（仅 non-intercept 路径）
            resp, conn = self.resp, self.conn
        else:
            # R-buf5key: 按轮转表选 key
            _orig_caller = self.metrics.get("caller", "")
            _rot_idx = self.attempt % len(self._KEY_ROTATION)
            _use_caller, _use_key_idx, _key_desc = self._KEY_ROTATION[_rot_idx]
            if _use_caller != _orig_caller:
                _log("NV-BUFFER-KEYSWAP",
                     f"({self.request_model}) attempt={self.attempt+1} swapping caller "
                     f"{_orig_caller}→{_use_caller} (key→{_key_desc}) (req={_rid})")
            self.metrics["caller"] = _use_caller

            _mapped = self.metrics.get("mapped_model", self.request_model)
            _is_stream = self.oai_body.get("stream", False)
            chain_result = _try_glm52_mode_chain(
                self.oai_body, _mapped, _rid, self.metrics, self.t_start,
                _is_stream, [], None
            )
            self.metrics["caller"] = _orig_caller  # 恢复

            if not (chain_result.success and not chain_result.empty_200):
                _log("NV-BUFFER-EXEC-FAIL",
                     f"({self.request_model}) NVCF chain failed on "
                     f"attempt {self.attempt + 1} key={_key_desc} (req={_rid}), "
                     f"all_keys_exhausted={chain_result.all_keys_exhausted}")
                return None, "execute_failed"
            resp = chain_result.resp
            conn = chain_result.conn
            self.metrics["nv_key_idx"] = chain_result.nv_key_idx
            self.metrics["upstream_type"] = chain_result.upstream_type

        verdict, reason = self._drain_upstream(resp, conn, timeout_s)

        try:
            conn.close()
        except Exception:
            pass

        return verdict, reason

    def _reset_for_retry(self):
        """重试前重置 buffer + state + converter。"""
        self.buffered_bytes = b""
        self.state = StreamState()
        self.converter = OaiSseToAnthropicConverter(
            self.request_model,
            request_id=self.metrics.get("request_id")
        )

    def run(self):
        """
        主入口：运行 buffer+判定+重试循环。

        R-buf2key: SSE headers 已由 handler 发送 (intercept 时),
        这里只做 NVCF key2→key5 重试 + drain + flush.
        返回 True = 成功（已 flush 给 CC）
        返回 False = 2 次全败（已发 error 给 CC）
        """
        _rid = self.metrics.get("request_id", "?")
        _caller = self.metrics.get("caller", "?")

        # R-buf2key: handler 已发 SSE headers, 跳过 _send_sse_headers

        _log("NV-BUFFER-START",
             f"({self.request_model}) caller={_caller} max_retries={self.max_retries} "
             f"stairs={self.timeout_stairs} ping={self.ping_interval_s}s "
             f"total_deadline={NVU_BUFFER_TOTAL_DEADLINE_S}s (req={_rid})")

        for attempt in range(self.max_retries):
            self.attempt = attempt
            timeout_s = self.timeout_stairs[min(attempt, len(self.timeout_stairs) - 1)]

            # 不超过总 deadline
            remaining = self.total_deadline - time.time()
            if remaining < 30:
                _log("NV-BUFFER-NO-TIME",
                     f"({self.request_model}) only {remaining:.0f}s left, "
                     f"aborting (req={_rid})")
                break
            if timeout_s > remaining:
                timeout_s = max(30, int(remaining))

            _log("NV-BUFFER-ATTEMPT",
                 f"({self.request_model}) attempt={attempt + 1}/{self.max_retries} "
                 f"timeout={timeout_s}s caller={_caller} "
                 f"input={self.metrics.get('total_input_chars', 0)}c "
                 f"thinking={bool(self.metrics.get('thinking_type'))} "
                 f"(req={_rid})")

            verdict, reason = self._execute_and_drain(
                timeout_s, is_first=(attempt == 0)
            )

            _log("NV-BUFFER-VERDICT",
                 f"({self.request_model}) attempt={attempt + 1} "
                 f"verdict={verdict.value if verdict else 'None'} "
                 f"reason={reason} "
                 f"content={self.state.content_chars}c "
                 f"reasoning={self.state.reasoning_chars}c "
                 f"tool(id={self.state.saw_tool_call_id},"
                 f"args={self.state.saw_tool_call_args}) "
                 f"fr={self.state.finish_reason} done={self.state.saw_done} "
                 f"closed={self.state.connection_closed} "
                 f"buffered={len(self.buffered_bytes)}b "
                 f"elapsed={int(time.time() - self.t_start)}s "
                 f"(req={_rid})")

            # 成功判定
            if verdict is not None and not should_retry(verdict):
                # flush buffer 给 CC
                _log("NV-BUFFER-FLUSH",
                     f"({self.request_model}) flushing {len(self.buffered_bytes)}b "
                     f"to CC, verdict={verdict.value} "
                     f"(req={_rid})")
                try:
                    if self.buffered_bytes:
                        self.handler.wfile.write(self.buffered_bytes)
                        self.handler.wfile.flush()
                except (BrokenPipeError, ConnectionResetError, OSError) as e:
                    _log("NV-BUFFER-FLUSH-FAIL",
                         f"({self.request_model}) CC gone during flush: {e} "
                         f"(req={_rid})")
                    self.metrics["error_type"] = "client_gone_during_flush"
                    self.metrics["status"] = 499
                    self.metrics["duration_ms"] = int((time.time() - self.t_start) * 1000)
                    self.metrics["buffer_attempt"] = attempt + 1
                    self.metrics["buffer_verdict"] = verdict.value
                    _log_metrics(self.metrics)
                    return True  # 内容已发，CC 自己断

                # 发终末事件
                fin = self.converter.finish(
                    interrupted=False, zombie=False,
                    input_tokens_real=0,
                    flushed_content_chars=self.state.content_chars,
                )
                if fin:
                    try:
                        self.handler.wfile.write(fin)
                        self.handler.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError, OSError):
                        pass

                self.metrics["status"] = 200
                self.metrics["finish_reason"] = self.state.finish_reason or "stop"
                self.metrics["duration_ms"] = int((time.time() - self.t_start) * 1000)
                self.metrics["buffer_attempt"] = attempt + 1
                self.metrics["buffer_verdict"] = verdict.value
                self.metrics["buffer_total_retries"] = attempt
                _log("NV-BUFFER-SUCCESS",
                     f"({self.request_model}) flushed {len(self.buffered_bytes)}b "
                     f"after {attempt + 1} attempt(s), "
                     f"elapsed={self.metrics['duration_ms']}ms "
                     f"(req={_rid})")
                _log_metrics(self.metrics)
                return True

            # 失败，准备重试
            if attempt < self.max_retries - 1:
                _log("NV-BUFFER-RETRY",
                     f"({self.request_model}) attempt={attempt + 1} failed "
                     f"({verdict.value if verdict else reason}), resetting for retry "
                     f"(req={_rid})")
                self._reset_for_retry()
            else:
                _log("NV-BUFFER-LAST-FAIL",
                     f"({self.request_model}) attempt={attempt + 1} was last, "
                     f"exhausted (req={_rid})")

        # 全部 NVCF key 失败，尝试 ms_gw fallback (最后兜底, 不让 CC 拿 502)
        _log("NV-BUFFER-EXHAUSTED",
             f"({self.request_model}) all {self.max_retries} NVCF attempts failed, "
             f"trying ms_gw fallback (req={_rid})")

        _ms_result = self._try_ms_gw_fallback()
        if _ms_result:
            self.metrics["status"] = 200
            self.metrics["finish_reason"] = "stop"
            self.metrics["upstream_type"] = "ms_fallback"
            self.metrics["fallback_occurred"] = True
            self.metrics["fallback_from"] = "nv_gw"
            self.metrics["fallback_to"] = "ms_gw"
            self.metrics["duration_ms"] = int((time.time() - self.t_start) * 1000)
            self.metrics["buffer_attempt"] = self.max_retries
            self.metrics["buffer_verdict"] = "ms_gw_fallback"
            _log("NV-BUFFER-MS-FB-OK",
                 f"({self.request_model}) ms_gw saved request after "
                 f"{self.max_retries} NVCF failures, "
                 f"elapsed={self.metrics['duration_ms']}ms (req={_rid})")
            _log_metrics(self.metrics)
            return True

        # ms_gw 也失败了，发 error 给 CC
        _log("NV-BUFFER-MS-FB-FAIL",
             f"({self.request_model}) ms_gw fallback also failed, "
             f"sending error to CC (req={_rid})")

        err_evt = _sse_bytes("error", {
            "type": "error",
            "error": {
                "type": "api_error",
                "message": f"upstream stream incomplete after {self.max_retries} NVCF retries "
                           f"+ ms_gw fallback (last verdict: {verdict.value if verdict else reason})",
            },
        })
        try:
            self.handler.wfile.write(err_evt)
            self.handler.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

        self.metrics["status"] = 502
        self.metrics["error_type"] = "buffer_exhausted"
        self.metrics["error_message"] = f"last verdict: {verdict.value if verdict else reason}"
        self.metrics["duration_ms"] = int((time.time() - self.t_start) * 1000)
        self.metrics["buffer_attempt"] = self.attempt + 1
        self.metrics["buffer_verdict"] = verdict.value if verdict else "None"
        self.metrics["buffer_total_retries"] = self.attempt + 1
        _log_metrics(self.metrics)
        return False

    def _try_ms_gw_fallback(self):
        """R-buf5key: 所有 NVCF key 失败后, 调 _ms_fallback_request 取 ms_gw 流,
        再走 _drain_upstream + converter buffer → flush 给 CC.
        成功 = True (已 flush), 失败 = False.
        """
        _rid = self.metrics.get("request_id", "?")
        _mapped = self.metrics.get("mapped_model", self.request_model)

        try:
            from .upstream import _ms_fallback_request
            _log("NV-BUFFER-MS-FB-ATTEMPT",
                 f"({self.request_model}) attempting ms_gw fallback "
                 f"after {self.max_retries} NVCF failures (req={_rid})")

            # 检查剩余时间
            _remaining = self.total_deadline - time.time()
            if _remaining < 30:
                _log("NV-BUFFER-MS-FB-SKIP",
                     f"({self.request_model}) only {_remaining:.0f}s left, "
                     f"skipping ms_gw (req={_rid})")
                return False

            _ms_timeout = min(int(_remaining), 150)
            ok, ms_result = _ms_fallback_request(
                self.oai_body, _mapped, _rid, self.metrics, self.t_start
            )
            if not ok or ms_result is None:
                _log("NV-BUFFER-MS-FB-FAIL",
                     f"({self.request_model}) ms_gw request failed (req={_rid})")
                return False

            # ms_gw 返回 openai SSE 流, 走同样的 drain → converter → buffer → flush
            self._reset_for_retry()
            _log("NV-BUFFER-MS-FB-DRAIN",
                 f"({self.request_model}) draining ms_gw stream "
                 f"timeout={_ms_timeout}s (req={_rid})")

            verdict, reason = self._drain_upstream(
                ms_result.resp, ms_result.conn, _ms_timeout
            )
            try:
                ms_result.conn.close()
            except Exception:
                pass

            if verdict is not None and not should_retry(verdict):
                # flush buffer 给 CC
                try:
                    if self.buffered_bytes:
                        self.handler.wfile.write(self.buffered_bytes)
                        self.handler.wfile.flush()
                except (BrokenPipeError, ConnectionResetError, OSError):
                    pass

                fin = self.converter.finish(
                    interrupted=False, zombie=False,
                    input_tokens_real=0,
                    flushed_content_chars=self.state.content_chars,
                )
                if fin:
                    try:
                        self.handler.wfile.write(fin)
                        self.handler.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError, OSError):
                        pass
                return True

            _log("NV-BUFFER-MS-FB-FAIL",
                 f"({self.request_model}) ms_gw stream also failed: "
                 f"verdict={verdict.value if verdict else reason} (req={_rid})")
            return False

        except Exception as e:
            _log("NV-BUFFER-MS-FB-ERR",
                 f"({self.request_model}) ms_gw fallback exception: {e} (req={_rid})")
            return False
