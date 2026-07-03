# R581: kimi_nv 思考强度 low→medium + openclaw 飞书插件缺失修复

**日期:** 2026-07-03
**方向:** CC 直接改 HM2 (R569 起交替优化全停)
**铁律遵守:** 改前有数据 / 改后有验证 / 聚焦 nv_40006_uni + openclaw / 写入仓库; HM1 全程未改

## 1. kimi_nv 思考强度落地 medium

用户决策: 三 agent 都默认中等强度思考即可, 保持开启, 不需要 agent 侧选强度, 在容器代码里写死。

**落地分析 (NVCF 抓包实测, 每 function 触发参数不同):**
- dsv4p_nv (74f02205): `thinking:{type:enabled}` 触发, **无档位** (NVCF 不接受 low/medium/high, reasoning_effort 对 74f02205 返回 200 但 rc 恒空无效) — 保持 inject 开思考, 无"中等"可设
- glm5_2_nv (3b9748d8): `chat_template_kwargs:{enable_thinking:true}` 触发, **无档位** (reasoning_effort 无效, strip 掉) — 保持 inject 开思考
- kimi_nv (f966661c): `reasoning_effort` 触发, **支持 low/medium/high** — 唯一能设档位的

**改动:** `/opt/cc-infra/proxy/nv-uni/gateway/config.py` line 85:
```python
"kimi_nv": {
    "inject": {"reasoning_effort": "medium"},  # was "low"
}
```
backup: `config.py.bak.R580_kimi_medium`。bind-mount 改 .py 只 restart: `docker compose restart nv_40006_uni` → /health ok。

**未动:** dsv4p_nv/glm5_2_nv 的 inject (NVCF 不支持档位, 开思考已是唯一正确做法); agent 侧 (openclaw/opencode 的 reasoning 配置保留手动选强度功能; hermes 不支持我们的链路但 NV 思考由网关 inject 兜底, 不影响)。

**hermes 思考机制澄清 (非本轮改动, 仅分析):** hermes `_supports_reasoning_extra_body()` (run_agent.py:5251) 是白名单制, 只对 nousresearch/github/lmstudio/openrouter 白名单内 provider 返回 True, 我们的 litellm-nv-hm/custom provider 不在白名单 → supports_reasoning=False → chat_completions.py:426 generic 分支不进 → hermes 不发任何思考参数。NV 链路思考由 nv_40006_uni inject 强制开, hermes 发不发结果一样; MS 链路 glm5.2 默认带思考。故 hermes 缺思考强度选择能力不影响功能。

## 2. openclaw 飞书不回消息修复

**症状:** openclaw control UI (18789) 正常对话, 飞书不回任何消息。

**根因:** `openclaw.json` 里 `plugins.entries.feishu.enabled=true`, 但官方飞书 channel 插件 `@openclaw/feishu` **未装**。journal 反复告警:
```
plugins.entries.feishu: plugin not installed: feishu — install with: openclaw plugins install @openclaw/feishu
```
没装 → gateway 不注册飞书 channel → 收不到飞书事件。control UI 能用是走内部 webchat ws, 不经 feishu channel。

**易混:** 之前装过 `@larksuite/openclaw-lark` (6月11日), 但那是技能/命令扩展包 (doctor/diagnose/auth + feishu-* skills), package.json 无 `openclaw.channel` 字段, **不是 channel 插件**。channel 路由必须装 `@openclaw/feishu` (manifest `openclaw.channel.id="feishu"`)。

**修复:**
```bash
openclaw plugins install @openclaw/feishu   # 自动选兼容版 2026.6.8 (runtime 2026.6.8; 最新 2026.6.11 要 pluginApi>=2026.6.11 不兼容, 自动降级, 无需升级 openclaw)
systemctl --user restart openclaw-gateway
```
重启后验证 (journal):
```
[gateway] http server listening (2 plugins: feishu, memory-core)
[feishu] starting feishu[default] (mode: websocket)
[feishu] bot open_id resolved: ou_e750e1f31f133cbf8294c7a59cd2c09a
[feishu] WebSocket client started
[ws] ws client ready
```
飞书用 **websocket 长连接模式** (非 webhook 回调), 不需公网入口/tailscale funnel, openclaw 主动连飞书服务器。`curl /api/channels/feishu/events` 返回 401 是正常 (webhook 模式路由, ws 不用)。

**飞书 channel model:** 不覆盖, 用 agent default = primary `nv_cus/glm5_2_nv` + fallback `ms_cus/glm5_2_ms` (glm5_2_nv 稳, 兜底 glm5_2_ms)。

**端到端:** websocket 连接层全通; 待用户从飞书发消息验证 receive→model→reply 完整链路 (model 侧 glm5_2_nv+glm5_2_ms fallback 已配)。

## 附带观察 (非本轮修)

nv_40006_uni 近5分钟 dsv4p_nv 有 2 个 502 (19:41/19:45), 耗时 74-154s (思考请求长)。这是 NVCF 侧波动, 与飞书无关; openclaw 飞书用 glm5_2_nv (稳) + ms fallback, 不受 dsv4p 波动影响。

## 下轮

可继续: 监控飞书实际消息回复成功率; 或排查 dsv4p_nv 间歇 502 (NVCF surge vs 网关 timeout)。
