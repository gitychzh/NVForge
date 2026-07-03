# R580: ms_uni40007 自建 MS 代理 + 三 agent 接入 fallback + 思考强度可选性分析

**日期:** 2026-07-03
**方向:** CC 直接改 HM2 (R569 起交替优化全停, CC 直接改两机静态运维)
**铁律遵守:** 改前有数据 / 改后有验证 / 聚焦 hm-40006--nv (现 nv_40006_uni) / 写入仓库; HM1 全程未改

## 本轮三件事

### 1. ms_uni40007 自建 MS ModelScope 代理 (HM2, 端口 0.0.0.0:40007)

OpenAI passthrough (无 Anthropic 转换), 7 MS key × 10 variant 2D 轮转, 白名单错误检测 (MS 返回 HTTP 200 + `{"choices":null}` 畸形壳, 非 429), 流式首块预检, n+1 计数 (cycle 不触计数), bind-mount 源码改 .py 只 restart。

- 路径: `/opt/cc-infra/proxy/ms-uni/gateway/` (config.py/upstream.py/handlers.py/rr_counter.py/cooldown.py/logger.py/error_mapping.py)
- docker-compose service `ms_uni40007`: port 40007, env MS_KEY1..7 (=41001 同值), NUM_KEYS=7, NUM_VARIANTS=10, bind-mount gateway+logs, healthcheck, network cc-net
- 2D 轮转: `variant_idx=(N//NUM_KEYS)%NUM_VARIANTS, key_idx=N%NUM_KEYS`
- 白名单: error body / choices null / content empty+reasoning_content fallback / tool_calls
- _sanitize_request_body strip NVCF 风格 (chat_template_kwargs/thinking/thinking_effort), 保留 MS 原生 reasoning_effort+thinking_budget
- 部署后 curl /health /v1/models /v1/chat/completions 全通, 计数前进, 2D 轮转, empty-200 cycle 切换均验证

### 2. 三 agent 模型配置清理 + 接入 fallback

| agent | default | fallback | 备注 |
|---|---|---|---|
| openclaw | `nv_cus/glm5_2_nv` | `["ms_cus/glm5_2_ms"]` | agents.defaults.model.fallbacks 数组(跨provider); ms_cus provider @40007; compaction.model=dsv4p_nv 不动; thinkingDefault=xhigh |
| hermes | `dsv4p_nv` (从kimi_nv改) | `glm5_2_ms` (custom provider @40007) | fallback_providers[{provider:custom,api_mode:chat_completions}]; `hermes fallback list` 验证 |
| opencode | `nv_cus/kimi_nv` (从glm5_1_nv改,EOL) | **无** (用户决定:NV挂=直错) | ms_cus provider 加但仅手动切; $schema首行保留(OpenCode Zen自动加载); webui 4096 不碰 |

backup 均 `.bak.ms_fallback_20260703_180745`。

**端到端验证:**
- openclaw→ms_cus/glm5_2_ms: ms_metrics caller=openclaw 2次成功(1次6cycles)
- hermes fallback: `HERMES_HOME=/tmp/...` 覆盖 + primary 指死端口 39999 → 输出 "fallback ok", ms_uni40007 18:33 收 req=56312796 (caller=unknown, hermes custom provider 不发 X-Caller)
- opencode webui 4096: HTTP 200 不受影响

**坑:**
- hermes **无 `-c <file>` 全局 flag** (误用致静默加载内置 config 无输出)。配置覆盖正确方式: `HERMES_HOME=<tmpdir> hermes -z`; `--ignore-user-config` 与 HERMES_HOME 覆盖冲突
- opencode jsonc 注释剥离: `(?m)^\s*//.*$` 全行 + `(\s)//[^\"\n]*$` 行尾 (naive `//.*` 误匹配 URL `//`)

### 3. 三 agent 思考强度 agent 侧可选性分析

| agent | agent 侧可选? | 机制 |
|---|---|---|
| openclaw | ✅ 最完整 | thinkingDefault=xhigh 全局 + 每模型 compat.supportedReasoningEfforts 白名单 + `openclaw infer model run --thinking <level>` 每调覆盖 |
| opencode | ✅ (config, 无 CLI flag) | `providers.{name}.models.{id}.reasoning.effort` 或顶层 `reasoningEffort` → openai-compatible provider 放进 body `reasoning_effort`; ms_uni40007 白名单保留 → 直达 MS glm5.2 |
| hermes | ❌ 对 NV/MS 链路不可选 | 有 `agent.reasoning_effort` config + `/reasoning <level>` 命令, 但 `agent/transports/chat_completions.py:426` generic 分支(非 kimi/tokenhub/lmstudio/github/gemini) 硬编码 `extra_body.reasoning={enabled:True,effort:"medium"}`, 不读 config effort → 我们 litellm-nv-hm/custom provider 走此分支, config 设 xhigh 被丢恒发 medium |

**NV 链路真生效处:** nv_40006_uni config.py NVCF_PEXEC_MODELS spec 的 `inject` 字段 (抓包实测每 function 触发参数不同):
- kimi_nv: inject reasoning_effort=low (reasoning_effort 真触发)
- dsv4p_nv: inject thinking={type:enabled} (74f02205); reasoning_effort 仅 sglang 8915fd28
- glm5_2_nv/glm5_1_nv: strip reasoning_effort/thinking, inject chat_template_kwargs.enable_thinking (reasoning_effort 无效)

即 agent 侧设思考强度对 NV 链路基本不改变行为 (网关 inject 固定), 仅 opencode→ms_uni40007 链路 reasoning_effort 真透传到 MS。要让 hermes 真支持需改源码 chat_completions.py:426 读 reasoning_config.effort。

## 下轮

可继续: 监控三 agent 接入 ms fallback 后实际流量下 NV→MS fallback 触发率与 MS 成功率; 或修 hermes chat_completions.py:426 让 reasoning_effort 对 custom provider 生效 (源码改动, 非配置)。
