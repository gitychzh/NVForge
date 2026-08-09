---
name: cc-auto-update-enotempty-crash
description: "2026-07-14 CC 崩溃根因——npm自动更新reify时ENOTEMPTY致claude二进制悬空, webui拉不起claude"
metadata: 
  node_type: memory
  type: project
  originSessionId: 3c8d8f5f-50f9-4f31-9c0c-b1eae74a0183
---

2026-07-14 13:25 本地时间 CC "崩溃"真根因：Claude Code 自动更新器检测到 2.1.208（上一次成功更新 7-11 2.1.201→2.1.207），触发 npm reify：先把旧 `@anthropic-ai/claude-code` 目录 rename 成 `.claude-code-XXXX`(retire) 再装新版。rename 因目录非空失败（`ENOTEMPTY`），旧二进制被 retire 掉、新的没装上 → `~/.npm-global/bin/claude` 软链悬空 → cc_webui(node[819]) 经 claude-agent-sdk spawn claude 时抛 `ReferenceError: Claude Code native binary not found`。

**证据**：`.claude/.update.lock` 残留 PID 790327(已死)；npm 日志 `06_15_31_513Z-debug-0.log` uninstall 时复现同 ENOTEMPTY；mihomo 13:16-13:17 大量 registry.npmjs.org 连接=自更新下载；journal 13:25:06 SDK not found 报错；8 分钟日志空白(13:17→13:25)=reify 卡住。

**手动恢复**：npm cache clean --force → npm uninstall 报 ENOTEMPTY → `sudo rm -rf claude-code .claude-code-WiJlQpuj bin/claude bin/.claude-t5MI550R` → `npm install -g @anthropic-ai/claude-code@2.1.208` exit 0。

**Why**: installMethod=global + 未设 autoUpdates:false，npm-global 装法在有残留/并发更新时易 ENOTEMPTY，更新中断即二进制悬空，外部表现为"CC 崩溃"。
**How to apply**: 防复发①删 stale `.update.lock`(PID死)②settings.json 加 `"autoUpdates": false` 或 `DISABLE_AUTOUPDATER=1`③手动更新前先 `sudo rm -rf` 残留 retired `.claude-code-*` 目录再 install。88f513be 主 jsonl 丢失(仅剩 subagents)，相关审计结论见 [[r845-cc4101-stall-watcher-b2-b5-fix]] [[cc4101-b1-b2-audit-correction]]。
