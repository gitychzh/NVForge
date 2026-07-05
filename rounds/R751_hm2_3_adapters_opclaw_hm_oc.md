# R751: HM2 opclaw4103/hm4104/oc4105 三个 ChatCompletions 适配器

> 日期: 2026-07-05  机器: HM2 (实验床)  链路: 3 agent → 41xx 适配器 → nv_gw/ms_gw
> **HM1 全程未动** (本地生产冻结)

## 背景

R750 建 cx4102 (codex 适配器) 后, 继续为 openclaw/hermes/opencode 建对称的 41xx 适配器,
实现 5 agent 完全解耦。与 cx4102 区别: 这 3 个 agent 都用 ChatCompletions API (非 Responses),
**不需要 Responses↔ChatCompletions 转换**, 只需"ChatCompletions 透传 + 可选 fallback"。

## 设计决策 (用户拍板)

openclaw/hermes 自身已有 fallback 机制 (primary+fallbacks 数组)。若 41xx 也做 fallback 会双重 fallback。
**用户选: 41xx 自带 fallback, agent 简化为单 base_url** (与 cx4102 一致, fallback 逻辑集中可调)。
后续改 3 agent config 时删 agent 自身 fallback 字段。

## 通用 cc-adapter 源码 (一镜像三容器)

路径: `/opt/cc-infra/proxy/cc-adapter/gateway/` (bind-mount, 改完 docker restart 即可)

| 文件 | 作用 |
|---|---|
| config.py | env-overridable, ADAPTER_NAME/PRIMARY_URL/FALLBACK_ENABLED 等 |
| forwarder.py | CircuitState + _post_upstream + 透传 + fallback (复用 cx4102 框架, 去掉 Responses 转换) |
| app.py | http.server, 路由 /v1/chat/completions + /v1/embeddings + /health |
| gateway_main.py | 入口 |
| logger.py | JSON-line stdout + 文件 |
| Dockerfile | `FROM python:3.12-slim`, ENTRYPOINT `gateway/gateway_main.py` |

**与 cx4102 的区别**:
- 不做 Responses↔ChatCompletions 转换 (agent 直接用 ChatCompletions)
- fallback reminder 插入 chat 响应 (非流: choices[0].message.content 前缀; 流: 首 content delta 前插 chunk)
- 多了 `/v1/embeddings` 透传 (opclaw memorySearch 用, 无 fallback)
- 多了 `FALLBACK_ENABLED` 开关 (oc4105 设 0 禁用 fallback)

## 3 个容器

| 容器 | 端口 | primary | fallback | fallback_enabled | ADAPTER_API_KEY |
|---|---|---|---|---|---|
| opclaw4103 | 4103 | nv_gw/glm5_2_nv | ms_gw/glm5_2_ms | 1 | opclaw-gw-token |
| hm4104 | 4104 | nv_gw/dsv4p_nv | ms_gw/dsv4p_ms | 1 | hm-gw-token |
| oc4105 | 4105 | nv_gw/kimi_nv | (无) | 0 | oc-gw-token |

模型一致性: openclaw 全程 glm5.2, hermes 全程 dsv4p, opencode 只 kimi_nv (无 fallback, 用户明确要求)。

## fallback 策略 (与 cx4102 一致, 自包含)

- primary 5xx / 连接失败 / 流式首响应超时 (PRIMARY_STREAM_TIMEOUT_S=60) → 切 fallback
- primary 流中途失败 → 不切 fallback, 直接收尾 (无法回溯)
- 连续 3 次故障 → circuit 打开 60s, 直接走 fallback
- circuit 打开后 30s → 试探回 primary
- fallback 时 reminder 插入响应 (不中断 agent 任务)
- oc4105 (FALLBACK_ENABLED=0): primary 不可用直接返 503, 不切

## 验收数据 (curl 直接测)

| 测试 | 结果 |
|---|---|
| oc4105 kimi_nv 非流式 | ✅ HTTP 200, 3.3s, primary 直接成功 |
| oc4105 kimi_nv 流式 | ✅ HTTP 200, 5.2s, SSE 正确 |
| hm4104 dsv4p_nv 非流式 | ✅ HTTP 200, 8.4s, primary 成功 (带 reasoning) |
| hm4104 dsv4p_nv 流式 | ✅ HTTP 200, SSE 正确 ("字：你、好、世。") |
| opclaw4103 glm5_2_nv 非流式 (nv_gw 502 → fallback) | ✅ HTTP 200, 19s, PRIMARY-FAIL → FALLBACK-STREAM, ms_gw glm5_2_ms 返回, reminder 注入 content 前缀 |

**注**: opclaw4103 的 glm5_2_nv 在 HM2 当前 nv_gw 不稳 (R696/R705 已知: HM2 出口打 NVCF glm5.2 挂),
正好验证 fallback 触发。kimi_nv/dsv4p_nv 在 nv_gw 上稳定, primary 直接成功。

## 已知小瑕疵 (todo, 不影响功能)

- 流式响应末尾有时两个 `[DONE]` (`_stream_from_upstream` finally 总 yield done, 加上游自己的 done)。
  客户端处理第一个 [DONE] 就停, 多余的无害。下轮修。

## 后续 pending (等用户拍板)

- [ ] 改 openclaw config: primary → opclaw4103/glm5_2_nv, fallbacks 删 (让 41xx 处理)
- [ ] 改 hermes config: provider → hm4104/dsv4p_nv, fallback_providers 删
- [ ] 改 opencode config: provider → oc4105/kimi_nv
- [ ] 3 agent 各自验收 (真实对话)
- [ ] 删 nv_gw FALLBACK_GRAPH (A 类跨模型 fallback, 41xx 已做)
- [ ] HM1 同步 (待 HM2 观察窗口跑稳 + 用户拍板)

## 验证清单

- [x] cc-adapter 源码 6 文件 + Dockerfile, py_compile 通过
- [x] cc-adapter:latest 镜像 build 成功
- [x] 3 容器 opclaw4103/hm4104/oc4105 Running, /health 200
- [x] oc4105 kimi 非流+流式 200 (primary 成功)
- [x] hm4104 dsv4p 非流+流式 200 (primary 成功, 带 reasoning)
- [x] opclaw4103 fallback 触发 (nv_gw 502 → ms_gw, reminder 注入)
- [x] HM1 全程未动
- [x] nv_gw/ms_gw 代码未改 (模块化铁律)
- [x] compose 加 3 服务, docker compose config 校验通过
