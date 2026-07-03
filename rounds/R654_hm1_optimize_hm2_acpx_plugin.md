# R654 HM1→HM2: openclaw acpx 插件清理 + 状态收敛

## 背景
用户报 openclaw agent 报警 `{ 确认 OpenClaw acpx 对 hermes 的支持情况 grep ... failed }`.
排查发现是 7-3 16:05 历史 session 里 agent (glm5_2_nv) 执行 hermes-acp 依赖排查时的
一次性工具调用失败记录, 非当前持续故障. 但暴露 acpx 插件状态长期不一致:
- doctor 报 "plugins.entries.acpx: plugin not installed" (启动时序)
- plugins list 又显示 enabled
- npm 安装路径有冲突 (短路径 + --force 产生的长路径两份)

## 改动 (HM2)
1. `openclaw plugins uninstall acpx --force` — 清掉注册 + 长路径目录 + allowlist entry.
2. `rm -rf ~/.openclaw/npm/projects/openclaw-acpx-052d680d6d` — 清残留短路径目录.
3. `openclaw plugins install @openclaw/acpx` — 干净重装到正规短路径.
4. `openclaw config set plugins.allow --strict-json '["feishu","memory-core","acpx"]'`
   — 把 acpx 加回 allowlist (uninstall 时被删, 导致 enable blocked).
5. `openclaw plugins enable acpx` + 重启 + `openclaw doctor --fix`.

## 改后验证
- `Plugins Loaded: 3` (feishu + memory-core + acpx), `Errors: 0`. ✅
- journal: `[gateway] http server listening (3 plugins: acpx, feishu, memory-core)`,
  `[plugins] embedded acpx runtime backend registered lazily`. ✅
- doctor 无 "acpx not installed" / "acpx: missing", `Missing requirements: 0`. ✅
- 重启后无 runtime error. ✅

## 关于那条 "failed" 报警
是 openclaw main agent 在 session f9c6dee0 (7-3 14:37~16:05) 跟 "Boss张" 对话排查
"Hermes 的 ACP 依赖" 时执行的工具调用. 命令 `# 确认 OpenClaw acpx 对 hermes 的支持情况
\ngrep -ri "hermes" .../acp-agents.md` 本身合法 (注释+grep, exit=0 可跑通), "failed"
标记源于当时 acpx 插件状态不一致 + hermes-acp --check 失败. 陈旧记录, 非当前故障,
无需再修. 当前 acpx 已干净加载.

## 铁律
- 聚焦 nv_40006_uni? 本次非链路改动, 是 openclaw 插件层维护, 不碰 hm40006. ✅
- 改前有数据: session transcript 定位报警来源 + doctor/plugins list 交叉验证状态. ✅
- 改后有验证: journal + doctor + plugins list. ✅
- 写入仓库: 本文件. ✅

## 回滚
- 不需要回滚 (状态已收敛到正常).
- 若 acpx 再出问题: `openclaw plugins uninstall acpx --force` 重装, 或 config 里
  `plugins.entries.acpx.enabled=false` 临时禁用 (不影响 openclaw 主功能, acpx 只是
  ACP 外部 agent 调度扩展, hermes 在本环境是独立 agent 不走 acp 接入).
