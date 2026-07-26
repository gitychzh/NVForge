#!/usr/bin/env python3
"""
Stream success/failure判定函数 — 放在 nv_gw 或 cc4101 的流式处理层。

核心思想：在流处理过程中累积状态，流结束时（正常或异常）一次性判定。
判定结果决定：重试 / 放行 / 标记 zombie。

成功 = 有实际内容 + 合法 finish_reason + [DONE]，三者齐全。
任何缺失 = 失败，按缺失组合分类，驱动不同重试策略。
"""

import json
import time
from dataclasses import dataclass, field
from enum import Enum


class StreamVerdict(Enum):
    """流结束后的最终判定"""
    # ── 成功路径（6 种）──
    SUCCESS_TEXT = "success_text"                      # #1: content>0, stop, [DONE]
    SUCCESS_THINKING = "success_thinking"               # #2: content>0 + reasoning>0, stop, [DONE]
    SUCCESS_THINKING_ONLY = "success_thinking_only"     # #3: content=0 + reasoning>0, stop, [DONE]
    SUCCESS_LENGTH = "success_length"                   # #4: content≥0, length, [DONE]
    SUCCESS_TOOL_CALL = "success_tool_call"             # #5: 真tool_call delta, tool_calls, [DONE]
    SUCCESS_THINKING_TOOL = "success_thinking_tool"     # #6: reasoning>0 + 真tool_call, tool_calls, [DONE]

    # ── 失败路径（6 种）──
    ZOMBIE_PARTIAL = "zombie_partial"                   # Form B: 有内容但无finish_reason无[DONE]
    ZOMBIE_EMPTY = "zombie_empty"                        # 零内容, 有finish_reason(可能+有[DONE])
    FAKE_TOOL_CALL = "fake_tool_call"                   # R1932: finish_reason=tool_calls但无真delta
    INCOMPLETE_NO_DONE = "incomplete_no_done"            # 有内容+有finish_reason, 但无[DONE]
    INCOMPLETE_NO_FR = "incomplete_no_fr"               # 有内容+有[DONE], 但无finish_reason
    CONTENT_FILTER = "content_filter"                  # NVCF内容过滤


@dataclass
class StreamState:
    """流处理过程中累积的状态，每个 chunk 更新，结束时用于判定。"""
    # 内容计数
    content_chars: int = 0
    reasoning_chars: int = 0

    # tool_call 状态
    saw_tool_call_id: bool = False        # 收到 tool_call 的 id/name 头块
    saw_tool_call_args: bool = False       # 收到 tool_call 的 arguments delta（真正的）
    # 区分: 只有 id 无 args = NVCF 声明了 tool_calls 但没发真 delta = R1932 fake_tool_call

    # 终止信号
    finish_reason: str | None = None
    saw_done: bool = False

    # 时序
    t_start: float = field(default_factory=time.time)
    last_content_time: float | None = None  # 最后一次收到实际内容的时间

    # 异常
    connection_closed: bool = False          # TCP 连接断开（RemoteDisconnected 等）
    timeout_triggered: bool = False         # 我们的 idle/cap timeout 触发
    error_exception: str | None = None      # 异常类型名

    @property
    def has_real_content(self) -> bool:
        """有实际内容：content / reasoning / 真 tool_call args 至少一项"""
        return (self.content_chars > 0
                or self.reasoning_chars > 0
                or self.saw_tool_call_args)

    @property
    def has_real_tool_call(self) -> bool:
        """真正的 tool_call = 有 id + 有 args（不是只声明不发）"""
        return self.saw_tool_call_id and self.saw_tool_call_args

    @property
    def has_any_tool_call_signal(self) -> bool:
        """有 tool_call 迹象（id 或 finish_reason=tool_calls）"""
        return self.saw_tool_call_id or self.finish_reason == "tool_calls"


def update_state_from_chunk(state: StreamState, chunk_data: dict) -> None:
    """
    每收到一个 SSE chunk（已 json.loads 的 dict），更新 state。

    调用点：在 _stream_openai_to_anth / _stream_openai_passthrough 的
    while 循环里，json.loads(data_str) 之后，converter.feed_chunk 之前。
    """
    choices = chunk_data.get("choices") or [{}]
    delta = choices[0].get("delta") or {}

    # content
    cont = delta.get("content")
    if cont:
        state.content_chars += len(cont)
        state.last_content_time = time.time()

    # reasoning_content（thinking）
    rcont = delta.get("reasoning_content")
    if rcont:
        state.reasoning_chars += len(rcont)
        state.last_content_time = time.time()

    # tool_calls delta
    for tc in (delta.get("tool_calls") or []):
        if not isinstance(tc, dict):
            continue
        fn = tc.get("function", {})
        # tool_call 头块：有 id + 有 name，但没有 arguments
        if tc.get("id") or (fn.get("name") and not fn.get("arguments")):
            state.saw_tool_call_id = True
        # 真正的 arguments delta
        if fn.get("arguments"):
            state.saw_tool_call_args = True
            state.last_content_time = time.time()

    # finish_reason
    fr = choices[0].get("finish_reason")
    if fr:
        state.finish_reason = fr

    # usage（不影响判定，但可能有 token 信息）
    # 不在此处理


def mark_done(state: StreamState) -> None:
    """收到 `data: [DONE]` 时调用。"""
    state.saw_done = True


def mark_connection_closed(state: StreamState, exc: Exception | None = None) -> None:
    """TCP 连接断开时调用。"""
    state.connection_closed = True
    if exc is not None:
        state.error_exception = type(exc).__name__


def mark_timeout(state: StreamState, exc: Exception | None = None) -> None:
    """idle/cap timeout 触发时调用。"""
    state.timeout_triggered = True
    if exc is not None:
        state.error_exception = type(exc).__name__


def judge_stream(state: StreamState) -> StreamVerdict:
    """
    流结束后一次性判定。

    调用时机：
    - 主循环正常退出（resp.read() 返回 b"" 或收到 [DONE]）
    - 异常退出（RemoteDisconnected / timeout / OSError）
    - 主动 break（idle deadline / cap / no_content_gap）

    判定逻辑（严格按优先级从高到低）：

    成功充要条件：has_real_content + finish_reason∈{stop,length,tool_calls} + saw_done
    三者齐全 = 成功；任何缺失 = 失败，按缺失组合分类。
    """

    # ── 成功路径：三者齐全 ──
    valid_fr = state.finish_reason in ("stop", "length", "tool_calls")
    has_done = state.saw_done

    if state.has_real_content and valid_fr and has_done:
        # 三者齐全 = 成功，按内容类型分亚型
        has_tool = state.has_real_tool_call
        has_reasoning = state.reasoning_chars > 0
        has_content = state.content_chars > 0

        if has_tool and has_reasoning:
            return StreamVerdict.SUCCESS_THINKING_TOOL    # #6
        elif has_tool:
            return StreamVerdict.SUCCESS_TOOL_CALL         # #5
        elif has_reasoning and has_content:
            return StreamVerdict.SUCCESS_THINKING          # #2
        elif has_reasoning and not has_content:
            return StreamVerdict.SUCCESS_THINKING_ONLY     # #3
        elif state.finish_reason == "length":
            return StreamVerdict.SUCCESS_LENGTH            # #4
        else:
            return StreamVerdict.SUCCESS_TEXT               # #1

    # ── 失败路径：按缺失组合分类 ──

    # 优先判定 content_filter（NVCF 主动标记）
    if state.finish_reason == "content_filter":
        return StreamVerdict.CONTENT_FILTER

    # FAKE_TOOL_CALL: finish_reason=tool_calls 但没有真 delta
    if state.finish_reason == "tool_calls" and not state.has_real_tool_call:
        return StreamVerdict.FAKE_TOOL_CALL

    # ZOMBIE_EMPTY: 零内容（连 thinking 都没有）
    if not state.has_real_content:
        return StreamVerdict.ZOMBIE_EMPTY

    # 到这里 = has_real_content=True，但 finish_reason 或 [DONE] 缺失

    # ZOMBIE_PARTIAL (Form B): 有内容但无 finish_reason 无 [DONE]
    # 这就是本次 session 0e098783 的根因
    if state.finish_reason is None and not has_done:
        return StreamVerdict.ZOMBIE_PARTIAL

    # INCOMPLETE_NO_DONE: 有内容 + 有 finish_reason，但无 [DONE]
    if state.finish_reason is not None and not has_done:
        return StreamVerdict.INCOMPLETE_NO_DONE

    # INCOMPLETE_NO_FR: 有内容 + 有 [DONE]，但无 finish_reason
    if state.finish_reason is None and has_done:
        return StreamVerdict.INCOMPLETE_NO_FR

    # 兜底（理论上不会到达，三者齐全已在上面处理）
    return StreamVerdict.ZOMBIE_PARTIAL


def should_retry(verdict: StreamVerdict) -> bool:
    """
    判定结果是否应该触发重试。

    成功路径：不重试。
    失败路径：全部重试（但重试策略可不同）。

    重试策略建议：
    - ZOMBIE_PARTIAL / INCOMPLETE_NO_DONE / INCOMPLETE_NO_FR:
        → 流中途断了，换 key/换 channel 重试，大概率成功
    - ZOMBIE_EMPTY:
        → NVCF 返回空，可能是限流前兆，重试但降级优先级
    - FAKE_TOOL_CALL:
        → R1932 已有 finish() 内置修复（强转 end_turn），不重试也行
        → 但如果 CC 侧仍报 parse error，则需重试
    - CONTENT_FILTER:
        → NVCF 内容过滤，重试也可能再触发，但值得试一次
    """
    return verdict not in (
        StreamVerdict.SUCCESS_TEXT,
        StreamVerdict.SUCCESS_THINKING,
        StreamVerdict.SUCCESS_THINKING_ONLY,
        StreamVerdict.SUCCESS_LENGTH,
        StreamVerdict.SUCCESS_TOOL_CALL,
        StreamVerdict.SUCCESS_THINKING_TOOL,
    )


def verdict_summary(verdict: StreamVerdict, state: StreamState) -> str:
    """人类可读的判定摘要，用于日志。"""
    return (f"{verdict.value}: content={state.content_chars}c "
            f"reasoning={state.reasoning_chars}c "
            f"tool_call(id={state.saw_tool_call_id},args={state.saw_tool_call_args}) "
            f"fr={state.finish_reason} done={state.saw_done} "
            f"closed={state.connection_closed} timeout={state.timeout_triggered}")


# ── 集成示例：在 _stream_openai_to_anth 主循环中的用法 ──
# (注释展示，不是可执行代码)
#
# state = StreamState()
# while True:
#     chunk = resp.read(8192)
#     if not chunk:
#         mark_connection_closed(state)   # 连接关了
#         break
#     sse_buffer += chunk.decode(...)
#     while "\n\n" in sse_buffer:
#         event_str, sse_buffer = sse_buffer.split("\n\n", 1)
#         data_str = ...
#         if data_str == "[DONE]":
#             mark_done(state)
#             continue
#         chunk_data = json.loads(data_str)
#         update_state_from_chunk(state, chunk_data)
#         out_bytes = converter.feed_chunk(chunk_data)
#         if out_bytes:
#             self.wfile.write(out_bytes)
#             self.wfile.flush()
#
# # 流结束 → 判定
# verdict = judge_stream(state)
# _log("NV-STREAM-VERDICT", verdict_summary(verdict, state))
# if should_retry(verdict):
#     # 触发重试逻辑（换 key / 换 channel / ms_gw fallback）
#     ...
