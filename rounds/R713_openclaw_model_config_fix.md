# R713 — OpenClaw 模型配置系统性修复

**时间**: 2026-08-03 19:25 CST
**类型**: 配置修复 (非 nv_gw/dsv4p_nv40066 容器改动)
**触发**: 用户报告 OpenClaw 报错 "Exec failed: show ~/.openclaw/config/models.json"

## 问题定位

### 1. "Exec failed: show ~/.openclaw/config/models.json"
- **根因**: OpenClaw agent (小二) 在 trajectory 中用 exec 工具尝试运行 "show ~/.openclaw/config/models.json"
  - "show" 不是有效 shell 命令 (应为 cat)
  - 路径 `~/.openclaw/config/` 不存在 (实际 models.json 在 `~/.openclaw/agents/main/agent/models.json`)
- **性质**: agent LLM 行为错误, 非系统 bug, 但影响 agent 获取模型配置信息

### 2. models.json 配置错误
- `dsv4p_nv` 的 name 错误: 写的是 "GLM 5.2 (NVCF ai-glm-5_2 3b9748d8...)" 
  - 实际是 DeepSeek V4 Pro (NVCF deepseek-ai/deepseek-v4-pro, fid=12acbc62)
  - 请求返回 `model: deepseek-ai/deepseek-v4-pro`, `reasoning_content` 字段
- `dsv4p_nv` 的 `thinkingFormat: "zai"` 错误
  - "zai" 是 GLM 5.2 的 thinkingFormat, DeepSeek 用标准 `reasoning_content` 字段
- 缺少 `glm5_2_nv` model 定义 (opclaw4103 adapter FALLBACK_MODEL=glm5_2_nv)

### 3. ENOENT double workspace path
- 日志: `ENOENT: no such file or directory, access '/home/opc2_uname/.openclaw/workspace/workspace/openclaw2_improve_self/openclaw.md'`
- **根因**: workspace/MEMORY.md 项目路径表用 "workspace/openclaw2_improve_self/" 前缀
  - agent read 工具传 path="workspace/openclaw2_improve_self/openclaw.md"
  - openclaw 拼接 workspaceDir(/home/opc2_uname/.openclaw/workspace) + path → double workspace

## 修复内容

### Fix 1: models.json (agent 级 + 全局)
**文件**: `~/.openclaw/agents/main/agent/models.json` + `~/.openclaw/openclaw.json`

- `dsv4p_nv` name 修正为: "DeepSeek V4 Pro (NVCF deepseek-ai/deepseek-v4-pro 12acbc62, reasoning_content)"
- `dsv4p_nv` 移除 `thinkingFormat: "zai"` (DeepSeek 用标准 reasoning_content, 不需要特殊 format)
- 新增 `glm5_2_nv` model 定义 (fallback model, 保留 thinkingFormat: "zai")
- `openclaw.json` alias 更新: "opclaw4103/glm5_2_nv" → "GLM 5.2 (via opclaw4103 adapter, fallback model when dsv4p_nv fails)"

### Fix 2: 创建 config symlink
- `mkdir -p ~/.openclaw/config && ln -sf .../agents/main/agent/models.json ~/.openclaw/config/models.json`
- 让 agent 即使尝试 `~/.openclaw/config/models.json` 也能读到正确配置

### Fix 3: MEMORY.md 路径前缀修复
- 去掉项目路径表中的 "workspace/" 前缀 (5 处)
- 去掉编排架构文档路径的 "workspace/" 前缀 (1 处)

## 验证

1. `systemctl --user restart openclaw-gateway` → 重启成功
2. `curl http://127.0.0.1:18789/health` → `{"ok":true,"status":"live"}`
3. 日志确认: `"agent model: opclaw4103/dsv4p_nv (thinking=medium, fast=off)"`
4. 日志确认: 配置热重载成功 (`config hot reload applied (models.providers.opclaw4103.models)`)
5. 日志确认: feishu WebSocket 连接成功
6. 重启后无 ENOENT 或 Exec failed 错误

## 链路状态

```
OpenClaw (小二) → opclaw4103 (cc-adapter)
  ├─ PRIMARY: dsv4p_nv40066:40066/v1, model=dsv4p_nv (DeepSeek V4 Pro)
  └─ FALLBACK: nv_gw:40006/v1, model=glm5_2_nv (GLM 5.2) [FALLBACK_ENABLED=1]
```

## 备份

- `~/.openclaw/agents/main/agent/models.json.bak.R707`
- `~/.openclaw/openclaw.json.bak.R707`
- `~/.openclaw/workspace/MEMORY.md.bak.R707`
