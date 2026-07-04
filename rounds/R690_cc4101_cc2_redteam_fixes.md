# R690: cc4101 cc2 红队审计修复

**日期**: 2026-07-04
**主机**: HM2 (远程修改，HM1 不动)
**范围**: cc4101 容器 (端口 4101，cc2 专用 glm5.2 Anthropic↔OpenAI 转换网关)
**性质**: cc2 红队审计 (深度逐行分析) 后提交 bug，本机修复。**非 nv_gw 优化主线**，
属 cc2 模型链路加固，但满足"改前有数据/改后有验证/写入仓库"铁律。

## 背景

用户要求"再次深度分析框架结构，精细到每处源码，并与 cc2 讨论，让它来找 bug，提交给你修复"。
R689 只做了静态清理 + 路径验证，未做语义级红队。本轮驱动 cc2 实际通过 cc4101 跑通
(此前 R688 "端到端验证" 仅 curl 测过，从未让 cc2 真正调用 —— R690 发现 cc2 用
`x-api-key` 头而非 `Authorization: Bearer`，原 auth 校验只认 Bearer → cc2 一律 401)。

修复 auth 后 cc2 跑通，对其自身源码做红队审计，产出 23KB 报告。本机据报告逐条修复。

## 数据 (改前)

- cc2 通过 cc4101 首调即 401 (auth 只认 `Authorization: Bearer`，cc2/Anthropic JS SDK 发 `x-api-key`)
- 抓包验证 (HM2 :14101 头捕获服务): `'x-api-key': 'cc4101-token'`，无 Authorization 头
- 跑通后 cc2 一次 5 token 回答 TTFB 34s (glm5.2 深度思考)，曾出现 382411ms
  `stream_socket_timeout` 超 UPSTREAM_TIMEOUT=120s → 暴露 collect 路径 502 当 200 返回
- cc2 报告按 CRITICAL/HIGH/MEDIUM 三级列 bug，与本机自审一致；本机另捕一条
  (`error_mapping.py:47` "rate" 误匹配) cc2 未提

## 修复 (按严重度)

### CRITICAL

| ID | 文件 | 问题 | 修复 |
|---|---|---|---|
| Auth | handlers.py:66-86 | 只校验 `Authorization: Bearer`；cc2 发 `x-api-key` → 全 401 | 同时接受 `x-api-key` 与 `Bearer`；R690 已先行上线验证 |
| C1 | stream.py | 流式中途异常 (socket.timeout/RemoteDisconnected) 伪造 `end_turn` 收尾，CC 收到"成功"假响应无法重试 | `_emit_graceful_end` 加 `interrupted=False` 形参；异常分支传 `True`，且 `pending_stop_reason is None` 时发 Anthropic `error` SSE (api_error) + message_stop，置 metrics status=502，让 CC 重试 |
| C3 | stream.py `collect_stream_to_anth` | 收集路径无视 metrics status，固定 `_send_json(200, anth_response)` → 502 也当 200 回 | 取 `client_status=metrics.status`，≥400 时改发 `convert_error` 的 Anthropic 错误 payload |

### HIGH

| ID | 文件 | 问题 | 修复 |
|---|---|---|---|
| H1 | stream.py reasoning 分支 | text/tool_use 块开后又来 reasoning_content → 试图重开 thinking 块，违反 Anthropic 协议(thinking 必须在 text/tool_use 之前，不可重开) | `active_block_type not in (None,"thinking")` 时丢弃后续 reasoning_content |
| H2 | converters.py:296 | `max_tokens` 默认 4096，glm5.2 思考模式 reasoning_content 可消耗数千 token，留给正文不足 → finish_reason=length 截断 | 默认改 8192 |
| H3 | converters.py:315 | `if body.get("temperature")` 真值判断 → temperature=0/top_p=0 被丢弃，参数到不了上游 | 改 `"temperature" in body` / `"top_p" in body` 显式存在性检查 |
| H4 | converters.py:261-273 | assistant 历史里 thinking 块被完全丢弃 → 多轮思考上下文丢失 | thinking 块转 `[thinking]\n...\n[/thinking]` 文本拼接进 text_parts |
| H5 | converters.py:226-251 | tool_result.content 为 dict (单块) 时落入空串 → 工具结果体丢失；is_error 未透传 | 加 `elif isinstance(tc, dict)` 分支；is_error 加 `[tool_error]` 前缀 |
| E1 | error_mapping.py:47 | `"rate" in msg_lower` 误匹配 "operate/moderate/generate" → 普通 api_error 被误判 rate_limit_error | 收紧为 `"rate limit" / "rate_limit" / "429"` |

### MEDIUM

| ID | 文件 | 问题 | 修复 |
|---|---|---|---|
| M3 | db.py enqueue_metrics | queue.Full 静默 pass → 队列满时数据丢失无感知 | 加 `_dropped_count` 计数 + 每 50 条打日志；暴露 `dropped_count()` 给 health |
| M4 | db.py stop_worker | atexit 不 join worker → 进程退出时 worker 可能正在写半截 psycopg2 连接 | drain+flush 后 `t.join(timeout=5)` (排除当前线程) |
| M5 | config.py / docker-compose.yml | LISTEN_HOST=0.0.0.0 + ports: 4101:4101 → 端口对全网卡暴露 | compose 改 `127.0.0.1:4101:4101` 仅 loopback 发布 (容器内仍 0.0.0.0，Docker 发布层限本机) |
| M6 | handlers.py auth | `==` 比较 token → 时序侧信道 | `hmac.compare_digest` |
| M7 | handlers.py body 读取 | 无上限读 Content-Length → 内存 DoS 风险 | 上限 50MB，越界返 413 |

## 部署/验证

```
scp 6 文件 → HM2 /opt/cc-infra/proxy/cc4101/gateway/
docker exec cc4101 py_compile 全 OK
docker compose up -d cc4101 (compose ports 改 127.0.0.1:4101:4101)
```

端到端验证 (HM2 实测):
- `/health` → HTTP 200 ok
- 无 auth → 401；错 token → 401；`x-api-key: cc4101-token` → 200
- Content-Length 99999999 → HTTP 413 invalid_request_error
- cc2 `claude -p "Reply PONG"` (shell env 内联覆盖 settings) → `PONG` ✅
- cc2 `claude -p` + Bash 工具调用 (tool_use→tool_result 往返) → 正确返回 `HI_FROM_CC2` ✅
- docker logs 验证期无 ERROR

## 非目标 / 不动

- nv_gw (40006) 优化主线本轮不碰
- legacy 40000-40005+41001 链路保留不退役 (R682)
- cc2 模型选择/思考强度/tool_calls 逻辑不动 (cc4101 只做格式转换+上游转发)
- HM1 不修改

## 待观察

- glm5.2 深度思考 TTFB 34s / 偶发 382s stream timeout：非 cc4101 可解 (上游 nv_gw/NVCF 侧)，
  C1/C3 修复后至少不再伪装成功，CC 会重试。
- cc2 是否会真发 dict 形 tool_result.content 或 assistant thinking 块：当前 cc2 实测走 list 形，
  H4/H5 为协议合规修复，对当前 cc2 调用为 no-op，但防未来 client 行为变化。
