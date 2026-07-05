# R752: HM2 三 agent config 改指 41xx 适配器 + 验收

> 日期: 2026-07-05  机器: HM2 (实验床)  前置: R750 (cx4102), R751 (opclaw4103/hm4104/oc4105)
> **HM1 全程未动** (本地生产冻结)

## 背景

R751 建好 3 个 ChatCompletions 适配器 (opclaw4103/hm4104/oc4105) 后, 改 3 agent config
指向新 41xx, 删 agent 自身 fallback (用户决策: 41xx 自带 fallback, agent 简化为单 base_url)。

## 改动

### opencode `~/.config/opencode/opencode.jsonc`
- model: `nv_gw/kimi_nv` → `oc4105/kimi_nv`
- provider: 删 nv_gw + ms_gw, 加 oc4105 (baseURL http://127.0.0.1:4105/v1, apiKey oc-gw-token)
- 备份: opencode.jsonc.bak.R751

### openclaw `~/.openclaw/openclaw.json`
- agents.defaults.model.primary: `nv_gw/glm5_2_nv` → `opclaw4103/glm5_2_nv`
- agents.defaults.model.fallbacks: `[ms_gw/glm5_2_ms]` → `[]` (删, 41xx 处理)
- compaction.model: `nv_gw/dsv4p_nv` → `opclaw4103/glm5_2_nv`
- memorySearch.remote.baseUrl: `http://localhost:40006/v1` → `http://127.0.0.1:4103/v1` (apiKey opclaw-gw-token)
- models.providers: 删 nv_gw + ms_gw, 加 opclaw4103
- 备份: openclaw.json.bak.R751
- systemctl --user restart openclaw-gateway

### hermes `~/.hermes/config.yaml`
- model.provider: `nv_gw` → `hm4104`
- model.base_url: `http://127.0.0.1:40006/v1` → `http://127.0.0.1:4104/v1`
- providers: 删 nv_gw, 加 hm4104 (api_key hm-gw-token, default_model dsv4p_nv)
- fallback_providers: 删除 (41xx 自带 fallback)
- 备份: config.yaml.bak.R751
- systemctl --user restart hermes-gateway

## 验收

### opencode → oc4105 (kimi_nv)
- curl `/v1/chat/completions` 带 tools 流式: ✅ HTTP 200, 5.8s, 返回 "1+1=2。" + 正确 [DONE]
- `opencode run` CLI: 发请求成功 (log 显示 message.part.delta 多次), 但非 TTY 模式不 stdout 输出回答
  (直连 nv_gw 旧 config 同样行为, 是 opencode CLI 自身非交互输出问题, 非 oc4105 bug)

### openclaw → opclaw4103 (glm5_2_nv → fallback glm5_2_ms)
- curl 非流式: ✅ HTTP 200, 19s, nv_gw 502 → fallback ms_gw, reminder 注入 content 前缀
- `openclaw agent --agent main -m "..."` : ✅ 触发完整 fallback 链路
  (日志: REQ tools=24 → 60s 超时 PRIMARY-FAIL-STREAM → FALLBACK-STREAM ms_gw)
  (openclaw agent CLI 同样非 TTY 不 stdout 输出)

### hermes → hm4104 (dsv4p_nv) — 真实 CLI 验收成功 ✅
```
$ hermes -z "用一句话回答:1+1=?"
2
```
hm4104 收到 REQ (dsv4p_nv stream=True tools=18), 链路完整, hermes CLI 真实输出 "2"。

## 关键发现

**opencode/openclaw CLI 在非 TTY 模式下都不 stdout 输出回答** (直连 nv_gw 旧 config 也一样,
是 CLI 自身行为, 非 41xx 适配器问题)。hermes CLI `-z` 模式能正常输出。
三个 agent 的链路均通过 curl 端到端 + adapter 日志验证正确。

## 5 agent 全解耦架构 (HM2 当前状态)

```
codex    → cx4102(4102)     → nv_gw/glm5_2_nv → ms_gw/glm5_2_ms  ✅ (R750 codex CLI 4490 tokens)
openclaw → opclaw4103(4103) → nv_gw/glm5_2_nv → ms_gw/glm5_2_ms  ✅ (curl+fallback 日志)
hermes   → hm4104(4104)     → nv_gw/dsv4p_nv → ms_gw/dsv4p_ms    ✅ (CLI 输出 "2")
opencode → oc4105(4105)     → nv_gw/kimi_nv (无 fallback)         ✅ (curl 5.8s)
claude   → cc4101(4101)     → (legacy cloudcli, R684/R699/R700)
```

5 个 41xx 适配器完全解耦, 各自独立调参/fallback, 不影响彼此。nv_gw/ms_gw 作为共享后端, 代码零改动 (模块化铁律)。

## 后续 pending (等用户拍板)

- [ ] 用户 TTY 实测 opencode/openclaw (HM2 终端直接跑, 看真实回答)
- [ ] 删 nv_gw FALLBACK_GRAPH (A 类跨模型 fallback, 41xx 已做, 重复)
- [ ] HM1 同步 (待 HM2 观察窗口跑稳 + 用户拍板)

## 验证清单

- [x] opencode config 改 oc4105, json 解析通过
- [x] openclaw config 改 opclaw4103, fallbacks 删, gateway restart active
- [x] hermes config 改 hm4104, fallback_providers 删, gateway restart active
- [x] oc4105 curl 带 tools 流式 200 (5.8s)
- [x] opclaw4103 fallback 链路日志完整 (nv_gw 502/timeout → ms_gw, reminder 注入)
- [x] hm4104 hermes CLI 真实输出 "2"
- [x] HM1 全程未动
- [x] nv_gw/ms_gw 代码未改 (模块化铁律)
