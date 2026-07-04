# R688 — cc4101: HM2 cc2 专用 glm5.2 链路 (干净独立, Anthropic↔OpenAI 转换)

> 范围: HM2 远程. 不改 HM1. 不属 nv_gw 优化主线 (nv_gw 仍是 40006 优化目标), 但与 cc2
> 有关的一切模型链路在此聚焦. 这是给 cc2 单独建的一条干净 glm5.2 链路, 与旧 legacy
> 40000-40005+41001 (glm5.1 MS) 解耦.

## 摘要

HM2 新建独立容器 `cc4101` (端口 4101), 只供 Claude Code (cc2) 调用. 功能: Anthropic
Messages API ↔ OpenAI Chat Completions 双向格式转换. 后端**只用 glm5.2**:
- primary: `nv_gw` (40006) `glm5_2_nv`
- fallback: `ms_gw` (40007) `glm5_2_ms` (primary 5xx/conn/timeout 时切换)

cc2 (`~/.claude/settings.json`) 从 `ANTHROPIC_BASE_URL=:40000` (legacy_dispatch→
legacy_cc→41001 glm5.1 MS) 切到 `:4101` (cc4101). legacy 链路保留不退役 (R682 决策).

带结构化 PG 日志 → `hermes_logs.cc_requests` 表 (异步队列 + daemon thread + batch
INSERT, 抄 nv_gw/ms_gw db.py 模式), 供长期系统性分析优化.

## 参数表

| 项 | 值 |
|---|---|
| 容器名 | `cc4101` |
| 对外端口 | `4101` |
| 镜像 base | `python:3.12-slim` (自写 proxy, 不 import litellm; 仅 `psycopg2-binary`) |
| 源码目录 | `/opt/cc-infra/proxy/cc4101/` (Dockerfile + gateway_main.py + gateway/*.py) |
| bind-mount | `./proxy/cc4101/gateway:/app/gateway` (改 .py 只 `docker compose up -d cc4101`, 不 rebuild) |
| PROXY_ROLE | `cc4101` |
| LISTEN_PORT | `4101` |
| UPSTREAM_TIMEOUT | `120`s (per-upstream HTTP timeout) |
| PROXY_TIMEOUT | `600`s (overall budget) |
| primary | `http://nv_gw:40006/v1/chat/completions`, model `glm5_2_nv`, token `nv-gw-token` |
| fallback | `http://ms_gw:40007/v1/chat/completions`, model `glm5_2_ms`, token `ms-gw-token` |
| 网关鉴权 | `CC4101_GATEWAY_API_KEY=cc4101-token` (CC 发 `Authorization: Bearer cc4101-token`; `/health` 免鉴权) |
| 上游策略 | **总是 stream=true** (CC stream=false 时 collect 合成非流式) |
| fallback 触发 | primary 5xx / conn / timeout → fallback; primary 4xx 不触发 (client/quota 错, 转也一样) |
| DB | `hermes_logs.cc_requests` (env `CC4101_DB_*=1`, host `logs_db`) |
| 日志 | `/opt/cc-infra/logs/cc4101/` (`proxy.*.log` + `metrics.*.jsonl` + `error_detail.*.jsonl`, 保留 14 天) |
| HOST_MACHINE | `opc2sname` |

## 改前数据 (铁律: 改前必有数据)

实测 HM2 两个 glm5.2 后端 (2026-07-04 16:1x):

1. **nv_gw `glm5_2_nv` 非流式**: 3×empty200, 全 key 失败 ("All NV API tiers failed for
   glm5_2_nv after 11.4s. Tiers tried: [glm5_2_nv: 3×empty200]"). 流式正常 (返回
   `reasoning_content` delta).
2. **ms_gw `glm5_2_ms` 非流式**: `finish_reason=length`, `content=""`, 答案全在
   `reasoning_content` 里 (50 token 就 length 截断). 流式正常.
3. **结论**: glm5.2 在两个后端**非流式都坏** (empty200 / content-empty). 只有流式可靠.
   → cc4101 上游**总是 stream=true**. CC 请求 stream=false 时, 网关 collect 上游 SSE
   合成非流式 Anthropic JSON 返 CC.
4. cc2 旧链路是 glm5.1 (legacy_ms_litellm 41001), 不是优化目标, 但 cc2 切走后零流量,
   保留不退役.

参考代码 (HM1 只读): `legacy-cc/gateway/{converters,stream,handlers,error_mapping,logger}.py`
+ `nv-gw/gateway/db.py` + `postgres/{hermes-logs,ms}-schema.sql`. cc4101 从这些精简而来
(去掉 v×k cycling / NV tier / MS-NV interleaving / glm5.1 thinking_budget 注入).

## 设计要点

- **8 个 .py 模块** (config/converters/stream/error_mapping/upstream/db/logger/handlers)
  + app.py + gateway_main.py + Dockerfile. 每个职责单一, 注释清晰.
- **upstream.py 两段式**: primary → fallback. 无 v×k, 无 tier. 4xx 不转 fallback.
- **stream.py**: `stream_to_anth` (实时 SSE) + `collect_stream_to_anth` (collect 合成).
  `reasoning_content → thinking block`, `content → text block`, `tool_calls → tool_use block`.
- **db.py**: 异步队列 (max 2000) + daemon thread + batch INSERT (50/batch 或 2s).
  DB down → 队列满 → 丢; JSONL 是 ground truth.
- **cc_requests 表**: 21 列 (request_id PK, ts, host_machine, request_model,
  mapped_model, upstream_used, fallback_triggered, is_stream, tokens, ttfb, duration,
  status, finish_reason, error_type/message, primary_error_type/elapsed). 5 个索引 + 2 个视图.

## 修复记录 (实施中)

1. **collect_stream 卡 120s**: ms_gw 流式发完 `[DONE]` 后 socket 不关 (无
   `Connection: close`), `resp.read()` 阻塞到 UPSTREAM_TIMEOUT. 修: 在 `[DONE]` 时
   主动 `conn.close()` + `done=True` 跳出外层循环. (stream.py collect 路径)

## 验证 (改后必有验证)

1. `docker compose up -d --build cc4101` → healthy. `curl /health` → ok.
2. 非流式 `/v1/messages` (primary nv_gw): `content=[thinking, text]`, text="Hi there,
   friend.", usage output_tokens=353, 17s. ✓
3. 流式 `/v1/messages` stream=true: SSE 完整 (message_start / 2×content_block_start /
   40×content_block_delta / 2×content_block_stop / message_delta / message_stop). ✓
4. fallback (临时把 primary URL 指向 59999 死端口): `PRIMARY-FAIL conn` → `FALLBACK-OK`
   → ms_gw glm5_2_ms 接管, HTTP 200, 合成响应. ✓
5. DB: `cc_requests` 7 行, primary 200, tokens/duration 齐全. ✓
6. JSONL: `logs/cc4101/{proxy,metrics,error_detail}.2026-07-04.{log,jsonl}` 齐全. ✓
7. cc2 settings.json: `ANTHROPIC_BASE_URL=http://127.0.0.1:4101`,
   `ANTHROPIC_API_KEY=cc4101-token`, `model=cc-glm5-2`. 备份 `settings.json.bak.pre_cc4101`.
   从 127.0.0.1:4101 模拟 CC 调用成功. ✓ (cc2 当前无运行进程, 下次启动即用新链路)

## 预期效果

- cc2 走干净 glm5.2 链路, 与 legacy glm5.1 解耦, 不受 legacy 链路问题影响.
- primary 用 nv_gw (NVCF, 无 RPM 限制), fallback 用 ms_gw (7 key×10 variant 2D 轮转)
  做兜底, 双保险.
- 全程结构化日志入 PG, 可长期分析: success rate / latency / fallback rate /
  primary 失败分布 / token 消耗, 指导后续 cc2 链路优化.
- 流式强制避免 glm5.2 非流式 empty-content 陷阱.

## 边界 / 不碰

- 不改 HM1 (只读参考).
- 不改 nv_gw / ms_gw / legacy_* 任何容器.
- 不改 cc2 的 model selection / thinking / tool_calls 逻辑 (cc4101 只格式转换+转发).
- 只用 glm5.2 (不掺 dsv4p/kimi/glm5.1).
- legacy 40000-40005+41001 保留不退役.

## 文件清单 (HM2 新增)

- `/opt/cc-infra/proxy/cc4101/{Dockerfile, gateway_main.py, cc4101-schema.sql}`
- `/opt/cc-infra/proxy/cc4101/gateway/{__init__,config,converters,stream,error_mapping,upstream,db,logger,handlers,app}.py`
- `/opt/cc-infra/postgres/cc4101-schema.sql`
- `/opt/cc-infra/docker-compose.yml` (加 `cc4101` service, 备份 `.bak.R684`)
- `~/.claude/settings.json` (cc2 切到 4101, 备份 `.bak.pre_cc4101`)

## 后续观察点

- cc2 实际跑起来后的 success rate / latency (查 `v_cc4101_upstream_health_1h`).
- primary empty200 是否频发 (nv_gw glm5_2_nv 非流式已知 empty200, 但 cc4101 强制流式
  应该规避; 流式路径若 empty_stream_response 也只能让 CC 重试 — 监控此指标).
- ms_gw fallback 时 usage token 0 的问题 (ms_gw 最终 usage chunk 是 `choices:[]`,
  当前代码已 try `chunk_data.get("usage")` 但实测 0; 待 cc2 真实流量验证是否系统性).
