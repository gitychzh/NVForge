# R1261: HM2 适配器容器暴露 0.0.0.0 + openclaw/hermes 切远程 adapter

## 时间
2026-08-14 22:00~22:40 CST

## 变更摘要

### 1. HM2 docker-compose 端口暴露 (hm4104 + oc4105)
- `hm4104`: `127.0.0.1:4104:4104` → `0.0.0.0:4104:4104`
- `oc4105`: `127.0.0.1:4105:4105` → `0.0.0.0:4105:4105`
- `cc4101` 和 `opclaw4103` 已经是 `0.0.0.0`, 无需改动
- 备份: `docker-compose.yml.bak.R1261`
- 重启: `docker compose up -d hm4104 oc4105`

### 2. openclaw 切到远程 opclaw4103
- `~/.openclaw/openclaw.json` 修改:
  - `agents.defaults.model.primary`: `oc_zen/big-pickle` → `nv_cus/glm5_2_nv`
  - `agents.defaults.model.fallbacks`: `[oc_zen/big-pickle, nv_gw/glm5_2_nv, ms_gw/glm5_2_ms]`
  - `nv_cus` provider 已指向 `http://100.109.57.26:4103/v1` + `opclaw-gw-token` (之前已配好)
- 备份: `openclaw.json.bak.R1261`
- 重启: `kill -USR1` → full process restart, PID 1428960 → 1487583
- 验证: 日志 `agent model: nv_cus/glm5_2_nv (thinking=xhigh, fast=off)`

### 3. hermes 切到远程 hm4104
- `~/.hermes/config.yaml` 修改:
  - `model.base_url`: `http://127.0.0.1:40006/v1` → `http://100.109.57.26:4104/v1`
  - `model.default`: `dsv4p_nv` → `dsv4f0731_nv`
  - `providers.nv_gw.api_key`: `nv-gw-token` → `hm-gw-token`
  - `providers.nv_gw.base_url`: `http://127.0.0.1:40006/v1` → `http://100.109.57.26:4104/v1`
  - `providers.nv_gw.default_model`: `dsv4p_nv` → `dsv4f0731_nv`
  - 新增 `dsv4f0731_nv` model 定义 (supports_thinking=true, max_tokens=32768)
  - `providers.nv_gw.name`: `NV HM Proxy (40006)` → `HM2 hm4104 adapter (100.109.57.26:4104)`
  - fallback_providers 保持本地 ms_gw (127.0.0.1:40007) 作为二级兜底
- 备份: `config.yaml.bak.R1261`
- 重启: `hermes gateway restart`, PID 920 → 1490298
- 验证: gateway 日志显示 feishu 重新连接成功

### 4. CC (已切远程, 无需改动)
- `~/.claude/settings.json` 已指向 `http://100.109.57.26:4101` (R1258)
- 模型: `cc-glm5-2`, token: `cc4101-token`

### 5. opencode (保持现状, 不改动)

## 参数表

| 组件 | 端口 | 绑定 | Primary | Fallback |
|---|---|---|---|---|
| cc4101 | 4101 | 0.0.0.0 | glm5_2_nv@nv_gw:40006 | dsv4f0731_nv@dsvf0731_nv40666:40666 |
| opclaw4103 | 4103 | 0.0.0.0 | glm5_2_ms@ms_gw:40007 | glm5_2_nv@nv_gw:40006 |
| hm4104 | 4104 | 0.0.0.0 | dsv4f0731_nv@dsvf0731_nv40666:40666 | dsv4f0731_ms@ms_gw:40007 |
| oc4105 | 4105 | 0.0.0.0 | dsv4f0731_nv@dsvf0731_nv40666:40666 | dsv4f0731_ms@ms_gw:40007 |

## 端到端验证

### cc4101 (anthropic /v1/messages)
```
curl http://100.109.57.26:4101/v1/messages -H "x-api-key: cc4101-token" ...
→ ✅ 200 OK, content="Hello."
```

### opclaw4103 (openai /v1/chat/completions)
```
curl http://100.109.57.26:4103/v1/chat/completions -H "Authorization: Bearer opclaw-gw-token" ...
→ ✅ 200 OK, content="Hello", model=glm5_2_ms
→ ✅ streaming OK
```

### hm4104 (openai /v1/chat/completions)
```
curl http://100.109.57.26:4104/v1/chat/completions -H "Authorization: Bearer hm-gw-token" ...
→ ✅ 200 OK, content="你好！很高兴能用中文为你服务。", model=deepseek-ai/deepseek-v4-flash-0731
→ ✅ streaming OK
```

### oc4105
```
curl http://100.109.57.26:4105/health → ✅ ok
```

### HM2 容器状态
```
hm4104     0.0.0.0:4104->4104/tcp   Up 35 minutes
oc4105     0.0.0.0:4105->4105/tcp   Up 35 minutes
opclaw4103 0.0.0.0:4103->4103/tcp   Up 26 hours
cc4101     0.0.0.0:4101->4101/tcp   Up 34 hours
```

### Agent 进程状态
- openclaw: PID 1487583, node, gateway port 18789, model=nv_cus/glm5_2_nv
- hermes: PID 1490298, python, systemd hermes-gateway.service active
- CC: running through 100.109.57.26:4101 (R1258)
