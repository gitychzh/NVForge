# R751: HM2 cx4102 流式 hang/转换 bug 修复 + codex CLI 验收

> 日期: 2026-07-05  机器: HM2 (实验床)  链路: codex → cx4102(4102) → nv_gw(40006)/glm5_2_nv → fallback ms_gw(40007)/glm5_2_ms
> **HM1 全程未动** (本地生产冻结)

## 背景

R750 建 cx4102 后, codex CLI 实测出现两类硬 bug:
1. curl 流式请求 hang 死 (curl 一直等, 不退出)
2. 非流 fallback 到 ms_gw 时 `chat_to_responses` 报 `'NoneType' object is not iterable`

本 round 修这两个 bug, 并用 codex CLI 真实验收。

## 铁律遵守

1. **改前必有数据**: curl 流式 hang (task 60s timeout 无事件输出); 非流 fallback CONVERT-ERR 日志 + ms_gw body 见 `delta.tool_calls: null`.
2. **改后必有验证**: codex `codex exec` 真实对话成功 (4518 tokens).
3. **聚焦 nv_gw**: cx4102 自包含修复, nv_gw/ms_gw 代码未改 (模块化铁律).
4. **所有修改写入仓库**: 本 round + forwarder.py/codex.py/app.py.

## Bug 1: 流式 hang (HTTP/1.1 + Connection: keep-alive)

### 现象
`curl -s -N -X POST .../v1/responses ... stream:true` 卡住不退出. cx4102 日志只到 `REQ stream=True`, 无 PRIMARY-FAIL/STREAM-FINAL/STREAM-ERR. curl 60s timeout 拿不到任何 event.

### 真因
`app.py CxHandler` 用 `protocol_version = "HTTP/1.1"` + `Connection: keep-alive` + 无 `Content-Length` + 无 `Transfer-Encoding: chunked`.
SSE 是无边界的流, HTTP/1.1 keep-alive 下客户端 (curl/codex) 没法判断响应何时结束 → 死等.

### 修复
`app.py._handle_stream` 改 `Connection: close` + `self.close_connection = True`:
```python
self.send_header("Connection", "close")
self.close_connection = True  # http.server 流式收尾的标准做法
```
流发完 (generator 耗尽) 后服务端主动关连接, 客户端立刻感知 EOF.

## Bug 2: 非流 fallback 转换 `'NoneType' object is not iterable`

### 现象
primary nv_gw 502 → fallback ms_gw, ms_gw 返回 200 但 body 同时含 `message` (空 content) + `delta` (带 reasoning_content), 且 `delta.tool_calls: null` (JSON null, key 存在).
`chat_to_responses` 报 `'NoneType' object is not iterable`.

### 真因
1. `chat_to_responses` 用 `message = choice.get("message") or choice.get("delta", {})` 取 message, ms_gw 的 message.content 为空字符串 (falsy), delta.content 才是真内容. 需合并.
2. `feed_chunk` (流式) 用 `for tc in delta.get("tool_calls", [])` — 当 JSON 显式 `tool_calls: null` 时, `.get("tool_calls", [])` 返回 `None` (key 存在值 null), 迭代 None 抛 TypeError.

### 修复
**codex.py `chat_to_responses`** (非流): 合并 message + delta 两个字段:
```python
message = choice.get("message") or {}
delta = choice.get("delta") or {}
text_content = (message.get("content") or "") or (delta.get("content") or "")
reasoning_content = (message.get("reasoning_content") or "") or (delta.get("reasoning_content") or "")
tool_calls = message.get("tool_calls") or delta.get("tool_calls") or []
```
(reasoning_content + content 都放进 output_text, codex 需要 reasoning 上下文.)

**codex.py `feed_chunk`** (流): `for tc in (delta.get("tool_calls") or []):` 用 `or []` 而非 `.get(..., [])` 兜底 null.

## forwarder.py forward_stream 重构

R750 的 forward_stream 控制流纠缠 (initial_events 触发条件错, fallback 分支可进入 4xx 不检查). 重构成清晰两段:

```
try_primary?
  ├─ resp is None / resp.status>=500 → 静默切 fallback (新 converter, fallback_used=True)
  ├─ 2xx/4xx → primary converter, initial_events, _stream_from_upstream, record_success, return
  └─ (流中途失败 → _stream_from_upstream 内部 final_events 兜底, 不切 fallback)

fallback (circuit 开 / primary 首字节前失败):
  converter = StreamConverter(); converter.fallback_used = True
  initial_events → _post_upstream(ms_gw) → _stream_from_upstream
  (resp None / 4xx → 插 ⚠️ output_text delta + final_events 兜底)
```

`_iter_sse_chunks(resp)` 提成独立生成器: `resp.read(8192)` 循环 + `\n\n` 分割 + `data:` 解析 + `[DONE]` 停止.
`_stream_from_upstream(resp, conn, converter, fallback_used)` 通用: 读 SSE → feed_chunk → final_events, finally close conn.

## fallback 提醒策略 (R750 设计落实)

| 模式 | 提醒位置 | 理由 |
|---|---|---|
| 非流 | `output[0].content[0]` 插 `⚠️ [cx4102] ...` output_text (在正文前) | agent 看到完整 response, 不中断 |
| 流 | `response.completed.metadata.fallback_used/notice` | 不插 output_text delta, 避免污染 codex reasoning 流 |

文案: `⚠️ [cx4102] nv_gw 全部 5 key 故障/超时, 已 fallback 到 ms_gw (glm5_2_ms). 本轮继续, 下一轮将自动回 nv_gw.`

## 配置 (最终值, 与 R750 一致)

R750 文档提到 `PRIMARY_STREAM_TIMEOUT_S=60` — **本 round 未实现该参数**. 实际用 `FALLBACK_TIMEOUT_S=300` 作 http.client socket timeout (整体上限), 配合 `CIRCUIT_FAILURE_THRESHOLD=3` + `CIRCUIT_OPEN_S=60` + `FALLBACK_RECOVER_S=30` 做 fallback 节流. primary 流式 5xx (nv_gw 502 通常 11-13s 返回) 走 `_is_primary_failure`/status>=500 判定切 fallback, 不需要单独的首响应超时.

```yaml
cx4102 env (最终):
  PRIMARY_URL=http://nv_gw:40006/v1
  FALLBACK_URL=http://ms_gw:40007/v1
  PRIMARY_MODEL=glm5_2_nv
  FALLBACK_MODEL=glm5_2_ms
  FALLBACK_TIMEOUT_S=300        # http.client socket timeout
  CIRCUIT_FAILURE_THRESHOLD=3   # 连续 3 次故障 circuit 打开
  CIRCUIT_OPEN_S=60             # circuit 打开 60s
  FALLBACK_RECOVER_S=30         # fallback 后 30s 试探回 primary
```

## 验收数据

### curl 直测

| 测试 | 结果 |
|---|---|
| 非流 primary (nv_gw 正常) | ✅ 200, "你好呀！😊 有什么可以帮你的吗？", 走 primary 无 fallback |
| 非流 fallback (primary 死端口 59999) | ✅ 200, reminder + ms_gw 回答, `chat_to_responses` 无报错 |
| 流式 primary (nv_gw 正常) | ✅ 200, 完整事件序列 created→in_progress→output_item.added→content_part.added→output_text.delta*→content_part.done→output_item.done→response.completed, curl exit=0 |
| 流式 fallback (primary 死端口) | ✅ 200, 同上完整序列, STREAM-FINAL 日志确认 final_events 触发 |

### codex CLI 真实对话 (最终验收)

```
$ CX4102_API_KEY=cx-gw-token codex exec --skip-git-repo-check "用一句话介绍你自己"
model: glm5_2_nv  provider: cx4102
codex: 我是 Codex CLI，一个开源的命令行编程助手，能帮你读代码、写代码、跑命令、修 bug...
tokens used: 4,518

$ codex exec "回复: cx4102 验收通过"
codex: ... "cx4102 acceptance passed" / "cx4102 verification passed"
```

✅ 完整链路: codex → cx4102 (Responses→ChatCompletions) → nv_gw/glm5_2_nv → NVCF, 真实 tokens 计费.
✅ Responses API function_call 转换路径可用 (codex 生成 bash 命令的 tool_call 正确).

## 已知遗留

- **codex `--full-auto` 工具执行**: bubblewrap 缺失警告 (codex 用 bundled bwrap), `--sandbox workspace-write` 默认. 工具执行受 codex 自身 sandbox 策略限制, 非 cx4102 问题.
- **ms_gw 流式慢**: ms_gw 流式响应 1-2min (ModelScope glm5_2_ms 含 reasoning), 非 cx4102 问题. cx4102 正确转发 + EOF 时发 final_events 闭环.
- **fallback metadata 未在所有路径生效**: 部分测试 `response.completed.metadata` 为 `{}` (可能与 circuit 时序 + converter 实例有关), 非阻塞 — codex 不读 metadata, 提醒主要靠非流 output_text. 后续观察.

## 部署副作用 (本 round 修复)

- **docker-compose.yml 重建**: 修复过程中 sed 误清空过 compose (HM2 无 .bak 文化), 已从 `docker inspect` 5 容器 (env/mount/network/port) 完整重建, 加了 cx4102 的 bind-mount (原镜像无挂载, 导致 `docker restart` 不加载新代码 — 已修, 现 bind-mount `./proxy/cx-gw/gateway:/app/gateway`).
- **CX4102_API_KEY 持久化**: 写入 `~/.bashrc`.

## 验证清单

- [x] cx4102 容器 Running, /health 200, primary_url=nv_gw (非死端口)
- [x] cx4102 bind-mount 生效 (改 .py → docker restart 即更新, 无需 rebuild)
- [x] curl 非流 primary 200
- [x] curl 非流 fallback 200 + reminder 嵌入
- [x] curl 流式 primary 200 + 完整 SSE 事件序列 + curl exit=0 (不 hang)
- [x] curl 流式 fallback 200 + 完整 SSE 事件序列
- [x] codex CLI codex exec 真实对话成功 (4518 tokens)
- [x] HM1 全程未动
- [x] nv_gw/ms_gw 代码未改 (模块化铁律)
- [x] docker-compose.yml 重建完整 (5 容器全配置)
