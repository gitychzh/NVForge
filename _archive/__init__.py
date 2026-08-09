#!/usr/bin/env python3
"""Shared format conversion package (R1648a/b).

Anthropic ↔ OpenAI conversion logic, extracted from cc4101/gateway/converters.py
and cc4101/gateway/stream.py so nv_gw / ms_gw / cc4101 can each carry a copy
(R1648 framework: 各复制一份).

This package is self-contained: no dependency on any gateway's config.py. Defaults
are module-level; callers may override via env or kwargs. Keeping it dependency-free
is what makes it safe to copy across gateways without dragging config coupling.

Modules:
  anth_to_oai.py — Anthropic request → OpenAI request (anth_to_openai + helpers).
  oai_to_anth.py — OpenAI SSE-chunks / non-stream JSON → Anthropic SSE / message
    JSON (OaiSseToAnthropicConverter + oai_nonstream_to_anth). Added R1648b.
"""
