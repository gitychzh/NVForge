# R1648d: ms_gw 加 /v1/messages anthropic 端点

> R1648 框架第 4 轮 (a→b→c→**d**→e→f)。承接 R1648c (nv_gw ms fallback)。
> ms_gw 加 anthropic 格式端点, 镜像 R1648b 的 nv_gw 结构。只改 **HM2**。

## 一、动机

R1648 目标架构: cc4101 瘦成纯透传 (R1648e), 所有格式转换下沉到 nv_gw / ms_gw 本体。
R1648b 已让 nv_gw 服务 `/v1/messages`; 本轮让 ms_gw 也能服务 anthropic 格式,
这样 R1648e 后 cc4101 可同时透传到 nv_gw:40006/v1/messages (主) 和 ms_gw:40007/v1/messages (兜底),
agent / CC 无需感知后端是 openai 格式。

## 二、改动 (format pkg 复制 + handlers 加端点)

### 1. `gateway/format/` 包 (新, 3 文件, 从 nv_gw 复制)
- `anth_to_oai.py` (md5 dec1655dd37a2e9b50dc9441d6333eb5) — Anthropic→OpenAI 请求转换
- `oai_to_anth.py` (md5 10adc0f0ab4bfc832c03056b3df1d612) — OpenAI SSE/JSON→Anthropic SSE/JSON
  (`OaiSseToAnthropicConverter`, `oai_nonstream_to_anth`, `convert_error_to_anth`)
- `__init__.py` (md5 c6ca650932eda1806d29620002684534) — re-export
- **自包含**, 无 gateway config 依赖 (只 import json/os/uuid); 可安全跨 gateway 复制。
  与 nv_gw format/ 内容一致 (各复制一份, R1648 框架原则)。

### 2. `gateway/handlers.py` (md5 f662585df982f626809231d307b564a3)
- import: `from .format.anth_to_oai import ...` + `from .format.oai_to_anth import ...`
- `do_POST`: 加 `if parsed.path in ("/v1/messages","/messages"): self._handle_messages_anthropic()`
- `do_HEAD`: 加 `/v1/messages` / `/messages` 到 200 路径列表
- `_send_json(status, body_dict, extra_headers=None)`: 加可选 extra_headers (429 retry-after)
- 新增 3 方法:
  - `_handle_messages_anthropic()`: auth→读 body(50MB cap)→model 校验(MODEL_REGISTRY)→
    `anth_to_openai(anth_body, target_model=request_model)`→force stream=True (R684 parity,
    glm5.2 非流返空)→MSG-FIX (trailing assistant→"Continue.")→`_sanitize_request_body`→
    `_try_ms_keys`→error path(`convert_error_to_anth` + 429 retry-after) /
    success stream→`_relay_stream_to_anth` / non-stream→`_relay_nonstream_to_anth`
  - `_relay_stream_to_anth(resp, conn, first_chunk, ...)`:
    `_try_ms_keys` 已预读 `_first_chunk` (ms_gw 的设计, R806), 先 replay 它再 `resp.read1(8192)`,
    每�� SSE event 解析后 `OaiSseToAnthropicConverter.feed_chunk` → 写 anthropic SSE 到 wfile。
    比 nv_gw 简单 (无 R850/R1407/R1627 deadline/zombie 基建, ms_gw `_relay_stream` 本来也是
    纯 read1 透传); 仅 settimeout + 基本 zombie 检测 (content_chars 计数, 终末走 converter.finish)。
    空响应/中断 → `converter.finish(zombie=...)` 发 api_error SSE 让 CC 重试。
  - `_relay_nonstream_to_anth(...)`: 收集所有 SSE chunks (content/reasoning/tool_calls/usage),
    合成 openai JSON 再 `oai_nonstream_to_anth` 转 anthropic message JSON 返客户端。
    zombie/empty 检测 (mirror nv_gw collect)。

## 三、架构决策

- **没整搬 nv_gw 的复杂 deadline/zombie 基建到 ms_gw**。ms_gw 本身的 `_relay_stream`
  就是简单 read1 透传 (R806), 保持同样简洁; 只加 per-chunk 转换调用。zombie/empty 检测
  保留基本版 (content_chars 计数 + 终末 finish) 以保 CC 重试语义, 但不带 idle-deadline。
- **format 包各复制一份**: nv_gw 和 ms_gw 各自 `gateway/format/`, 内容一致, 不共享 import
  (R1648 框架原则: 先求简单, 避免跨 gateway 耦合)。
- `_try_ms_keys` 的 `MSExecResult` 复用: `.relay`/`.resp`/`.conn`/`.metrics[_first_chunk]`
  对接转换器, 不改 upstream.py。

## 四、验证 (HM2, 2026-07-17 11:17)

| # | 测试 | 结果 |
|---|---|---|
| 1 | `/v1/messages` 非流式 glm5_2_ms "reply pong" | ✅ anthropic message JSON, content=[thinking+sig, text="pong"], stop_reason=end_turn, usage |
| 2 | `/v1/messages` 流式 glm5_2_ms "reply pong" | ✅ anthropic SSE: message_start→content_block_start(thinking)→content_block_delta(thinking_delta)→... |
| 3 | 回归: openai `/v1/chat/completions` 非流式 | ✅ 返 openai JSON (无回归) |
| 4 | 回归: openai 流式 | ✅ `data:` SSE 正常 |
| 5 | format pkg import + handlers import | ✅ 容器内无启动错 |

DB 确认 (ms_requests): 两个 R1648d anthropic 测试请求 (req 7522fb67 非流 1459ms ok,
845df33b 流 12s ok) 经现有 `_log_metrics` 路径正确入库。**注**: ms_requests 表无
`agent_type`/`path` 列 (与 nv_requests 不同), anthropic 与 openai 请求在 DB 里不可区分
(caller 仍由 User-Agent 定)。本轮非目标, 后续需区分再加列。

## 五、后续

- **R1648e**: cc4101 瘦成纯透传 (删 R1643 fallback + breaker, handlers 透传 anthropic body
  到 nv_gw:40006/v1/messages 主, ms_gw:40007/v1/messages 兜底)。届时开 nv_gw
  NVU_MS_FALLBACK_ENABLED=1 长跑。
- **R1648f**: 切换 + ≥6h 长跑观察, 更新 compose + memory。HM1 不推 (后续轮)。
- ms_gw 没有 peer-fallback / breaker (它就是 nv_gw 的兜底终点), 不需要加。
