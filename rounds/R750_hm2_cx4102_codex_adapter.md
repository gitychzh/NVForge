# R750: HM2 cx4102 codex 适配器 (Responses↔ChatCompletions 互转 + fallback)

> 日期: 2026-07-05  机器: HM2 (实验床)  链路: codex → cx4102(4102) → nv_gw(40006)/glm5_2_nv → fallback ms_gw(40007)/glm5_2_ms
> **HM1 全程未动** (本地生产冻结, 待 HM2 观察窗口后用户拍板才同步)

## 背景

R705 退役 HM2 legacy 链路后, HM2 仅剩 4 容器 (nv_gw/ms_gw/logs_db/cc4101)。
codex 原走 100.113.71.43:40001 (HM1 legacy) — 跨机耦合, 不整洁。
本 round 建 cx4102 适配器, 让 codex 走 HM2 本地 4102, 与 cc4101 对称, 为后续
opclaw4103/hm4104/oc4105 (openclaw/hermes/opencode 解耦) 铺路。

## 铁律遵守

1. **改前必有数据**: R705 已确认 HM2 legacy 退役干净; codex 跨机走 HM1 是历史遗留。
2. **改后必有验证**: codex CLI `codex exec` 真实对话成功 (4490 tokens 计费)。
3. **聚焦 nv_gw**: cx4102 是 nv_gw 的前端适配, 不改 nv_gw/ms_gw 任何代码 (模块化铁律)。
4. **所有修改写入仓库**: 本 round 文件 + compose + 源码。

## 架构

```
codex CLI (wire_api=responses)
  → 127.0.0.1:4102 (cx4102, Python http.client)
     → /v1/responses 入, 转 /v1/chat/completions 打 primary
     → primary: http://nv_gw:40006/v1/glm5_2_nv  (NVCF 5 key 轮转/429/空响应/NVCF 由 nv_gw 处理)
     → fallback: http://ms_gw:40007/v1/glm5_2_ms  (MS 7 key × 10 variant 由 ms_gw 处理)
     → 响应转回 Responses SSE 返 codex
```

**模型一致性**: codex 全程 glm5.2 (primary glm5_2_nv → fallback glm5_2_ms, 同模型跨后端)。
**模块化铁律**: cx4102 自包含 fallback 逻辑 (CircuitState + 首响应超时), nv_gw/ms_gw 不动。

## cx4102 容器

- 路径: `/opt/cc-infra/proxy/cx-gw/gateway/` (bind-mount, 改完 `docker restart` 即可, 无需 rebuild)
- 源码: gateway_main.py, app.py, codex.py (Responses↔ChatCompletions 转换 + StreamConverter),
  forwarder.py (CircuitState + 转发 + fallback), config.py (env-overridable, 无 key), logger.py
- 鉴权: `CX_GATEWAY_API_KEY=cx-gw-token` (与 nv-gw-token/ms-gw-token 解耦)
- 后端 key: 用 `nv-gw-token` / `ms-gw-token` 访问后端 (cx4102 不持 key)

## fallback 策略 (自包含, 不依赖 nv_gw/ms_gw)

| 触发条件 | 行为 |
|---|---|
| primary 连接失败 (TimeoutError/ConnectionRefused) | 立即切 fallback, record_failure |
| primary 5xx (含 502/504/all_tiers_exhausted) | 立即切 fallback, record_failure |
| primary 流式首响应超时 (PRIMARY_STREAM_TIMEOUT_S=60s) | 切 fallback (避免 nv_gw 流式挂死干等 300s, R696 已知问题) |
| primary 流中途失败 (已发部分流) | 不切 fallback, 发 final 收尾 (无法回溯) |
| 连续 3 次故障 (CIRCUIT_FAILURE_THRESHOLD=3) | circuit 打开 60s, 直接走 fallback |
| circuit 打开后 30s (FALLBACK_RECOVER_S=30) | 试探回 primary |

**提醒文案** (fallback 时插入, 不中断 agent 任务):
`⚠️ [cx4102] nv_gw 全部 5 key 故障/超时, 已 fallback 到 ms_gw (glm5_2_ms). 本轮继续, 下一轮将自动回 nv_gw.`
- 非流: 放 response.output[0].content[0] (output_text, 在正文前)
- 流: 放 response.completed.metadata (不插 output_text delta, 避免污染 codex reasoning 流)

## 配置 (compose env, 最终值)

```yaml
cx4102:
  environment:
    - LISTEN_PORT=4102
    - AUTH_ENABLED=1
    - PROXY_TIMEOUT=300           # 整体请求超时上限
    - PRIMARY_URL=http://nv_gw:40006/v1
    - PRIMARY_MODEL=glm5_2_nv
    - FALLBACK_URL=http://ms_gw:40007/v1
    - FALLBACK_MODEL=glm5_2_ms
    - FALLBACK_TIMEOUT_S=300      # 整体 socket 超时上限
    - PRIMARY_STREAM_TIMEOUT_S=60 # primary 流式首响应超时 (新增, 本 round 关键参数)
    - CIRCUIT_FAILURE_THRESHOLD=3
    - CIRCUIT_OPEN_S=60
    - FALLBACK_RECOVER_S=30
    - NV_GW_API_KEY=nv-gw-token
    - MS_GW_API_KEY=ms-gw-token
    - CX_GATEWAY_API_KEY=cx-gw-token
```

## codex CLI 配置 (`~/.codex/config.toml`)

```toml
model = "glm5_2_nv"
model_provider = "cx4102"
[model_providers.cx4102]
name = "CX Gateway 4102 (Responses→ChatCompletions, glm5_2_nv)"
base_url = "http://127.0.0.1:4102/v1"
env_key = "CX4102_API_KEY"
wire_api = "responses"
requires_openai_auth = false
request_max_retries = 4
stream_max_retries = 5
stream_idle_timeout_ms = 300000
models = ["glm5_2_nv", "glm5_2_ms"]
```

env: `export CX4102_API_KEY=cx-gw-token` (写进 ~/.bashrc 或 codex 启动环境)。

## 修复的 bug (本 round)

1. **codex.py tool_calls null crash**: ms_gw 返回 `delta.tool_calls: null` (显式 null, 非 missing key)。
   `delta.get("tool_calls", [])` 返回 None (key 存在时 default 不触发), `for tc in None` 崩。
   修: `for tc in tool_calls:` (tool_calls 用 `or` 链) + `for tc in (delta.get("tool_calls") or []):`。
2. **PRIMARY_URL 测试残留 59999**: 上一轮测试用 127.0.0.1:59999, 残留进 compose。
   多次 sed/python replace 报成功但实际未写盘 (疑似 NFS/缓存), 最终 `sed -i` 强制改 + force-recreate。
3. **PRIMARY_STREAM_TIMEOUT_S 新增**: nv_gw 流式 glm5_2_nv 在 HM2 有挂死现象 (R696/R705 已知:
   HM2 出口打 NVCF 流式不稳), cx4102 用 FALLBACK_TIMEOUT_S=300 等太长。
   新增 PRIMARY_STREAM_TIMEOUT_S=60, primary 流式 60s 没拿到响应头就切 fallback。

## 验收数据

### curl 直测 (cx4102 /v1/responses)

| 测试 | 结果 |
|---|---|
| 非流式 stream=false | ✅ HTTP 200, 9s, nv_gw 5xx → fallback ms_gw 成功, reminder 正确嵌入 |
| 流式 stream=true (primary 成功) | ✅ HTTP 200, 10.4s, SSE 事件格式正确 (created→in_progress→output_item.added→content_part.added→output_text.delta→completed) |
| 流式 stream=true (nv_gw 挂死) | ✅ 60s 超时 → 切 fallback (PRIMARY_STREAM_TIMEOUT_S 生效) |

### codex CLI 真实对话

```
$ codex exec --skip-git-repo-check "say hi in 3 words"
codex: The user wants me to say hi in 3 words. Simple request. Hi right back!
tokens used: 4,490
```

✅ 完整链路: codex → cx4102 (Responses→ChatCompletions) → nv_gw/glm5_2_nv → NVCF, 4490 tokens 真实计费。

## 已知遗留 (非 cx4102 问题, 后端平台侧)

- **nv_gw 流式 glm5_2_nv 在 HM2 不稳** (R696/R705 已知): HM2 出口打 NVCF 流式挂/超时。
  cx4102 用 PRIMARY_STREAM_TIMEOUT_S=60 兜底, 60s 没首字节就切 ms_gw。
- **ms_gw 流式 stream_no_data_lines**: ms_gw 流式有时空响应, ms_gw 内部 MS-FASTBREAK 兜底。
  这是 ms_gw 自身问题, 不在本 round 范围 (模块化铁律: 不改 ms_gw)。

## 后续 (pending, 等用户拍板)

- [ ] 删 nv_gw FALLBACK_GRAPH (跨模型 fallback, A 类, 因 41xx 已做 fallback) — 保留 func_health/PEER-FB/key cooldown (B 类)
- [ ] 建 opclaw4103 (openclaw: glm5_2_nv→glm5_2_ms)
- [ ] 建 hm4104 (hermes: dsv4p_nv→dsv4p_ms)
- [ ] 建 oc4105 (opencode: kimi_nv, 无 fallback)
- [ ] 改 3 agent config 指向新 41xx 适配器
- [ ] HM1 同步 (待 HM2 观察窗口跑稳 + 用户拍板)

## 验证清单

- [x] cx4102 容器 Running, /health 200
- [x] cx4102 PRIMARY_URL=http://nv_gw:40006/v1 (非 59999)
- [x] cx4102 PRIMARY_STREAM_TIMEOUT_S=60 生效
- [x] curl /v1/responses 非流式 200 (fallback 触发, reminder 嵌入)
- [x] curl /v1/responses 流式 200 (SSE 格式正确)
- [x] codex CLI codex exec 真实对话成功 (4490 tokens)
- [x] codex.py tool_calls null bug 修复 (container 内 line 202/312)
- [x] HM1 全程未动
- [x] nv_gw/ms_gw 代码未改 (模块化铁律)
