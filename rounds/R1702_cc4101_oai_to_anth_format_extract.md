# R1702: cc4101 反向转换(oai→anth SSE)抽到 format 包 — 第 1 步(路 A, 纯重构)

## 背景

回答用户问题"cc4101↔40006/40007 的 openai-anthropic 格式转换代码到底放哪"的评估结论:
转换逻辑应**下沉到 nv_gw/ms_gw**(各持 `gateway/format/`),cc4101 最终瘦成纯透传(R1648e)。
理由见对话: glm5.2_nv 故障全在 openai 语义层,诊断必须落在 nv_gw 内部;cc4101 留转换=双份读循环
+deadline/breaker 永远在"对齐"上踩坑(R1407/R1602/R1640 倒挂学费);fallback 必须在转换器之前切。

R1648 重构已半落地(HM2): nv_gw/ms_gw 各有完整 `format/`(anth_to_oai + oai_to_anth),
但 **cc4101 只复制了 anth_to_oai, 反向 oai_to_anth 还内联在 cc4101 stream.py(923行)里没抽**。
本轮 = 第 1 步(路 A): 把 cc4101 stream.py 里内联的"纯转换体"换成对 `format/oai_to_anth.py`
`OaiSseToAnthropicConverter` 的调用。读循环/stall-watcher/recv-fallback/breaker(含 R1638 polarity)
**全部原样保留**。

## 变更(HM2 only; 破例改 HM2 因远程 CC 链路在 HM2)

1. **新增 `cc4101/gateway/format/oai_to_anth.py`**: 从 nv_gw `format/oai_to_anth.py` 原样复制
   (md5 一致 `10adc0f0...`, 与 ms_gw 同款)。cc4101 之前 format/ 只缺这一份。
2. **更新 `cc4101/gateway/format/__init__.py`**: docstring 不再说"oai_to_anth 还没抽"。
3. **改 `cc4101/gateway/stream.py` — `stream_to_anth`(流式)**:
   - 删 9 个内联局部状态(message_start_sent/message_delta_sent/next_block_idx/active_block_type/
     streaming_input_tokens/streaming_output_tokens/pending_stop_reason/stream_content_chars/
     stream_reasoning_chars/stream_saw_real_tool_call), 换成 `converter = OaiSseToAnthropicConverter(request_model)`。
   - 主循环转换体(reasoning/text/tool_calls/finish 映射 L360-538)换成 `out = converter.feed_chunk(chunk_data); _write_bytes(out)`。
   - `_emit_graceful_end` 终态 SSE(content_block_stop/message_delta/message_stop 或 api_error)改成
     `converter.finish(zombie=|interrupted=)` 产出 bytes 再 write; zombie 判定/empty_stream_response/
     breaker polarity(R1638: content_filter 无内容不计 breaker)/record_primary_success/metrics/conn.close **全部保留**。
   - zombie 检测点(content_filter/empty_completion/clean_eof/malformed)的判定和 `_record_primary_stream_fail`
     调用原样, 只把累积量读取从局部变量改 `converter.content_chars/reasoning_chars/saw_real_tool_call/next_block_idx/pending_stop_reason`。
   - stall-watcher 动态 IDLE_GAP 的 thinking 判定改读 `converter.reasoning_chars`。
4. **collect_stream_to_anth(非流式) 本轮不动**: 它拼完整 content 而非逐 chunk emit, 与 converter 模型不同;
   nv_gw `_collect_stream_to_anth` 也没用 feed_chunk。留下一轮(路 A 的 collect 半)。

## 行为差异(已确认接受)

- SSE JSON 序列化: cc4101 旧 `json.dumps(ensure_ascii=False)`(带空格) → format 包 `separators=(",",":")`(紧凑)。
  语义等价, nv_gw `/v1/messages` 早已用紧凑格式给 CC, CC 已验证可解析。非字节级零变化。
- thinking signature: cc4101 `THINKING_SIGNATURE_DEFAULT` 与 format 包 `THINKING_SIGNATURE` 读同 env, 同值。

## 验证(铁律: 改后必有验证)

bind-mount 改 .py 必须 `docker compose restart cc4101`(非 up -d, 后者跳过 — R1675 学费)。

三看:
- `docker ps` cc4101 Up, `[START] cc4101 listening on 0.0.0.0:4101` ✓
- `curl /health` HTTP=200 ✓
- `docker logs` 无 ImportError/SyntaxError/NameError ✓

功能(真实流经 cc4101 的 anthropic /v1/messages 请求):
- 流式: message_start → content_block_start(text) → content_block_delta(text_delta)×N → content_block_stop
  → message_delta(stop_reason=end_turn, usage) → message_stop ✓ 完整 anthropic SSE 序列。
- 非流式 collect(未动): type=message, stop=end_turn, content/usage 正确 ✓
- 重启后真实 CC 请求(opus-4-8 msgs=46-50 tools=30)流过, recv-fallback/malformed 兜底仍工作(保留的逻辑)。
- 6h 观察窗口待补(改后看 zombie/error_type 无异常上升)。

## 不做

- 不动 cc4101 读循环 deadline/IDLE_GAP 数值(路 B, 需数据)。
- 不动 collect_stream_to_anth(留下一轮)。
- 不动 cc4101 fallback/upstream 路由(R1643)。
- 不做 R1648e(cc4101 瘦身纯透传)。
- 不同步 HM1(HM1 cc4101 仍 15KB 旧 converters.py, 单独一轮)。

## 文件

- `cc4101/gateway/format/oai_to_anth.py` (新增, = nv_gw 同款)
- `cc4101/gateway/format/__init__.py` (docstring 更新)
- `cc4101/gateway/stream.py` (stream_to_anth 转换体换 converter; collect 不动)
- 备份: `stream.py.bak.R1702_pre`, `format/__init__.py.bak.R1702_pre`
