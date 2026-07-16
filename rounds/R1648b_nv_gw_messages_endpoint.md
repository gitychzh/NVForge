# R1648b: nv_gw 加 /v1/messages anthropic 端点（只转换，无 fallback）

> 状态: **已部署 HM2，端到端验证通过**。
> 范围: 只改 HM2 nv_gw。HM1 不动。破铁律"只改HM1"，本轮显式豁免（同 R1648/R1648a）。
> 日期: 2026-07-17。承接 R1648a（format 包抽取）。

## 一、本轮目标

R1648 框架第 2 步：给 nv_gw 加一个 anthropic 格式的 `/v1/messages` 端点，
让 cc4101（R1648e 后退化为纯透传）能把 Claude Code 的 anthropic 请求直接打到 40006。
本轮**只做转换，不加 fallback**（fallback 下沉是 R1648c 的事）。

数据流:
```
CC → cc4101 → nv_gw /v1/messages
  1. 鉴权 (NVU_GATEWAY_API_KEY)
  2. anth_to_oai(body, glm5_2_nv) → openai body
  3. execute_request(openai body) → 走现有 NVCF 5key×mode 链
  4. openai SSE → oai_to_anth → anthropic SSE 回客户端
```

## 二、关键设计决策（与 R1648a 框架设想不同之处）

R1648a 框架设想 "把 cc4101 stream.py 的反向转换抽成 format/oai_to_anth.py"。
实际读 cc4101 stream.py（897 行）后发现 `stream_to_anth` 把三件事缠在一起:
1. openai chunk → anthropic SSE 事件映射（纯转换，该抽）;
2. stall-watcher + idle-deadline + timed-out-obj recv-fallback 读循环;
3. cc4101 circuit-breaker 记账（record_primary_failure/success）。

nv_gw **已经拥有 (2)** 的更新版本：`_stream_openai_passthrough` 读循环含
R850/R1407/R1627 的 idle-deadline + no-content-gap + full-buffer 修复，比
cc4101 的 stall-watcher 更新。(3) 属于 nv_gw 自己的 breaker（R1648c 才加）。

**决策**: 只抽 (1) 为自包含的有状态转换器类 `OaiSseToAnthropicConverter`,
不把 cc4101 的读循环/breaker 一起搬进来。nv_gw 新写一个 `_stream_openai_to_anth`
读循环，复用本网关已有的 deadline/zombie/poll 基建，每个 chunk 喂给转换器出
anthropic SSE 字节。这避免了"在 nv_gw 里重实现 cc4101 stall-watcher 又漂移"的坑，
也避免把 cc4101 的 circuit 逻辑拖进转换层。

## 三、改动文件（HM2 /opt/cc-infra/proxy/nv-gw/gateway/）

### 新增 `format/oai_to_anth.py`（16127b，自包含无 config 依赖）
- `_sse_bytes(event_type, data_dict)` — 序列化一个 anthropic SSE event 为 bytes。
- `class OaiSseToAnthropicConverter` — 有状态转换器:
  - `feed_chunk(chunk_data) -> bytes` — 喂一个解析好的 openai chunk dict，返回
    要写给客户端的 anthropic SSE 字节。处理 message_start / content_block_start
    (thinking|text|tool_use) / content_block_delta / content_block_stop。
    累积 content_chars/reasoning_chars/saw_real_tool_call/input_tokens/output_tokens
    供调用方做 zombie 检测。**不发** message_delta/message_stop（finish() 才发）。
  - `finish(interrupted, zombie, input_tokens_real) -> bytes` — 发终末事件:
    zombie/interrupted → emit `error` (api_error) SSE 让 CC 重试;
    否则 → message_delta(stop_reason+usage) + message_stop。
  - thinking 块规范: thinking 必须在 text/tool_use 之前且不能再开（cc4101 R690 红队铁律保留）。
- `oai_nonstream_to_anth(openai_json, request_model)` — 非流式 openai JSON → anthropic message JSON。
- `convert_error_to_anth(error_json, request_model)` — openai 错误 → anthropic 错误
  (镜像 cc4101 error_mapping.convert_error 的 CC 错误语义: 429→rate_limit, 不当内容→invalid_request, 余→api_error)。
- 常量 `THINKING_SIGNATURE` (env 可覆盖, 默认同 cc4101 占位符)。

### 新增 `format/anth_to_oai.py`（从 HM2 cc4101 原样复制，15468b）
R1648a 已建，本轮原样复制进 nv_gw（无改动）。

### 更新 `format/__init__.py`
docstring 标注 oai_to_anth 已建（R1648a 的 TODO 兑现）。

### 改 `handlers.py`（+522 行，md5 8cca149→2c80b10）
- imports 加: `from .format.anth_to_oai import ...`, `from .format.oai_to_anth import (OaiSseToAnthropicConverter, oai_nonstream_to_anth, convert_error_to_anth, THINKING_SIGNATURE as OAI_TO_ANTH_THINKING_SIG)`.
- `do_POST` 路由加: `path in ("/v1/messages","/messages") → self._handle_messages_anthropic()`.
- `do_HEAD` 路由加 `/v1/messages`.
- 新增 `_handle_messages_anthropic()`:
  - 鉴权 → 解析 anthropic body (50MB 上限) → `detect_nv_model` → `anth_to_openai` →
    force upstream stream=True (R684 同 cc4101) → MSG-FIX → thinking-timeout 判定 →
    `execute_request(...)` (复用现有 NVCF 5key 链).
  - 失败: all_keys_exhausted → `format_nv_all_keys_exhausted` + `convert_error_to_anth`;
    其他上游错误 → `convert_error_to_anth`. 返回 anthropic 错误 JSON.
  - 成功 stream → `_stream_openai_to_anth`; 成功 non-stream → `_collect_stream_to_anth`.
- 新增 `_stream_openai_to_anth(resp, conn, metrics, t_start, request_model)`:
  读 NVCF openai SSE 流, 每个解析好的 chunk 喂 `OaiSseToAnthropicConverter.feed_chunk()`,
  出 anthropic SSE 字节写 `self.wfile`. 复用 `_stream_openai_passthrough` 的全套
  R850/R1407/R1627 deadline + R840/R852b zombie 检测 + R1408 poll socktimeout 基建.
  流结束调 `converter.finish()` 发终末事件 (zombie/interrupt→api_error 让 CC 重试).
- 新增 `_collect_stream_to_anth(...)`: 收集 openai SSE 流合成非流 anthropic message JSON
  (镜像 cc4101 collect_stream_to_anth). 含 content_filter/empty/zombie 检测.

## 四、验证（HM2, 2026-07-17）

### 1. 语法 + 导入
- `python3 -m py_compile handlers.py` (compile to /tmp, 避 root pycache) → OK
- 本地搭 gateway 包结构 import 测试: `from gateway import handlers` OK,
  `ProxyHandler` 含 `_handle_messages_anthropic`/`_stream_openai_to_anth`/`_collect_stream_to_anth` 三方法.
- `OaiSseToAnthropicConverter` 7 场景单测全过 (message_start, thinking→text block 切换, tool_use,
  finish graceful, finish zombie→api_error, finish interrupted→api_error, nonstream 合成).
- `convert_error_to_anth` 3 场景 (insufficient_quota→rate_limit, inappropriate content→invalid_request, generic→api_error) 全过.

### 2. 容器重启 + 启动日志
- `docker restart nv_gw` → health 200 OK, 无 import error.
- 启动日志: `[NV-PROXY] Listening on 0.0.0.0:40006`, format 包加载正常 (否则崩).

### 3. /v1/messages 非流式 (curl, glm5_2_nv)
```
POST /v1/messages  (stream=false, "Reply with exactly: PONG")
→ {"id":"chatcmpl-...","type":"message","role":"assistant","model":"glm5_2_nv",
   "content":[{"type":"text","text":"PONG"}],"stop_reason":"end_turn",
   "usage":{"input_tokens":12,"output_tokens":3,...}}
```
✓ anthropic 格式正确, content/stop_reason/usage 齐全.

### 4. /v1/messages 流式 (curl -N, glm5_2_nv)
```
event: message_start   data:{...message...}
event: content_block_start  data:{index:0, content_block:{type:text}}
event: content_block_delta  data:{delta:{type:text_delta, text:"P"}}
event: content_block_delta  data:{delta:{type:text_delta, text:"ONG"}}
event: content_block_stop
event: message_delta  data:{delta:{stop_reason:end_turn}, usage:{output_tokens:3,input_tokens:12}}
event: message_stop
```
✓ 原生 anthropic SSE 事件序列完整, chunk 边界处理正确 (P/ONG 独立 delta).

### 5. openai 路径回归 (不影响 agent)
```
POST /v1/chat/completions (glm5_2_nv, "Reply with exactly: REGRESSION-OK")
→ {"choices":[{"message":{"content":"REGRESSION-OK",...}}], ...}  (openai 格式)
```
✓ openai 路径未受影响, 路由 if/elif 隔离生效.

### 6. 404 路由 + DB 记账
- `POST /v1/foo` → 404 ✓.
- DB: 两条 /v1/messages 请求记入 `nv_requests`, `agent_type='_nv_anthropic'`:
  - stream req: 200, 4175ms, glm5_2_nv, input=12/output=3, finish=stop.
  - non-stream req: 200, 1940ms, glm5_2_nv, input=12/output=3, finish=stop.

## 五、参数表

| 项 | 值 | 说明 |
|---|---|---|
| 端点 | `/v1/messages`, `/messages` | anthropic Messages API, POST |
| 转换器 | `OaiSseToAnthropicConverter` | 有状态, feed_chunk+finish |
| 鉴权 | `NVU_GATEWAY_API_KEY` | 复用现有 (x-api-key/Bearer) |
| 上游模型 | `detect_nv_model(request_model)` → glm5_2_nv/dsv4p_nv/kimi_nv | 复用现有 tier 链 |
| force stream | 上游恒 stream=True | R684 同 cc4101 (glm5.2 非流空响应) |
| thinking-timeout | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | thinking 请求扩展 timeout |
| deadline 基建 | R850/R1407/R1627 | 复用 `_stream_openai_passthrough` 同套 |
| zombie 检测 | R840/R852b | content<阈值 + 无真 tool_call + 大 input → api_error 让 CC 重试 |
| fallback | **无** (R1648c 才加) | 本轮纯端点新增 |

## 六、风险/遗留

- **无 fallback**: 5key 全坏仍返 502 (R1648c 加 nv breaker + ms_gw fallback 治此).
- **zombie 仍 emit api_error**: 复用 R840 语义, CC 重试整请求. R1648c 后若命中 nv breaker
  会直走 ms, 但本端点不感知 breaker.
- **THINKING_SIGNATURE 占位符**: 同 cc4101, CC 接受. 未真实验证 thinking 流式 (本轮 curl
  未带 thinking 字段). 后续真实 CC 请求会覆盖.
- **cc4101 仍走老路径**: R1648b 只加了 nv_gw 端点, cc4101 还没改 (R1648e 才让它纯透传到这).
  当前 CC 实际仍走 cc4101 的内部转换, 未用本端点. 需 R1648e 切换后才真正承接 CC 流量.
- **HM1 未同步**: 按框架, R1648 全系列留后续轮同步 HM1.

## 七、与历史轮次关系

- R1648a: 抽 cc4101 format 包 → 本轮复制进 nv_gw (anth_to_oai 原样, oai_to_anth 新建).
- R1640: cc4101 header 倒挂 + polarity 修复 → 本轮 polarity 逻辑在 nv_gw 的 oai_to_anth
  (zombie→api_error) 与 `_stream_openai_to_anth` 的 zombie 检测里复现.
- R753: nv_gw 删跨 model fallback → R1648c 反向加回 (nv→ms), 本轮未动.
- R1627: nv_gw stream 全量缓冲 → 本轮未沿用全量缓冲 (anthropic SSE 边转边写更直接,
  且 R1627 的卡死丢弃→content_filter→CC 重试语义已由 zombie 检测覆盖). 后续观察是否需引入.

## 八、下一步

R1648c: nv_gw 加 5key 全坏 → ms_gw fallback (glm5_2_nv 专) + nv breaker (阈值 15).
- config 加 NVU_MS_FALLBACK_URL/ENABLED/FAIL_THRESHOLD=15/SKIP_S=30.
- upstream.execute_request: all_keys_exhausted 后 POST ms_gw (openai body, model 换 glm5_2_ms).
- 加 nv breaker (复用 cc4101 circuit.py 模式).
