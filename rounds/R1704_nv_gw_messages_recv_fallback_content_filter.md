# R1704: nv_gw /v1/messages 补 recv-fallback + content_filter polarity (R1648 终态收尾 第1步)

## 背景

R1648 终态设想 (记忆 r1648a): "转换下沉各网关, cc4101 终瘦纯透传"。
cc4101 当前打 nv_gw 的 `/v1/chat/completions` (OpenAI 端点), 自己做双向转换,
与 nv_gw 已有的 `/v1/messages` (anthropic 端点, R1648b) 形成"双转换冗余"。

为让 cc4101 透传化 (R1705), 前提: nv_gw /v1/messages 的诊断力必须 ≥ cc4101,
否则透传后丢诊断能力, CC 回归 R1640/R1674 前的死循环。

## 改前数据: 诊断点覆盖比对 (cc4101 stream.py vs nv_gw /v1/messages)

| 诊断点 | cc4101 | nv_gw /v1/messages | 覆盖 |
|---|---|---|---|
| zombie_empty_completion | L432-444 | L1013-1028 流 + L1168-1178 非流 | ✅ |
| upstream_content_filter + polarity | L395-418 | (只判 stop/tool_calls) | ❌ 缺 |
| recv-fallback (http.client timed-out-object) | L241-272 流 + L562-580 非流 | (continue 丢数据) | ❌ 缺 |
| stall-watcher 双门槛 | L198-221 | L869-880 (分档更细) | ✅ |
| first-byte deadline 分档 | upstream.py | L884-892 (4档) | ✅ |
| clean_eof / malformed SSE 兜底 | L282-294,L328 | — | 不需要 (nv_gw 不发自己 error chunk 给自己) |
| client_gone (BrokenPipe) | L84 | L956 | ✅ |

缺的 2 类是实锤踩过的坑:
- recv-fallback: CC "Request timed out" 死循环根因 (记忆 r1674)
- content_filter polarity: 503 死循环根因 (记忆 r1640)

## 改动 (HM2 nv_gw, /opt/cc-infra/proxy/nv-gw/gateway/handlers.py, bind-mount)

只改 /v1/messages 的 `_stream_openai_to_anth` + `_collect_stream_to_anth` 两个函数,
不碰 openai `/v1/chat/completions` 路径 (agents 走的, 隔离)。

### 改动1: _stream_openai_to_anth recv-fallback (镜像 cc4101 L241-272)
`except OSError` 的 timed-out-object 分支: 旧 `continue` 丢数据 → 改用 `sock.recv(MSG_PEEK)`
看 socket buffer 有无已到达数据 (如 NVCF 发的 [DONE]/content_filter), 有则 `recv` 取出当 chunk
处理 (能正常结束), 无则 continue 让 deadline 兜。

### 改动2: _collect_stream_to_anth recv-fallback (镜像 cc4101 L562-580)
同上, collect (非流式) 路径补同款 recv-fallback。R1674 只修了 cc4101, nv_gw /v1/messages
的 collect 路径一直缺。

### 改动3: _stream_openai_to_anth content_filter polarity (镜像 cc4101 L395-418)
finish_reason 分支前加 content_filter 处理:
- content=0 + reasoning=0 → nv_gw 主动快速失败 (first-byte/no-content-gap/total-deadline break),
  发 api_error 让 CC 重试, **不计** big_input breaker (polarity: 主动 break 非上游坏)。
- content>0 → 真中途死亡, 计 big_input breaker。
zombie stop/tool_calls 原逻辑不变 (改 elif 衔接)。

## 验证 (R1704)

- 备份: `handlers.py.bak.R1704_pre` (101370 bytes)
- 改后语法: `ast.parse` OK
- 重启: `docker compose restart nv_gw` (bind-mount, restart 非 up-d)
- 三看: StartedAt=18:31:36 (新进程) + "Listening on 0.0.0.0:40006" 日志 + 容器内 grep R1704=3 处标记
- health: `{"status":"ok",...}` 200
- 功能: `POST /v1/messages` (stream=false, "say hi") → 返回 anthropic 格式 message JSON
  (`content:[{type:text,text:"Hello to you!"}]`, `stop_reason:end_turn`, `usage`)。
  这是透传化后 cc4101 将收到的格式, 端点+转换正常。
- 隔离: openai /v1/chat/completions 路径 (agents + 当前 cc4101) 不受影响。
  30min 窗口: `cc4101-primary` 4OK/1 stream_no_content_gap (改前稳态失败模式, 非回归);
  `_nv_anthropic` 1OK (本轮测试请求); 无 content_filter 类新错误回归。
- big_input breaker: CLOSED (正常, 新逻辑待自然触发)。

recv-fallback + content_filter polarity 现处"已部署、待自然触发"状态——只在 NVCF 发
content_filter / http.client 崩坏时触发, 正常流量看不到, 但 R1705 透传化后这些诊断点
会在 nv_gw 侧兜住, 不再依赖 cc4101。

## 参数表

无参数变更 (纯诊断逻辑补齐)。

## 预期效果

- nv_gw /v1/messages 诊断力补齐到 cc4101 同等, 为 R1705 (cc4101 透传化) 扫除障碍。
- 即便不推进 R1705, 也提升 nv_gw /v1/messages 端点健壮性 (独立收益)。
- recv-fallback 治本 CC "Request timed out" 死循环 (r1674 在 nv_gw 侧的对称修复)。
- content_filter polarity 治本 503 死循环 (r1640 polarity 原则下沉到 nv_gw)。

## 下一步

R1705: cc4101 透传化 (打 /v1/chat/completions → 改打 /v1/messages, 删双向转换, 瘦身 stream.py)。
R1706: 收尾 (删 cc4101 format/ + converters.py 死代码, HM1 同步)。

铁律: 只改 HM2, 不改 HM1 (HM1 cc4101 缺 format/ 目录, 本轮不进场)。
