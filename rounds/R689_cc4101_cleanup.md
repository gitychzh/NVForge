# R689 — cc4101 系统性查漏补缺: 删冗余 + 修流式连接 + 验证全功能

> 范围: HM2 远程 `/opt/cc-infra/proxy/cc4101/`. 续 R688. 不改 HM1.
> 不属 nv_gw 优化主线, 但聚焦 cc2 链路. 全文 R-number 命名沿用 R680 后的消歧结果.

## 摘要

对 R688 新建的 cc4101 框架做一次整体系统性检查 — 通读全部 9 个源文件 (config/converters/
stream/upstream/handlers/db/logger/error_mapping/app) + Dockerfile + schema, 逐个函数
查 "是否被调用 / 是否被需要 / 有无隐藏 bug", 并实测 7 条功能路径.

**删冗余 (3 处死代码 + 3 处死 import + 1 个死 env):**
- `converters.py::openai_to_anth()` — 从未被调用 (collect 路径在 stream.py 内直接合成 Anthropic
  响应, 不走这个函数). 删除函数 + 其专用 import `THINKING_SIGNATURE_DEFAULT`.
- `config.py::_expected_auth_token()` — 从未被调用 (handlers.py 直接读 `CC4101_GATEWAY_API_KEY`). 删除.
- `config.py::PROXY_TIMEOUT` — 定义了但全文无人读 (handlers.py / stream.py 都 import 了
  但没用, 只用 `UPSTREAM_TIMEOUT`). 删除 config 定义 + 两处 import + compose env `PROXY_TIMEOUT: "600"`.
- `config.py::import time` — 删除 PROXY_TIMEOUT 后 `time` 也无人用. 删除.
- `handlers.py::UPSTREAM_TIMEOUT` import — 同样 import 了但全文没用. 删除.

**修 bug (1 处):**
- `stream.py::stream_to_anth()` 实时 SSE 路径没设 `Connection: close` / `close_connection=True`.
  CC (httpx, HTTP/1.1) 收完 SSE 后 socket 可能 keep-alive 不释放. 补 `send_header("Connection",
  "close")` + `handler.close_connection = True`. (非流式路径 `_send_raw` 本来就有这俩, 此前只有流式路径漏了.)

**验证全功能 (7 条路径全过):**
1. `/health` — 200, role=cc4101, primary/fallback 正确.
2. `/v1/models` — 200, 单 model `cc-glm5-2`.
3. 鉴权 — 无 token 401 / 错 token 401 / 对 token 通过.
4. 非流式 (collect→synthesize) — thinking+text block, stop_reason=end_turn, 18→115 token, 5.7s.
5. 流式 (real-time SSE) — 完整事件序列 message_start→content_block_start/delta/stop→
   message_delta→message_stop, stop_reason=max_tokens (80 token 截断).
6. tool_use 往返 — thinking+text+tool_use block, stop_reason=tool_use, tool input `{'city':'Tokyo'}` 正确解析.
7. 404 路径 — `POST /v1/foo` → 404.
8. PG 日志 — `cc_requests` 表新行全部落库 (input/output_tokens, duration, finish_reason 全对).

## 改前数据

R688 部署后容器健康, 但通读代码发现上述死代码 + 流式连接隐患. 无需数据驱动 (这是代码
卫生 + 连接正确性, 不是参数调优), 但每条修改路径改后都端到端实测 (见下"验证").

## 参数表 (R688 表的增量)

| 项 | R688 | R689 |
|---|---|---|
| `PROXY_TIMEOUT` env | `600` | **删除** (无人读, 删 config + compose + 两处 import) |
| `openai_to_anth()` | 存在 | **删除** (死代码, collect 在 stream.py 内合成) |
| `_expected_auth_token()` | 存在 | **删除** (死代码, handlers 直读 env) |
| `config.py::import time` | 有 | **删除** |
| `converters.py::import THINKING_SIGNATURE_DEFAULT` | 有 | **删除** (随 openai_to_anth 一起走) |
| `handlers.py::import {PROXY_TIMEOUT, UPSTREAM_TIMEOUT}` | 有 | **删除** (都没用) |
| `stream.py::import PROXY_TIMEOUT` | 有 | **删除** |
| `stream_to_anth` Connection:close | 缺 | **补** (`send_header` + `close_connection=True`) |

其余 R688 参数全部不变 (UPSTREAM_TIMEOUT=120, cc4101-token, primary=nv_gw/glm5_2_nv,
fallback=ms_gw/glm5_2_ms, 总是 stream, cc_requests 表, 14 天日志保留).

## 改动清单

### 1. `gateway/converters.py`
- 删 `from .config import THINKING_SIGNATURE_DEFAULT` (只剩 `MAX_TOOL_DESC,
  MAX_SCHEMA_DESC, CHARS_PER_TOKEN_ESTIMATE`).
- 删 `openai_to_anth()` 函数 + 其段落标题 (整段 ~65 行). 理由: collect_stream_to_anth
  在 stream.py 内直接构建 Anthropic dict 响应, 不经此函数; 流式路径在 stream.py 内逐
  event 构建. 两路径都不需要它.

### 2. `gateway/config.py`
- 删 `PROXY_TIMEOUT = int(...)` 行.
- 删 `import time` (PROXY_TIMEOUT 删后 `time` 无人用).
- 删 `_expected_auth_token()` 函数 (handlers.py 直接读 `CC4101_GATEWAY_API_KEY`).

### 3. `gateway/handlers.py`
- `from .config import (...)` 删 `PROXY_TIMEOUT` 和 `UPSTREAM_TIMEOUT` (两者都 import
  了但全文无引用; 实际超时由 upstream.py 的 `UPSTREAM_TIMEOUT` 控制).

### 4. `gateway/stream.py`
- `from .config import THINKING_SIGNATURE_DEFAULT, UPSTREAM_TIMEOUT, PROXY_TIMEOUT`
  → `from .config import THINKING_SIGNATURE_DEFAULT, UPSTREAM_TIMEOUT`.
- `stream_to_anth()` 在 `send_response(200)` 后补:
  ```python
  handler.send_header("Connection", "close")
  handler.close_connection = True
  ```
  与非流式 `_send_raw` 路径对齐, 避免 CC 端 socket keep-alive 不释放.

### 5. `docker-compose.yml`
- cc4101 块删 `PROXY_TIMEOUT: "600"` env (config 不再读). 备份 `docker-compose.yml.bak.R689`.
  其他服务的 `PROXY_TIMEOUT` 不动.

## 验证 (铁律: 改后必有验证)

部署方式: `cd /opt/cc-infra && docker compose up -d cc4101` (bind-mount, 不 rebuild).
重启后 `docker logs cc4101` 无 import error, START 行正常.

```
[17:35:34.1] [START] cc4101 listening on 0.0.0.0:4101 (role=cc4101)
[17:35:34.1] [START]   primary  : glm5_2_nv
[17:35:34.1] [START]   fallback : glm5_2_ms
[17:35:34.1] [START]   UPSTREAM_TIMEOUT=120s (per-upstream HTTP timeout)
[17:35:43.8] [REQ] model=claude-opus-4-8→glm5_2_nv cc_stream=False msgs=1 tools=0
[17:35:53.3] [REQ] model=claude-opus-4-8→glm5_2_nv cc_stream=True msgs=1 tools=0
[17:36:15.6] [REQ] model=claude-opus-4-8→glm5_2_nv cc_stream=False msgs=1 tools=1
```

端到端 8 项实测全过:

| # | 路径 | 结果 |
|---|---|---|
| 1 | `GET /health` | 200 `{"status":"ok","proxy_role":"cc4101","primary":"glm5_2_nv","fallback":"glm5_2_ms","port":4101}` |
| 2 | `GET /v1/models` | 200 单 model `cc-glm5-2` (context_window 170000) |
| 3 | `POST /v1/messages` 无 token | 401 authentication_error |
| 3b | `POST /v1/messages` 错 token | 401 |
| 3c | `POST /v1/messages` 坏 JSON + 对 token | 400 `bad request: Expecting value...` |
| 4 | 非流式 (stream=false) | 200, thinking+text block, stop_reason=end_turn, 18→115 tok, 5.7s |
| 5 | 流式 (stream=true) | 200 SSE 完整序列, 末尾 message_delta(stop_reason=max_tokens, 80 tok 截断)+message_stop |
| 6 | tool_use | 200, blocks=[thinking,text,tool_use], stop_reason=tool_use, input `{'city':'Tokyo'}` |
| 7 | `POST /v1/foo` | 404 `cc4101 only serves /v1/messages` |
| 8 | PG 日志 | `cc_requests` 新行落库: 161→55 tok tool_use, 14→80 tok stream, 18→115 tok 非流式, 全对 |

JSONL metrics (`/opt/cc-infra/logs/cc4101/metrics.2026-07-04.jsonl`) 每条 request 全字段
(request_id/ts/upstream_used/status/tokens/duration/finish_reason/error_type 等) 完整.
`estimated_input_tokens` (估算值) 只进 JSONL 不进 DB (刻意, 它不是真实 token).

## 观察点 (不修, 记录)

- **ms_gw 流式后 socket 不关**: ms_gw 发完 `data: [DONE]` 不发 `Connection: close`,
  `resp.read()` 会阻塞到 UPSTREAM_TIMEOUT. collect_stream_to_anth 用 `done` flag + 主动
  `conn.close()` 已解决 (R688 修). stream_to_anth 在 `_emit_graceful_end` 内也 `conn.close()`,
  同样不阻塞. 直连 curl 测 ms_gw 会挂 (因为没有这一层), 走 cc4101 不挂.
- **ms_gw fallback 路径 usage token=0**: ms_gw 最终 usage chunk 的 `choices:[]`, 代码取
  `chunk_data.get("usage")` 拿到 0 (nv_gw primary 路径正常). 已记 R688, 留待 cc2 真实
  fallback 流量验证是否影响 CC 计费/上下文窗口. 不影响功能 (CC 不靠这个 token 数决定截断).
- **assistant 历史 thinking block 被丢弃**: `anth_to_openai` 的 assistant 分支只处理
  text+tool_use, 上一轮的 thinking block 不回传给上游. glm5.2 不需要 thinking 历史 (它
  本轮自己生成 reasoning_content), 这是正确行为, 非 bug.

## 部署后状态

- `cc4101` 容器健康 (`Up, health: healthy`), bind-mount gateway/ 改 .py 只 restart.
- cc2 `~/.claude/settings.json` 仍指 `:4101` (R688 已切, 本轮不动).
- legacy 40000-40005+41001 (glm5.1 MS) 全部不动.
- HM1 未改 (只读).
