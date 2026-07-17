# R1703: cc4101 collect 终态合成换 oai_nonstream_to_anth — 第 2 步(路 A, 纯重构)

## 背景

R1702 把 cc4101 流式(stream_to_anth)的纯转换体换成了 format 包的 OaiSseToAnthropicConverter。
本轮收尾非流式(collect_stream_to_anth): 终态的"手拼 Anthropic JSON"换成"重组 OpenAI 非流式 JSON
→ `oai_nonstream_to_anth`",与 ms_gw `_relay_nonstream_to_anth`(R1648d 已验证)对齐。

至此 cc4101 的 oai→anth 转换(流式+非流式)全部走 format 包, 与 nv_gw/ms_gw 共用同一份代码,
转换逻辑单点存活于 `gateway/format/oai_to_anth.py`。读循环/stall-watcher/recv-fallback/breaker
/路由全部留在 cc4101(本轮不动)。

## 变更(HM2 only)

`cc4101/gateway/stream.py`:
1. import 加 `oai_nonstream_to_anth`(同 format 包, 无新依赖)。
2. `collect_stream_to_anth` 终态合成段(L764-830 手拼 content/stop_reason/anth_response)替换:
   - 保留 status 决定/metrics 记录/error→`_send_json` 502 路径(error_mapping.convert_error)。
   - 成功路径: 把 `reasoning_text`/`content_text`/`tool_calls_data`/`finish_reason`/`msg_id`/usage
     重组成 OpenAI 非流式 JSON(`choices[0].message` 结构, 镜像 ms_gw L773-783),
     调 `oai_nonstream_to_anth(oai_json, request_model)` 得 anth_response, `_send_json`。
3. collect 读循环(stall-watcher/recv-fallback/累积, L530-712)与 zombie/empty 判定(L714-762)**不动**。

## 行为差异(逐条核对)

- thinking signature: cc4101 旧 `THINKING_SIGNATURE_DEFAULT` ↔ format 包 `THINKING_SIGNATURE`, 同 env 同值。
- content 空: 两边都补 `{"type":"text","text":""}`。
- stop_reason 映射: 两边一致(length→max_tokens, tool_calls→tool_use, 其余 end_turn)。
- content_filter: cc4101 L715 已走 empty_stream→502 不到合成段; oai_nonstream_to_anth 对 content_filter 映射 end_turn — 合成段只在 status=200 走, 无冲突。
- tool_calls input json.loads 兜底 `{"raw":...}`: 两边一致。
- **JSON 序列化字节级零变化**: `_send_json` 未动, 仍 `json.dumps(ensure_ascii=False)` 带空格。
  (与 R1702 的 SSE 紧凑化不同, R1703 是真正的字节零变化。)

## 验证(铁律)

bind-mount 改 .py → `docker compose restart cc4101`。
三看: `Up` + `[START] listening 0.0.0.0:4101` + `/health` 200 + 无 ImportError ✓

功能:
- 非流式 collect: 返回完整 message JSON(type/role/content/stop_reason/usage), oai_nonstream_to_anth
  合成的标准结构 ✓。字节级带空格(`{"id": "...", "type": "message", ...}`), 与改动前一致 ✓。
- 流式(R1702 回归): 完整 anthropic SSE 序列未坏 ✓。
- thinking 分支: oai_nonstream_to_anth 已实现 reasoning→thinking block, 与 ms_gw 同款(ms_gw 生产在跑)。

## 不做

- 不动 collect 读循环/stall-watcher/recv-fallback/zombie 判定。
- 不动 nv_gw `_collect_stream_to_anth`(它仍手拼, 不在本轮范围; 虽然它注释说用 oai_nonstream_to_anth 但实现没换)。
- 不动 cc4101 fallback/路由/breaker。
- 不做 R1648e(cc4101 瘦身纯透传)。
- 不同步 HM1。

## 回滚

`stream.py.bak.R1703_pre` 已备。回滚 = 还原 + restart。

## 剩余(路 A 之后)

- 路第 3 步(R1648e): cc4101 瘦成纯透传(把 anthropic body 透传给 nv_gw `/v1/messages`, 删 cc4101 自己的
  anth→oai + 读循环)。**前置条件**: R1648c/R1673 的 breaker 在生产真正触发验证过(记忆载 R1675/R1695/R1696
  三轮没重启故 0 次 OPEN, 尚未验证)。未验证前不动 R1648e。
- HM1 同步: HM1 cc4101 仍 15KB 旧 converters.py(无 format/), nv_gw/ms_gw 也缺 format/ 包。单独一轮。
- nv_gw `_collect_stream_to_anth` 也可顺手换 oai_nonstream_to_anth(对齐 ms_gw/cc4101), 但不在本轮。
