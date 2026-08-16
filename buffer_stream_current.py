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
from .nv_breaker import is_ms_fallback_open as _nv_breaker_is_open
from .nv_breaker import record_nv_failure as _nv_breaker_record_failure
from .nv_breaker import record_nv_success as _nv_breaker_record_success
from .nv_breaker import breaker_state as _nv_breaker_state
from .key_manager import KeyManager as _KeyManager
import os

from .config import (
    NVU_BUFFER_MAX_RETRIES, NVU_BUFFER_TIMEOUT_STAIRS,
    NVU_BUFFER_PING_INTERVAL_S, NVU_BUFFER_TOTAL_DEADLINE_S,
    NVU_STREAM_POLL_S,
    NVU_CALLER_KEY_MAP,
    NV_GLM52_MODE_CHAIN,
    NVU_NUM_KEYS,
)

# 预生成 ping bytes（不变量，复用）
_PING_BYTES = b"event: ping\ndata: {}\n\n"

# R-bugfix-F: 全局 RR counter, 让每个 buffer 请求的起始 key 轮转,
# 避免所有请求都从 k1 开始 → k1 被集中冲击 → NVCF 429 累积.
_buf_rr_counter = 0
_buf_rr_lock = __import__("threading").Lock()

def _next_buf_start_idx(num_keys):
    """返回下一个 buffer 请求的起始 key index (0~num_keys-1)."""
    global _buf_rr_counter
    with _buf_rr_lock:
        idx = _buf_rr_counter % num_keys
        _buf_rr_counter += 1
        return idx


class BufferStreamSession:
    """一次 buffer 会话，管理 1-3 次 NVCF 流的完整生命周期。

    用法：
        session = BufferStreamSession(handler, resp, conn, oai_body, metrics,
                                      t_start, request_model, converter)
        session.run()
    """

    def __init__(self, handler, resp, conn, oai_body, metrics,
                 t_start, request_model, converter, is_nonstream=False):
        self.handler = handler
        self.resp = resp              # 首次的 NVCF HTTPResponse（已成功 peek）
        self.conn = conn              # 首次的 NVCF HTTPConnection
        self.oai_body = oai_body
        self.metrics = metrics
        self.t_start = t_start
        self.request_model = request_model
        self.converter = converter
        self.is_nonstream = is_nonstream  # R-glm52-pure: 非流式路径, collect JSON 不发 SSE

        self.buffered_bytes = b""
        self.state = StreamState()
        self.attempt = 0
        self.max_retries = NVU_BUFFER_MAX_RETRIES
        self.timeout_stairs = NVU_BUFFER_TIMEOUT_STAIRS
        self.ping_interval_s = NVU_BUFFER_PING_INTERVAL_S
        # R833: 连续 all_keys_exhausted 计数 — buffer level fail-fast.
        # R829 只检查 KeyManager.is_available() (cooling 状态), 但 NVCF RemoteDisc/529
        # 是 5s 短惩罚不进 long-cooldown, key 在 backoff 期间已恢复 → R829 永不触发.
        # 改看 chain 返回的 all_keys_exhausted 信号: 连续 3 次 → 真全 key 不可用,
        # fail-fast break, 不跑完 5 次 attempt (~421s → ~190s).
        self._last_all_keys_exhausted = False
        self._consecutive_ake_count = 0
        # R834: R833 AKE fail-fast 发生过 → 跳过 WaitQueue (避免 break 后还等 120-240s).
        # R833 只 break for-loop, 但 run() 末尾 WaitQueue 仍在线等 NVCF 恢复, 导致
        # fail-fast 后总耗时仍 ~450s (实测 5 失败请求 451-466s). 加此 flag 让 WaitQueue
        # 检测到 AKE fail-fast 就跳过, 真正做到 ~190s fail-fast exit.
        self._ake_fail_fast = False
        # R827: deadline 锚定 t_start, 非创建时刻. non-stream STAGE1 chain 失败后
        # 进 buffer retry 时, time.time() 已远晚于 t_start (实例 20d7d1b1 耗 244s 才进
        # buffer), 旧逻辑 self.t_start 假设永远从请求开头算却用 time.time()+450s 给
        # 自己预算, 导致 buffer 5×90s 跑过 cc4101 470s 总截止 -> CC 断连 -> 502 穿透
        # (R826 前首次出现 2 个用户可见 502). 修复: deadline = t_start + 450s, 与
        # cc4101 CC4101_STREAM_TOTAL_DEADLINE_S=470s 对齐, 总在 CC 切断前结束.
        self.total_deadline = self.t_start + NVU_BUFFER_TOTAL_DEADLINE_S

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
            # R-bugfix1: SSE 流不设 Connection: close header
            # (避免 cc4101/zcode 连接池提前标记不可复用)
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
        # R-cpu-spin-fix: settimeout(None) — 无限阻塞, 由 select() + deadline 控制.
        # 旧方案 settimeout(NVU_STREAM_POLL_S)=15s, resp.read 超时后 http.client fp
        # 进入 "timed out object" 状态, 后续 resp.read 立即抛异常 -> while True continue
        # 无任何阻塞 -> 100% CPU spin (PID 2323013, 96.8% CPU 死循环 ~2h).
        # 同 R829b cc4101 修复: select() 等 socket 可读后再 read, 不让 fp 进 timed-out 状态.
        if _poll_sock is not None:
            try:
                _poll_sock.settimeout(None)
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

            # R-cpu-spin-fix: select() 等 socket 可读 (5s 一次回循环检 deadline).
            # 防止 resp.read 在 timed-out-object 状态下立即抛异常导致 100% CPU spin.
            if _poll_sock is not None:
                try:
                    _rfds, _, _ = select.select([_poll_sock], [], [], 5.0)
                except Exception:
                    _rfds = []
                if not _rfds:
                    continue  # 5s 内无数据, 回循环顶部检查 deadline, 然后继续等
            try:
                chunk = resp.read(8192)
            except socket.timeout:
                continue
            except OSError as _re:
                # R1704 recv-fallback: http.client fp 崩坏后用 sock.recv 取 buffer 数据.
                # R-cpu-spin-fix: 此分支理论上不再触发 (select 已保证可读), 保留兜底.
                if "timed out object" in str(_re) or "timeout" in str(_re).lower():
                    continue  # 回循环顶部, select 会重新等
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
        ("cc4101-primary", 0, "k1"),   # R-glm52-pure: 启用 k1 (独立代理 7894)
        ("cc4101-primary", 1, "k2"),
        ("cc4101-primary", 2, "k3"),
        ("cc4101-primary", 3, "k4"),
        ("cc4101-primary", 4, "k5"),
    ]

    def _execute_and_drain(self, timeout_s, is_first=False, chain_full_retry=False):
        """
        R-buf5key: 直接调 _try_glm52_mode_chain (NVCF only, 不经 ms_gw fallback).
        按轮转表依次试 4 个 key (k2→k5→k3→k4), 每个最多 150s.
        全部失败后, run() 会调 ms_gw fallback 作最后兜底.

        R813: chain_full_retry=True → 跳过 _KEY_ROTATION override, 让
        _try_glm52_mode_chain 走完整 5key RR (_chain_max_attempts=NVU_NUM_KEYS+2=7),
        充分利用所有可能已恢复的 key. 用于 R806 WAIT-RECOVER 补丁: 旧补丁 pop
        override 后调本方法, 但本方法 line 268 又重设 override → chain 只试 1 key
        → RECOVER retry 1.5s 立即 all_keys_exhausted → WAIT-FAIL → 502. R812 实测
        5 次 RECOVER 全 FAIL, 根因即此.
        """
        _rid = self.metrics.get("request_id", "?")

        if is_first and self.resp is not None and self.conn is not None:
            # 复用外层已成功获取的 resp/conn（仅 non-intercept 路径）
            resp, conn = self.resp, self.conn
        else:
            # R-buf5key: 按轮转表选 key
            _orig_caller = self.metrics.get("caller", "")
            # R-bugfix-F: 起始 key 用全局 RR counter 轮转, 非固定 attempt%5.
            # 旧: attempt=0 时 _rot_idx 永远=0(k1), 所有请求都从 k1 开始,
            # k1 被集中冲击 → NVCF 429 累积 → 其他 key 还好但 k1 被限流.
            # 新: 第一个 attempt (attempt=0) 用 RR counter 选起始 key,
            # 后续 attempt 仍按轮转表顺序 (跳过刚试过的 key).
            if self.attempt == 0:
                _start_idx = _next_buf_start_idx(len(self._KEY_ROTATION))
            else:
                _start_idx = (getattr(self, "_buf_start_idx", 0) + self.attempt) % len(self._KEY_ROTATION)
            self._buf_start_idx = _start_idx if self.attempt == 0 else getattr(self, "_buf_start_idx", 0)
            _rot_idx = _start_idx
            _use_caller, _use_key_idx, _key_desc = self._KEY_ROTATION[_rot_idx]
            if chain_full_retry:
                # R813: WAIT-RECOVER 后走完整 5key chain, 不固定到 _KEY_ROTATION 的一个 key.
                # 不设 nv_start_key_override → _try_glm52_mode_chain 走 RR, _chain_max_attempts=7.
                _log("NV-BUFFER-CHAIN-FULL",
                     f"({self.request_model}) chain_full_retry=True, skip override, "
                     f"start_key=k{_use_key_idx+1} (RR起, NVCF chain full 5key) (req={_rid})")
            else:
                if _use_caller != _orig_caller:
                    _log("NV-BUFFER-KEYSWAP",
                         f"({self.request_model}) attempt={self.attempt+1} swapping caller "
                         f"{_orig_caller}→{_use_caller} (key→{_key_desc}) (req={_rid})")
                self.metrics["caller"] = _use_caller
                # R-bugfix-B: 传入 start_key_override 让 _try_glm52_mode_chain 用
                # _KEY_ROTATION 指定的 key, 而非 RR counter 覆盖.
                self.metrics["nv_start_key_override"] = _use_key_idx

            # R-bugfix-E: _try_glm52_mode_chain 全 key 失败可耗 40-90s,
            # 期间不发 ping, cc4101 30s 超时. 调用前先发 ping.
            if not self.is_nonstream:
                self._send_ping()

            _mapped = self.metrics.get("mapped_model", self.request_model)
            _is_stream = self.oai_body.get("stream", False)
            # R-bugfix-M: 传当前时间作为 chain 的 t_start, 不是 self.t_start (整个请求开始时间).
            # 旧: _try_glm52_mode_chain 内部用 t_start 算 elapsed_in_chain, 如果传 self.t_start,
            # 第 5 次 attempt 时 elapsed=155s > chain_budget=120s -> abort (remaining -35s).
            # 新: 每次 attempt 的 chain 从 0 开始计时, chain_budget 给单次 chain 用.
            _chain_t_start = time.time()
            # R266: NV_GLM52_MODE_CHAIN 未配置时, _try_glm52_mode_chain 立即返回
            # all_keys_exhausted (modes 为空, upstream.py:1378), buffer 5 次 attempt 全
            # 在 0s 内失败 → 无谓 ms_gw fallback (实测 14:13-14:20 窗口 8/10 cc2 请求
            # 走 fallback, nv_key_idx 空, dur 170s+). MODE_CHAIN 为空是设计意图
            # (R-nvonly-post14: glm5_2_nv 走标准 integrate-first 路径), 但 buffer 拦截
            # 仍硬调 mode chain → 必败. 修复: MODE_CHAIN 空时委托 execute_request
            # (与 handlers.py:902 非拦截路径同形, 走 NV-REQ→NV-INTEGRATE 健康路径).
            if NV_GLM52_MODE_CHAIN:
                chain_result = _try_glm52_mode_chain(
                    self.oai_body, _mapped, _rid, self.metrics, _chain_t_start,
                    _is_stream, [], None
                )
            else:
                _log("NV-BUFFER-EXEC-DELEGATE",
                     f"({self.request_model}) MODE_CHAIN empty, delegating to "
                     f"execute_request (integrate-first path) attempt={self.attempt + 1} "
                     f"(req={_rid})")
                chain_result = execute_request(
                    self.handler, self.oai_body, _mapped, _rid, self.metrics,
                    _chain_t_start
                )
            self.metrics["caller"] = _orig_caller  # 恢复
            self.metrics.pop("nv_start_key_override", None)  # R-bugfix-B: 清理 override

            if not (chain_result.success and not chain_result.empty_200):
                _log("NV-BUFFER-EXEC-FAIL",
                     f"({self.request_model}) NVCF chain failed on "
                     f"attempt {self.attempt + 1} key={_key_desc} (req={_rid}), "
                     f"all_keys_exhausted={chain_result.all_keys_exhausted}")
                # R833: 暴露 all_keys_exhausted 给 run() for-loop 做 buffer-level fail-fast
                self._last_all_keys_exhausted = bool(chain_result.all_keys_exhausted)
                return None, "execute_failed"
            # R833: chain 成功 → 清 all_keys_exhausted, 后续成功判定不受影响
            self._last_all_keys_exhausted = False
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

        # R830: glm5_2_nv 大请求硬限制 — NVCF 200K context 限制注定失败, 直接 fallback 不浪费 5×90s=450s
        if self.request_model == "glm5_2_nv":
            _input_chars = self.metrics.get("total_input_chars", 0)
            if _input_chars > 180000:
                _log("NV-BUFFER-INPUT-OVER-LIMIT",
                     f"({self.request_model}) input={_input_chars}c > 180K limit, "
                     f"glm5_2_nv NVCF 200K hard limit, skipping NVCF retries, "
                     f"going fallback directly (req={_rid})")
                _ms_result = self._try_ms_gw_fallback()
                if _ms_result:
                    self.metrics["status"] = 200
                    self.metrics["finish_reason"] = "stop"
                    self.metrics["upstream_type"] = "ms_fallback"
                    self.metrics["fallback_occurred"] = True
                    self.metrics["fallback_from"] = "nv_gw"
                    self.metrics["fallback_to"] = "ms_gw"
                    self.metrics["duration_ms"] = int((time.time() - self.t_start) * 1000)
                    self.metrics["buffer_attempt"] = 0
                    self.metrics["buffer_verdict"] = "input_over_limit_ms_gw"
                    _log("NV-BUFFER-INPUT-OVER-LIMIT-MS-OK",
                         f"({self.request_model}) input over limit, ms_gw served "
                         f"elapsed={self.metrics['duration_ms']}ms (req={_rid})")
                    _log_metrics(self.metrics)
                    return True
                _nv_breaker_record_failure()
                _log("NV-BUFFER-INPUT-OVER-LIMIT-MS-FAIL",
                     f"({self.request_model}) input over limit, ms_gw failed, "
                     f"falling through to NVCF (req={_rid})")

        # R828: nv breaker OPEN -> skip NVCF entirely, go straight to ms_gw.
        # 5 consecutive all_keys_exhausted failures -> OPEN for NVU_MS_FALLBACK_SKIP_S,
        # then HALF_OPEN (one probe allowed). Saves ~500s of futile NVCF retries.
        if _nv_breaker_is_open():
            _log("NV-BUFFER-BREAKER-OPEN",
                 f"({self.request_model}) nv breaker OPEN "
                 f"(state={_nv_breaker_state()}), skipping NVCF, "
                 f"serving ms_gw directly (req={_rid})")
            _ms_result = self._try_ms_gw_fallback()
            if _ms_result:
                self.metrics["status"] = 200
                self.metrics["finish_reason"] = "stop"
                self.metrics["upstream_type"] = "ms_fallback"
                self.metrics["fallback_occurred"] = True
                self.metrics["fallback_from"] = "nv_gw"
                self.metrics["fallback_to"] = "ms_gw"
                self.metrics["duration_ms"] = int((time.time() - self.t_start) * 1000)
                self.metrics["buffer_attempt"] = 0
                self.metrics["buffer_verdict"] = "breaker_open_ms_gw"
                _log("NV-BUFFER-BREAKER-MS-OK",
                     f"({self.request_model}) breaker OPEN, ms_gw served "
                     f"elapsed={self.metrics['duration_ms']}ms (req={_rid})")
                _log_metrics(self.metrics)
                return True
            # ms_gw also failed -- record failure and fall through to NVCF chain
            _nv_breaker_record_failure()
            _log("NV-BUFFER-BREAKER-MS-FAIL",
                 f"({self.request_model}) breaker OPEN but ms_gw failed, "
                 f"falling through to NVCF (req={_rid})")

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

            # R-bugfix-E: 每次 attempt 前发 ping, 重置 cc4101 的 30s read timeout.
            # 旧: 仅 _drain_upstream 内发 ping, 但 _execute_and_drain 的
            # _try_glm52_mode_chain 阶段 (全 key 失败可耗 40-90s) 不发 ping,
            # cc4101 resp.read(8192) 30s 超时 -> recv-fallback 误判连接关闭 ->
            # 返回空 200 (模型未返回任何内容根因).
            if not self.is_nonstream:
                if not self._send_ping():
                    _log("NV-BUFFER-PING-FAIL", f"CC gone before attempt {attempt + 1} (req={_rid})")
                    self.metrics["error_type"] = "client_gone_pre_attempt"
                    self.metrics["status"] = 499
                    self.metrics["duration_ms"] = int((time.time() - self.t_start) * 1000)
                    _log_metrics(self.metrics)
                    return True

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
                # R828: NVCF success -> reset breaker consecutive counter
                _nv_breaker_record_success()
                if self.is_nonstream:
                    # R-glm52-pure: 非流式路径 — 从 buffered anthropic SSE 合成 JSON
                    _log("NV-BUFFER-NONSTREAM-OK",
                         f"({self.request_model}) non-stream verdict={verdict.value}, "
                         f"collecting to JSON (req={_rid})")
                    try:
                        _anth_json = self._synthesize_nonstream_json()
                        self.metrics["status"] = 200
                        self.metrics["finish_reason"] = self.state.finish_reason or "stop"
                        self.metrics["duration_ms"] = int((time.time() - self.t_start) * 1000)
                        self.metrics["buffer_attempt"] = attempt + 1
                        self.metrics["buffer_verdict"] = verdict.value
                        self.metrics["buffer_total_retries"] = attempt
                        _log("NV-BUFFER-SUCCESS",
                             f"({self.request_model}) non-stream JSON synthesized "
                             f"after {attempt + 1} attempt(s), "
                             f"elapsed={self.metrics['duration_ms']}ms (req={_rid})")
                        _log_metrics(self.metrics)
                        self.handler._send_json(200, _anth_json)
                        return True
                    except (BrokenPipeError, ConnectionResetError, OSError) as e:
                        _log("NV-BUFFER-NONSTREAM-FAIL",
                             f"({self.request_model}) CC gone during JSON send: {e} (req={_rid})")
                        self.metrics["error_type"] = "client_gone_during_flush"
                        self.metrics["status"] = 499
                        self.metrics["duration_ms"] = int((time.time() - self.t_start) * 1000)
                        _log_metrics(self.metrics)
                        return True
                # flush buffer 给 CC (流式路径, 现状)
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

            # R829: 全 key cooling → fail-fast, 不继续无谓重试
            _all_cooling = all(
                not _KeyManager.is_available(self.request_model, k)
                for k in range(NVU_NUM_KEYS)
            )
            if _all_cooling:
                _log("NV-BUFFER-ALL-COOLING",
                     f"({self.request_model}) all {NVU_NUM_KEYS} keys cooling "
                     f"after attempt {attempt + 1}, fail-fast "
                     f"(state={_nv_breaker_state()}, req={_rid})")
                break

            # R833: 连续 all_keys_exhausted fail-fast — 补 R829 的盲区.
            # R829 检查 KeyManager.is_available() (cooling 状态), 但 NVCF RemoteDisc/529
            # 触发 5s 短惩罚 (mark_transport_error, 不累计 conn_count), backoff 期间 key
            # 已恢复 → is_available()=True → R829 永不触发. 改看 chain 真实返回信号:
            # 连续 N 次 all_keys_exhausted → 全 key 真不可用 (非瞬态), fail-fast break.
            if self._last_all_keys_exhausted:
                self._consecutive_ake_count += 1
            else:
                self._consecutive_ake_count = 0
            _ake_fast_threshold = int(os.environ.get("NVU_BUFFER_AKE_FAST_N", "3"))
            if self._consecutive_ake_count >= _ake_fast_threshold:
                _log("NV-BUFFER-AKE-FASTM",
                     f"({self.request_model}) {self._consecutive_ake_count} consecutive "
                     f"all_keys_exhausted (>= {_ake_fast_threshold}), fail-fast "
                     f"(state={_nv_breaker_state()}, req={_rid})")
                # R834: 标记 AKE fail-fast, 让 WaitQueue 跳过等待 (见 run() 末尾)
                self._ake_fail_fast = True
                break

            # 失败，准备重试
            if attempt < self.max_retries - 1:
                _log("NV-BUFFER-RETRY",
                     f"({self.request_model}) attempt={attempt + 1} failed "
                     f"({verdict.value if verdict else reason}), resetting for retry "
                     f"(req={_rid})")
                self._reset_for_retry()
                # R-bugfix-H: attempt 间退避等待. RemoteDisconnected/429 全挂时,
                # 立即重试大概率再全挂 (NVCF 还在过载). 等几秒让 transport penalty
                # 过期 + NVCF 恢复. 发 ping 保持 cc4101 连接不超时.
                _backoff = min(5 * (attempt + 1), 15)  # 5s, 10s, 15s 递增, 最多 15s
                _log("NV-BUFFER-BACKOFF",
                     f"({self.request_model}) backing off {_backoff}s before attempt {attempt + 2} (req={_rid})")
                _bo_end = time.time() + _backoff
                while time.time() < _bo_end:
                    if not self.is_nonstream:
                        self._send_ping()
                    time.sleep(min(5, _bo_end - time.time()))
            else:
                _log("NV-BUFFER-LAST-FAIL",
                     f"({self.request_model}) attempt={attempt + 1} was last, "
                     f"exhausted (req={_rid})")
                # R828: all NVCF retries exhausted -> record breaker failure.
                # 5 consecutive -> breaker OPENs, next request goes to ms_gw directly.
                _nv_breaker_record_failure()
                _log("NV-BREAKER-RECORD",
                     f"({self.request_model}) buffer exhausted, "
                     f"recording nv failure "
                     f"(state={_nv_breaker_state()}, req={_rid})")

        # R-rebuild Phase 4: 4-key 全挂后, 等 NVCF 恢复再重试, 不走 ms_gw
        _wait_enabled = os.environ.get("NVU_WAIT_QUEUE_ENABLED", "0") == "1"
        _wait_max = int(os.environ.get("NVU_WAIT_QUEUE_MAX_WAIT", "120"))

        # R834-BUGFIX (R843): AKE fail-fast 触发后跳过 WaitQueue.
        # R833/834 在 line ~616 设了 self._ake_fail_fast=True 并注释"让 WaitQueue
        # 跳过等待 (见 run() 末尾)", 但 run() 末尾从未消费该标记 → AKE fail-fast
        # 在 3 次全挂 (~120s) 后 break, 仍走 WAIT 180s + ms_gw fallback (~260s),
        # 总耗时从预期 ~120s 膨胀到 ~460s. 实测 d7259a82/b4d27aa4 各 462s/459s.
        # 修复: AKE fail-fast = 连续 N 次 all_keys_exhausted 说明 NVCF 后端真不可用,
        # 180s 很大概率不恢复 (实测两例均如此), 跳过 WAIT 直接走 ms_gw fallback.
        if _wait_enabled and self._ake_fail_fast:
            _log("NV-BUFFER-AKE-SKIP-WAIT",
                 f"({self.request_model}) AKE fail-fast active, skipping WaitQueue "
                 f"(would waste up to {_wait_max}s), going to ms_gw (req={_rid})")
            _wait_enabled = False

        # R829: 全 key 长冷却 (>30s) → 跳过 WaitQueue, 直接 ms_gw
        if _wait_enabled:
            _long_cooling = all(
                _KeyManager.get_state(self.request_model, k)["cooldown_remaining_s"] > 30
                for k in range(NVU_NUM_KEYS)
            )
            if _long_cooling:
                _log("NV-BUFFER-SKIP-WAIT",
                     f"({self.request_model}) all keys long-cooling (>30s), ",
                     f"skipping WaitQueue, going to ms_gw (req={_rid})")
                _wait_enabled = False

        if _wait_enabled:
            _log("NV-BUFFER-WAIT",
                 f"({self.request_model}) all {self.max_retries} NVCF attempts failed, "
                 f"waiting up to {_wait_max}s for recovery (req={_rid})")

            try:
                from .probe_worker import wait_for_recovery, clear_recovery_event
                clear_recovery_event()
                _recovered = wait_for_recovery(timeout_s=_wait_max)
            except Exception as e:
                _log("NV-BUFFER-WAIT-ERR",
                     f"({self.request_model}) wait_for_recovery error: {e} (req={_rid})")
                _recovered = False

            if _recovered:
                # R806: WAIT-RECOVER 后清掉 nv_start_key_override, 让 chain 走完整
                # 5key RR (NV_GLM52_MODE_CHAIN=pexec_us_rr, 一档), 而非被 _KEY_ROTATION
                # 固定到刚 probe 恢复的那 1 个 key. 旧逻辑 (R-bugfix-B 引入 override):
                # _try_glm52_mode_chain 见 override 走 BUFFER_OVERRIDE 分支
                # _chain_max_attempts=1, 只试 1 key, 失败即 all_keys_exhausted ->
                # WAIT-FAIL -> 502. 实测 2026-08-05 10:13-10:15 (req=357b71d9):
                # 5key 全挂 + wait 180s + 仅 k3 恢复 -> retry k3 一次 RemoteDisc
                # -> 502 (但同期其他 req 用 k4/k2 立即成功). 根因: 其他 4 key 早已
                # 优化点 mark_success 重置状态, 但 override 把 retry 困在 probe 的
                # 那一个 key. 修复: WAIT-RECOVER 后用完整 chain 充分利用所有恢复的 key.
                _remaining = self.total_deadline - time.time()
                _log("NV-BUFFER-WAIT-RECOVER",
                     f"({self.request_model}) key recovered, retrying NVCF with full "
                     f"5-key chain (override cleared), remaining={_remaining:.0f}s (req={_rid})")
                # verdict/reason 默认 None: 跳过分支 (剩余时间不足) -> 走 WAIT-FAIL
                verdict, reason = None, None
                if _remaining < 30:
                    # 剩余预算不足以跑 chain (~chain_budget_s 默认 120s), 不浪费配额
                    _log("NV-BUFFER-WAIT-NO-TIME",
                         f"({self.request_model}) only {_remaining:.0f}s left after wait, "
                         f"skip retry (req={_rid})")
                else:
                    self._reset_for_retry()
                    self.attempt = 0  # 重置 attempt 以从头选 healthy key
                    # R813 修复: 旧 R806 补丁在此 pop override 后调 _execute_and_drain,
                    # 但 _execute_and_drain 内部 line 268 又重设 override → chain 只试
                    # 1 key → RECOVER retry 1.5s 立即 all_keys_exhausted → WAIT-FAIL.
                    # R812 实测 5 次 RECOVER 全 FAIL 根因即此. 修复: 传 chain_full_retry=True
                    # 让 _execute_and_drain 跳过 override 设置 → chain 走完整 5key RR
                    # (_chain_max_attempts=NVU_NUM_KEYS+2=7).
                    verdict, reason = self._execute_and_drain(
                        self.timeout_stairs[0], is_first=False, chain_full_retry=True
                    )
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
                    self.metrics["status"] = 200
                    self.metrics["finish_reason"] = self.state.finish_reason or "stop"
                    self.metrics["duration_ms"] = int((time.time() - self.t_start) * 1000)
                    self.metrics["buffer_attempt"] = self.max_retries + 1
                    self.metrics["buffer_verdict"] = "wait_recovery_success"
                    _log("NV-BUFFER-WAIT-OK",
                         f"({self.request_model}) recovered after wait, "
                         f"elapsed={self.metrics['duration_ms']}ms (req={_rid})")
                    _log_metrics(self.metrics)
                    return True
                else:
                    _log("NV-BUFFER-WAIT-FAIL",
                         f"({self.request_model}) retry after recovery still failed "
                         f"(verdict={verdict.value if verdict else reason}) (req={_rid})")

        # ms_gw fallback (feature flag: NVU_DISABLE_MS_FALLBACK=1 时跳过)
        _disable_ms = os.environ.get("NVU_DISABLE_MS_FALLBACK", "0") == "1"
        if not _disable_ms:
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

            _log("NV-BUFFER-MS-FB-FAIL",
                 f"({self.request_model}) ms_gw fallback also failed, "
                 f"sending error to CC (req={_rid})")
        else:
            _log("NV-BUFFER-NO-MS",
                 f"({self.request_model}) ms_gw fallback disabled, "
                 f"sending error to CC (req={_rid})")

        # 发 error 给 CC
        err_evt = _sse_bytes("error", {
            "type": "error",
            "error": {
                "type": "api_error",
                "message": f"upstream stream incomplete after {self.max_retries} NVCF retries"
                           + ("" if _disable_ms else " + ms_gw fallback")
                           + f" (last verdict: {verdict.value if verdict else reason})",
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

    def _synthesize_nonstream_json(self):
        """R-glm52-pure: 从 buffered anthropic SSE bytes 合成非流式 anthropic JSON.

        buffered_bytes 是 OaiSseToAnthropicConverter 产出的 anthropic SSE event 流.
        解析每个 event 的 data, 提取 content_block_delta/reasoning/text/tool_use,
        合成 anthropic message JSON (非流式格式).
        """
        import json as _json
        import uuid as _uuid
        content_parts = []
        text_buf = []
        thinking_buf = []
        tool_calls = []  # [{id, name, input}]
        cur_tool = None
        cur_tool_raw = ""
        finish_reason = self.state.finish_reason or "stop"
        msg_id = "msg_" + _uuid.uuid4().hex[:24]

        # 解析 buffered SSE bytes
        try:
            sse_text = self.buffered_bytes.decode("utf-8", errors="replace")
        except Exception:
            sse_text = ""
        for line in sse_text.split("\n"):
            if not line.startswith("data: "):
                continue
            data_str = line[6:].strip()
            if not data_str or data_str == "[DONE]":
                continue
            try:
                evt = _json.loads(data_str)
            except _json.JSONDecodeError:
                continue
            etype = evt.get("type", "")
            if etype == "content_block_start":
                blk = evt.get("content_block", {})
                if blk.get("type") == "tool_use":
                    cur_tool = {"id": blk.get("id", ""), "name": blk.get("name", ""), "input": {}}
                    cur_tool_raw = ""
            elif etype == "content_block_delta":
                d = evt.get("delta", {})
                if d.get("type") == "text_delta":
                    text_buf.append(d.get("text", ""))
                elif d.get("type") == "thinking_delta":
                    thinking_buf.append(d.get("thinking", ""))
                elif d.get("type") == "input_json_delta":
                    cur_tool_raw += d.get("partial_json", "")
            elif etype == "content_block_stop":
                if cur_tool is not None:
                    try:
                        cur_tool["input"] = _json.loads(cur_tool_raw) if cur_tool_raw else {}
                    except _json.JSONDecodeError:
                        cur_tool["input"] = {"raw": cur_tool_raw}
                    tool_calls.append(cur_tool)
                    cur_tool = None
                    cur_tool_raw = ""
            elif etype == "message_delta":
                d = evt.get("delta", {})
                if d.get("stop_reason"):
                    finish_reason = d["stop_reason"]

        # 合成 content
        content = []
        thinking_text = "".join(thinking_buf)
        if thinking_text:
            content.append({"type": "thinking", "thinking": thinking_text,
                            "signature": "ErUBCkYIi3Na0nDg"})
        text_text = "".join(text_buf)
        if text_text:
            content.append({"type": "text", "text": text_text})
        for tc in tool_calls:
            content.append({"type": "tool_use", "id": tc["id"],
                            "name": tc["name"], "input": tc.get("input", {})})
        if not content:
            content.append({"type": "text", "text": ""})

        stop_reason = "end_turn"
        if finish_reason == "max_tokens":
            stop_reason = "max_tokens"
        elif finish_reason in ("tool_use", "tool_calls"):
            stop_reason = "tool_use"

        return {
            "id": msg_id, "type": "message", "role": "assistant",
            "model": self.request_model, "content": content,
            "stop_reason": stop_reason, "stop_sequence": None,
            "usage": {"input_tokens": 0, "output_tokens": 0,
                      "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0},
        }

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
