# R1711: cc4101 透传化 — 转换下沉 nv_gw/ms_gw /v1/messages (R1648 终态收尾 第2步)

> 轮号说明: 原计划名 R1705, 与同期 HM2→HM1 参数调参轮 R1705-R1710 撞号, 改用 R1711.
> 代码标记仍写 R1705 (已落地容器源码, 不回改), 轮文件用 R1711 落档.

## 背景 (接 R1704)

R1648 终态设想 (记忆 r1648a): **"转换下沉各网关, cc4101 终瘦纯透传"**.

R1704 (已提交, 在 origin) 给 nv_gw `/v1/messages` 补齐了 recv-fallback + content_filter
polarity, 使其诊断力 ≥ cc4101, 为 cc4101 透传化扫清前提.

本轮: 把 cc4101 从"双转换冗余" (自己 anth→oai 再 oai→anth, 同时 nv_gw /v1/messages 已能吃
anthropic 直入) 切到**纯透传**: cc4101 不再做格式转换, 直接把 CC 的 anthropic body 透给
nv_gw `/v1/messages` (primary) / ms_gw `/v1/messages` (fallback), 并把 nv_gw 已发的
anthropic SSE/JSON 原样回传 CC.

## 改前架构 vs 改后架构

| 维度 | 改前 (R1704 后) | 改后 (R1711) |
|---|---|---|
| cc4101 入站 | anth /v1/messages | 不变 |
| cc4101 转换 | anth→oai (converters.py) | **删除**, 直接透传 anth_body |
| 打 nv_gw 端点 | `/v1/chat/completions` (openai) | **`/v1/messages`** (anthropic) |
| 打 ms_gw 端点 | `/v1/chat/completions` | **`/v1/messages`** |
| model 字段 | cc4101 不改 (发 claude-*) | **cc4101 改写** → glm5_2_nv / glm5_2_ms (路由) |
| 回流转换 | oai SSE→anth (stream.py converter) | **纯透传** nv_gw 已发的 anthropic SSE |
| 诊断责任 | cc4101 自己判 zombie/content_filter | **下沉 nv_gw** (R1704 已补齐), cc4101 透传 api_error |
| breaker 信号 | 扫 chunk (内容级) | **纯连接级** (clean EOF=success, RemoteDisconnected/OSError=failure) |
| fallback 触发 | 流中途 zombie→切 ms_gw | **降级**: 流中途 zombie 不切 (透传 api_error 给 CC, CC 重试), 下个请求 breaker OPEN 才切 |

## 改前数据: 为何透传化

1. **双转换冗余**: cc4101 `anth→oai` + nv_gw `/v1/messages` 内部又 `oai→anth` (R1648b), 两段
   互逆转换无业务价值, 只增加字节码路径与 mojibake 风险面.
2. **诊断点分裂**: zombie/content_filter/recv-fallback 在 cc4101 与 nv_gw 各判一遍, 两套实现
   长期漂移 (R1640/R1674/R1675 踩过). R1704 已让 nv_gw 诊断力到位, cc4101 侧诊断成冗余.
3. **format 包重复**: cc4101/nv_gw/ms_gw 三处各持 format 包 (md5 一致 `10adc0f0...`), 透传后
   cc4101 不再需要, 为 R1712 收尾 (删 format/ + converters.py) 做准备.
4. **fallback 降级是接受的**: 流中途 zombie 透传 api_error 给 CC, CC 重试整请求; 只有 breaker
   OPEN (连接级连续失败) 才切 ms_gw. 用户已确认接受此降级.

## 关键前置验证 (改前已查证)

- nv_gw `detect_nv_model` 的 MODEL_MAP 只含 kimi/dsv4p/glm5_2 内部名+别名, **不含 claude-***;
  CC 发的 `claude-opus-4-8` 会被路由到 `DEFAULT_NV_MODEL=dsv4p_nv` (deepseek, **错误 tier**).
  → cc4101 必须改写 body.model 为 `glm5_2_nv` (primary) / `glm5_2_ms` (fallback).
  (dsv4p 是 hermes 主模型, 不是 CC 的 glm5.2 链.)
- nv_gw `/v1/messages` 已验证接受 `glm5_2_nv` 并返回正确 anthropic SSE.
- ms_gw `/v1/messages` (R1648d) 已验证接受 `glm5_2_ms` 并返回正确 anthropic 格式.
- format 包三处 md5 一致, 转换逻辑对等.

## 改动 (HM2 cc4101, /opt/cc-infra/proxy/cc4101/gateway/, bind-mount)

> 铁律: 只改 HM2. HM1 cc4101 仍缺 format/ 目录 (R1648 组只改 HM2), HM1 同步另轮.

### 1. upstream.py (patch A+B+E)
- `_call_upstream`: 透传原始 anthropic body; header 加 `anthropic-version: 2023-06-01`;
  `body_bytes = json.dumps(oai_body)` (oai_body 实为 anth_body).
- `_try_primary`: 加 `import copy as _copy; _pri_body = _copy.copy(oai_body); _pri_body["model"] = PRIMARY_UPSTREAM_MODEL`
  在 _call_upstream 前 (把 claude-* 改写为 glm5_2_nv 做路由).
- `_try_fallback`: 不变 (已深拷贝并改 model 为 FALLBACK_UPSTREAM_MODEL).
- docstring 注明 "R1705: oai_body 实为原始 anthropic body... 仅 model 字段在 _try_primary/_try_fallback 内改写做路由."

### 2. handlers.py (patch A+B+C)
- import: 删 `from .converters import anth_to_openai, _estimate_text_chars`;
  `from .stream import stream_to_anth, collect_stream_to_anth` → `from .stream import passthrough_stream, passthrough_nonstream`;
  加 `_estimate_input_chars(anth_body)` helper (用 `len(json.dumps(anth_body))`).
- `_handle_messages`: 删 `oai_body = anth_to_openai(...)` 与 `oai_body["stream"]=True`; 直接
  `execute_request(anth_body, ...)` 透传.
- success 路径: `passthrough_stream(self, resp, conn, metrics, t_start)` (流) /
  `passthrough_nonstream(...)` (非流) 替代旧转换函数.
- 请求日志标记 `(R1705 passthrough)`.

### 3. stream.py (新增 2 函数, 不删���)
- `passthrough_stream(handler, resp, conn, metrics, t_start)`: 纯透传 nv_gw anthropic SSE;
  `resp.read(8192)` + 写 raw bytes; 最小 stall-watcher (CC4101_STREAM_TOTAL_DEADLINE_S);
  OSError 走 recv-fallback; **breaker 信号纯连接级** (clean EOF=record_primary_success,
  RemoteDisconnected/Reset/OSError=record_primary_failure; client BrokenPipe 不计).
- `passthrough_nonstream(...)`: 读完整 body, `handler._send_raw(status, body_bytes, "application/json")`
  透传; breaker 连接级.
- 旧 `stream_to_anth`/`collect_stream_to_anth` 保留 (供 .bak 回滚, R1712 删除).

### 4. docker-compose.yml (cc4101 服务 env)
- `PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/chat/completions` → `.../v1/messages`
- `FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions` → `.../v1/messages`

## 改后验证 (HM2, 重启 cc4101 后)

重启: `cd /opt/cc-infra && docker compose up -d cc4101` (env 改动需 recreate, 非 restart).
备份: upstream.py.bak.R1705_pre / handlers.py.bak.R1705_pre / stream.py.bak.R1705_pre /
      docker-compose.yml.bak.R1705_pre.

1. **health**: `{"status":"ok","proxy_role":"cc4101","primary":"glm5_2_nv","port":4101}` ✅
2. **StartedAt**: 00:11:16 (新容器) ✅; 启动日志 `cc4101 listening on 0.0.0.0:4101` ✅
3. **真实 CC 请求**: `[REQ] model=claude-opus-4-8→glm5_2_nv cc_stream=True msgs=84 tools=30 (R1705 passthrough)` ✅
   — model 改写生效 (claude-*→glm5_2_nv), passthrough 路径标记出现.
4. **E2E 流**: stream=true 返回 anthropic SSE (message_start/content_block_start/content_block_delta,
   正文 "Hi there! 👋 How can I help you") ✅
5. **E2E 非流**: stream=false 返回 anthropic JSON ✅
6. **DB 路径标记**: `agent_type=_nv_anthropic | upstream=cc4101-primary | status=200` ✅
   — 请求正确打 nv_gw /v1/messages anthropic 端点.
7. **诊断联动 (关键回归)**: 改后 10min DB 按响应体积分档:

   | 体积档 | 200 | 502 (nv_gw 透传诊断) |
   |---|---|---|
   | <50k | 17 | 0 |
   | 50-200k | 55 | 5 (4 upstream_content_filter + 1 StreamStallWatcher) |
   | >200k | 22 | 20 (12 empty_stream_response + 8 upstream_content_filter) |

   - `upstream_content_filter` 12 条正是 R1704 在 nv_gw 补的 content_filter polarity 路径生效 ✅
   - `empty_stream_response` 12 条 (>200k) = nv_gw zombie 检测生效 ✅
   - `StreamStallWatcher` 1 条 = cc4101 passthrough 总时长兜底生效 ✅
   - 22 条 >200k 成功 = 大 input 透传正常, 没全坏 ✅
   - 10min 总 SR: 94×200 + 25×502 = 79.0% (502 全是 nv_gw 透传的 api_error, CC 重试)
8. **breaker 状态**: `('CLOSED', 0, 0)` — 纯连接级, 0 失败计入 (content_filter/empty_stream
   这些中途 zombie 不计 breaker, 符合设计; 不触发无谓 fallback). ✅
9. **无死循环回归** (R1672 铁律): 502 透传给 CC, CC 重试整请求, 不在 cc4101 内部循环;
   breaker 不会被中途 zombie 打开, 不会误切 ms_gw. ✅

## 参数表

| 参数 | 改前 | 改后 | 备注 |
|---|---|---|---|
| PRIMARY_UPSTREAM_URL | .../v1/chat/completions | .../v1/messages | anthropic 端点 |
| FALLBACK_UPSTREAM_URL | .../v1/chat/completions | .../v1/messages | anthropic 端点 |
| cc4101 格式转换 | anth→oai→anth (双转换) | 纯透传 | 转换下沉 nv_gw |
| cc4101 breaker 信号 | 扫 chunk (内容级) | 纯连接级 | clean EOF=success |
| cc4101 fallback 触发 | 流中途可切 | breaker OPEN 才切 | 接受降级 |
| cc4101 model 改写 | 不改 (发 claude-*) | glm5_2_nv/glm5_2_ms | 路由 (nv_gw MODEL_MAP 无 claude-) |

## 预期效果 (长期)

- cc4101 字节码路径收缩, mojibake 风险面减小.
- 诊断责任单一化 (只在 nv_gw), 不再两套实现漂移.
- 为 R1712 收尾 (删 cc4101 format/ + converters.py 死代码) 铺路.
- fallback 降级换来架构简洁: 中途 zombie 由 CC 重试而非 cc4101 内部切流, 避免半响应拼接.

## 下一步 R1712: 收尾

1. 删 cc4101 `gateway/format/` 目录 + `converters.py` (死代码, 透传后不再调用).
2. 评估 `circuit.py` 简化 (breaker 信号已纯连接级, 内容级逻辑可去).
3. 删 stream.py 旧 `stream_to_anth`/`collect_stream_to_anth`.
4. HM1 cc4101 同步 (HM1 缺 format/ 目录, 另轮处理; 铁律 HM2→HM1).

## 验证清单

- [x] health ok + StartedAt 新
- [x] 真实 CC 请求走 passthrough 路径 (model 改写生效)
- [x] E2E 流/非流返回正确 anthropic 格式
- [x] DB 路径标记 _nv_anthropic + cc4101-primary
- [x] 诊断联动: content_filter (R1704) + empty_stream + StreamStallWatcher 三路径生效
- [x] breaker CLOSED (纯连接级, 0 计入)
- [x] 无死循环回归 (502 透传, CC 重试)
- [x] 大 input (>200k) 仍可成功 (22 条 200)
