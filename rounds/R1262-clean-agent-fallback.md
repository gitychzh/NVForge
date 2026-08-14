# R1262: hermes/openclaw 清除自身 fallback, 交给容器网关处理 + 删除冗余

## 时间
2026-08-14 23:45~23:55 CST

## 背景
hm4104 和 opclaw4103 适配器已内置 primary→fallback 机制. agent 自身的 fallback 层是多余的:
- 22:29 故障中, hermes 等 fallback 40s, openclaw 多 provider 切换增加延迟
- 清除后故障链路只剩 adapter→upstream 两层, 恢复更快

## 变更

### hermes config.yaml
- **删除 `fallback_providers` 整节** (原 line 34-39, 本地 ms_gw fallback → 冗余, hm4104 已有 dsv4f0731_ms fallback)
- **删除 3 个死/EOL 模型定义**: `dsv4p_nv` (EOL 08-07), `kimi_nv` (全死), `minimax_m3_nv` (未用)
- **删除 `streaming: true`** (hermes 报 "unknown config keys ignored: streaming")
- **删除文件末尾 `fallback_model` 注释块** (21行注释, 无实际作用)
- 保留: `dsv4f0731_nv` (primary) + `glm5_2_nv` (adapter fallback label)
- 备份: `config.yaml.bak.R1262`

### openclaw openclaw.json
- **清除 `agents.defaults.model.fallbacks`** → `[]` (原: `[oc_zen/big-pickle, nv_gw/glm5_2_nv, ms_gw/glm5_2_ms]`)
- **删除 3 个不用的 providers**: `nv_gw` (local 40006), `ms_gw` (local 40007), `oc_zen` (local 45001)
- **删除 6 个 stale aliases**: `nv_gw/dsv4p_nv`, `nv_gw/glm5_2_nv`, `nv_gw/kimi_nv`, `nv_gw/minimax_m3_nv`, `ms_gw/glm5_2_ms`, `oc_zen/deepseek-v4-flash-free`
- 保留: 1 个 provider `nv_cus` (100.109.57.26:4103 → opclaw4103), 1 个 alias `nv_cus/dsv4f0731_nv`
- 备份: `openclaw.json.bak.R1262`

### 不动
- hm4104/opclaw4103 适配器自身配置 (容器级 fallback 不归 agent 管)
- hermes 的 model/agent/toolsets 等其他配置
- openclaw 的 gateway/tools/compaction 等配置

## 适配器 fallback 现状 (容器网关负责)
```
hermes → hm4104 (4104)
  primary: dsv4f0731_nv @ dsvf0731_nv40666:40666 (NVCF pexec)
  fallback: dsv4f0731_ms @ ms_gw:40007 (ModelScope)

openclaw → opclaw4103 (4103)
  primary: big-pickle @ oc45001:45001 (opencode zen)
  fallback: glm5_2_nv @ nv_gw:40006 (NVCF pexec)
```

## 验证
- hermes restart: PID 1556554, 无 "unknown config keys" 警告, feishu 连接 OK
- openclaw restart: PID 1557852, `agent model: nv_cus/glm5_2_nv (thinking=xhigh, fast=off)`, 0 fallbacks
- E2E hm4104: ✅ 200 OK "Hello!" (dsv4f0731_nv)
- E2E opclaw4103: ✅ 200 OK, adapter 自行 fallback 到 glm5_2_nv (primary big-pickle 降级, adapter 层正确工作)
