#!/usr/bin/env python3
"""Anthropic → OpenAI request conversion (R1648a).

Extracted from cc4101/gateway/converters.py (R684). Self-contained: no gateway
config dependency. The three tunable limits default here and can be overridden
via env so each gateway (cc4101 / nv_gw / ms_gw) can tune independently without
editing this file.

  MAX_TOOL_DESC    — truncate tool descriptions to this many chars.
  MAX_SCHEMA_DESC   — truncate nested schema descriptions to this many chars.
  CHARS_PER_TOKEN_ESTIMATE — only used by _estimate_text_chars (metrics, not
                     functional); kept here so callers don't need a separate config.

Functional behavior is identical to the cc4101 original. This is a pure code-
organization move (R1648a: behavior unchanged).
"""
import json
import os
import uuid

MAX_TOOL_DESC = int(os.environ.get("MAX_TOOL_DESC", "2000"))
MAX_SCHEMA_DESC = int(os.environ.get("MAX_SCHEMA_DESC", "600"))
CHARS_PER_TOKEN_ESTIMATE = float(os.environ.get("CHARS_PER_TOKEN_ESTIMATE", "3.0"))


# ─── Truncation ───────────────────────────────────────────────────────────

def _truncate_desc(text, max_len):
    if not text or len(text) <= max_len:
        return text
    double_nl = text.find("\n\n")
    if double_nl > 0 and double_nl <= max_len * 2:
        result = text[:double_nl].strip()
        if len(result) <= max_len:
            return result
    truncated = text[:max_len]
    last_sentence = truncated.rfind(". ")
    if last_sentence > max_len // 4:
        return text[:last_sentence + 1].strip()
    return text[:max_len - 3].rstrip() + "..."


def _truncate_schema_descriptions(schema, max_len=MAX_SCHEMA_DESC):
    if isinstance(schema, dict):
        for key in schema:
            if key == "description" and isinstance(schema[key], str):
                schema[key] = _truncate_desc(schema[key], max_len)
            else:
                _truncate_schema_descriptions(schema[key], max_len)
    elif isinstance(schema, list):
        for item in schema:
            _truncate_schema_descriptions(item, max_len)
    return schema


# ─── Text char estimation (metrics only) ──────────────────────────────────

def _estimate_text_chars(oai_body):
    """Estimate char count of actual text content (excludes JSON structure overhead)."""
    text_chars = 0

    for msg in oai_body.get("messages", []):
        if msg.get("role") == "system":
            content = msg.get("content", "")
            if isinstance(content, str):
                text_chars += len(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_chars += len(block.get("text", ""))
                    elif isinstance(block, str):
                        text_chars += len(block)

    for msg in oai_body.get("messages", []):
        role = msg.get("role", "")
        if role == "system":
            continue
        content = msg.get("content", "")
        if isinstance(content, str):
            text_chars += len(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    block_type = block.get("type", "")
                    if block_type == "text":
                        text_chars += len(block.get("text", ""))
                    elif block_type == "thinking":
                        text_chars += len(block.get("thinking", ""))
                    elif block_type == "tool_use":
                        text_chars += len(json.dumps(block.get("input", {})))
                        text_chars += len(block.get("name", ""))
                    elif block_type == "tool_result":
                        tc = block.get("content", "")
                        if isinstance(tc, str):
                            text_chars += len(tc)
                        elif isinstance(tc, list):
                            for sub_block in tc:
                                if isinstance(sub_block, dict) and sub_block.get("type") == "text":
                                    text_chars += len(sub_block.get("text", ""))
                                else:
                                    text_chars += len(json.dumps(sub_block, default=str))
                    elif block_type == "image_url":
                        url = block.get("image_url", {}).get("url", "")
                        if url.startswith("data:"):
                            text_chars += 8000
                        else:
                            text_chars += len(url)
                elif isinstance(block, str):
                    text_chars += len(block)

        tool_calls = msg.get("tool_calls", [])
        if tool_calls and isinstance(content, str):
            for tc in tool_calls:
                fn = tc.get("function", {})
                text_chars += len(fn.get("name", ""))
                text_chars += len(fn.get("arguments", ""))

    for tool in oai_body.get("tools", []):
        fn = tool.get("function", {})
        text_chars += len(fn.get("name", ""))
        text_chars += len(fn.get("description", ""))
        text_chars += len(json.dumps(fn.get("parameters", {})))

    return text_chars


# ─── Anthropic → OpenAI (request) ─────────────────────────────────────────

def _tool_anth_to_oai(anth_tools):
    oai_tools = []
    for tool in anth_tools:
        if tool.get("type", "tool_use") != "tool_use":
            continue
        name = tool.get("name", "")
        desc = _truncate_desc(tool.get("description", ""), MAX_TOOL_DESC)
        schema = _truncate_schema_descriptions(tool.get("input_schema", {}))
        oai_tools.append({
            "type": "function",
            "function": {"name": name, "description": desc, "parameters": schema},
        })
    return oai_tools


def _convert_tool_choice(anth_choice):
    if not anth_choice:
        return None
    if isinstance(anth_choice, dict):
        ctype = anth_choice.get("type", "")
        if ctype == "auto":
            return "auto"
        if ctype == "none":
            return "none"
        if ctype == "any":
            return "required"
        if ctype == "tool":
            return {"type": "function", "function": {"name": anth_choice.get("name", "")}}
    if isinstance(anth_choice, str):
        return anth_choice
    return None


def anth_to_openai(body, target_model=None):
    """Convert Anthropic Messages API request → OpenAI Chat Completions request.

    R684: Always sets stream=True (caller may override, but cc4101 forces stream
    upstream regardless — glm5.2 non-stream is broken on both backends). The
    caller in handlers.py sets stream=True after this; this function preserves
    the client's stream flag for metrics, then the upstream layer forces True.
    """
    model = target_model or body.get("model", "glm5_2_nv")
    system_text = ""
    system_blocks = body.get("system")
    if system_blocks:
        if isinstance(system_blocks, str):
            system_text = system_blocks
        elif isinstance(system_blocks, list):
            parts = []
            for block in system_blocks:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    parts.append(block)
            system_text = "\n".join(parts)

    oai_messages = []
    if system_text:
        oai_messages.append({"role": "system", "content": system_text})

    for msg in body.get("messages", []):
        role = msg.get("role", "")
        content = msg.get("content", "")

        if role == "user":
            if isinstance(content, list):
                text_parts = []
                tool_results = []
                image_parts = []
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "tool_result":
                            tool_results.append(block)
                        elif block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                        elif block.get("type") == "image":
                            source = block.get("source", {})
                            if source.get("type") == "base64":
                                media_type = source.get("media_type", "image/png")
                                data = source.get("data", "")
                                image_parts.append({
                                    "type": "image_url",
                                    "image_url": {"url": f"data:{media_type};base64,{data}"},
                                })
                            elif source.get("type") == "url":
                                image_parts.append({
                                    "type": "image_url",
                                    "image_url": {"url": source.get("url", "")},
                                })
                    elif isinstance(block, str):
                        text_parts.append(block)
                if image_parts:
                    oai_content = []
                    for tp in text_parts:
                        oai_content.append({"type": "text", "text": tp})
                    for ip in image_parts:
                        oai_content.append(ip)
                    oai_messages.append({"role": "user", "content": oai_content})
                elif text_parts:
                    oai_messages.append({"role": "user", "content": "\n".join(text_parts)})
                for tr in tool_results:
                    tool_id = tr.get("tool_use_id", "")
                    content_str = ""
                    is_error = tr.get("is_error", False)
                    tc = tr.get("content", "")
                    if isinstance(tc, str):
                        content_str = tc
                    elif isinstance(tc, list):
                        parts = []
                        for b in tc:
                            if isinstance(b, dict) and b.get("type") == "text":
                                parts.append(b.get("text", ""))
                            else:
                                parts.append(json.dumps(b, default=str))
                        content_str = "\n".join(parts)
                    elif isinstance(tc, dict):
                        # R690 cc2 red-team: Anthropic allows tool_result.content to be a
                        # single block dict ({"type":"text","text":"..."}), not just a list.
                        # Previously fell through to "" and the tool result body was lost.
                        if tc.get("type") == "text":
                            content_str = tc.get("text", "")
                        else:
                            content_str = json.dumps(tc, default=str)
                    if is_error:
                        content_str = f"[tool_error] {content_str}" if content_str else "[tool_error]"
                    oai_messages.append({"role": "tool", "tool_call_id": tool_id, "content": content_str})
            elif isinstance(content, str):
                oai_messages.append({"role": "user", "content": content})
            else:
                oai_messages.append({"role": "user", "content": str(content)})

        elif role == "assistant":
            if isinstance(content, list):
                text_parts = []
                tool_calls = []
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                        elif block.get("type") == "thinking":
                            # R690 cc2 red-team: assistant history may carry thinking
                            # blocks (signature blocks from prior turns). glm5.2 doesn't
                            # accept Anthropic thinking blocks natively, but dropping them
                            # silently breaks multi-turn thinking context. Surface them as
                            # tagged text so the model at least sees prior reasoning.
                            thinking_text = block.get("thinking", "")
                            if thinking_text:
                                text_parts.append(f"[thinking]\n{thinking_text}\n[/thinking]")
                        elif block.get("type") == "tool_use":
                            tool_calls.append({
                                "id": block.get("id", f"call_{uuid.uuid4().hex[:24]}"),
                                "type": "function",
                                "function": {
                                    "name": block.get("name", ""),
                                    "arguments": json.dumps(block.get("input", {})),
                                },
                            })
                msg_dict = {"role": "assistant"}
                if text_parts:
                    msg_dict["content"] = "\n".join(text_parts)
                else:
                    msg_dict["content"] = None
                if tool_calls:
                    msg_dict["tool_calls"] = tool_calls
                oai_messages.append(msg_dict)
            elif isinstance(content, str):
                oai_messages.append({"role": "assistant", "content": content})
            else:
                oai_messages.append({"role": "assistant", "content": str(content)})

        elif role == "tool":
            pass  # handled in user tool_result

    oai_body = {
        "model": model,
        "messages": oai_messages,
        "stream": body.get("stream", False),
        "stream_options": {"include_usage": True},
    }
    # R690 cc2 red-team: default 4096 is too small for glm5.2 thinking mode —
    # reasoning_content alone can consume thousands of tokens, leaving no room
    # for the actual answer (finish_reason=length). Bump default to 8192.
    # (CC usually sends its own max_tokens, so this only bites when absent.)
    output_tokens = body.get("max_tokens") or body.get("max_completion_tokens") or 8192
    if output_tokens:
        oai_body["max_tokens"] = output_tokens
        oai_body["max_completion_tokens"] = output_tokens
    # R690 cc2 red-team: use "in" checks, not truthiness — temperature=0 and
    # top_p=0 are valid explicit values that must reach the upstream.
    if "temperature" in body:
        oai_body["temperature"] = body["temperature"]
    if "top_p" in body:
        oai_body["top_p"] = body["top_p"]
    if body.get("stop_sequences"):
        oai_body["stop"] = body["stop_sequences"]
    if body.get("tools"):
        oai_tools = _tool_anth_to_oai(body["tools"])
        if oai_tools:
            oai_body["tools"] = oai_tools
    tc = _convert_tool_choice(body.get("tool_choice"))
    if tc:
        oai_body["tool_choice"] = tc

    # R684: No thinking_budget / reasoning_effort injection. glm5.2 doesn't need it;
    # nv_gw/ms_gw handle their own param stripping. Anthropic thinking blocks in
    # request history are converted to text above (role=assistant thinking block).
    return oai_body
