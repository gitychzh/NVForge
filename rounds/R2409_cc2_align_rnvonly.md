# R2409: cc2 自优化方向对齐 R-nvonly

**日期**: 2026-07-28
**主机**: HM2 (cc2 自优化系统)
**作者**: CC 基础设施侧

## 改动摘要

将 cc2 自优化 agent 的优化方向从"降低 fallback 率"对齐到 R-nvonly 方向:
"让 nv_gw 纯靠 5key+5IP 自恢复到 99%+ SR, 无需 ms_gw fallback"。

### 修改的文件 (均在 HM2 cc2 工作目录, 非 nv_gw 源码)

1. **`~/cc_ps/cc2_repair_self/CLAUDE.md`** — 完全重写
   - 旧: ms_gw 是"重启窗口热备", 优化目标是"降低 fallback 率"
   - 新: ms_gw fallback 已禁用, 优化目标是"nv_gw 纯靠 5key+5IP 自恢复"
   - 新增 R-nvonly 当前架构说明 (KeyManager/ProbeWorker/WaitQueue/BufferStreamSession)
   - 新增 deadline 链对齐说明 (90s×4=380s buffer < 400s cc4101 < 850s SDK)
   - 新增 5 个关键验证点 (RemoteDisconnected/Buffer轮转/WaitQueue/deadline链/SR)
   - 保留数据源命令, 增加 buffer/deadline 查询
   - 铁律更新: "不碰 40007" → "ms_gw 已禁用, 不要重新启用"

2. **`~/cc_ps/cc2_repair_self/.claude/cc2_resume.sh`** — prompt 重写
   - 新 prompt 强调 R-nvonly 方向: 纯 glm5_2_nv, 无 ms fallback, 5key+5IP 自恢复
   - 新增关键验证点清单 (RemoteDisconnected 快速恢复 / Buffer 4key 轮转 / WaitQueue / deadline 链)
   - 删除旧 R2192 三任务引用 (已被 R-buffer 部分取代, 不再是 cc2 的活跃任务)
   - 保留 R2082 no-output 看门狗检测 + R-guard 悬空 .py 守卫
   - 修复 claude 二进制路径问题 (Bun native binary 需 AVX2, HM2 CPU 不支持 → 改用 Node.js wrapper)

3. **`~/cc_ps/cc2_repair_self/.claude/settings.json`** — 无实质变化
   - 确认 `CLAUDE_STREAM_IDLE_TIMEOUT_MS=850000` (对齐 cc4101 400s + buffer 380s + 余量)
   - 确认 `API_TIMEOUT_MS=850000`
   - 备份 `.bak.R-nvonly`

### 修复: claude binary 路径

HM2 的 claude npm 包 (v2.1.220) 在升级后 native binary (Bun) 需要 AVX2 指令集,
但 HM2 CPU 是 Intel i3-2328M (Sandy Bridge, 无 AVX2) → Bus error core dump。
所有 cc2 轮次自升级后全部空转 (timeout: failed to run command)。

修复: 将 `~/.npm-global/bin/claude` 符号链接从 native binary 改为 `cli-wrapper.cjs` (Node.js fallback)。
`node cli-wrapper.cjs --version` 返回 `2.1.186` (wrapper 版本号不同但功能正常)。

## 数据 (改前)

cc2 自上次 claude npm 包升级后 (约 2026-07-28 00:34) 全部轮次失败:
- cc2.log 最后 ~20 行全是 `timeout: failed to run command 'claude': No such file or directory`
- 0 轮成功执行, STATE.md 停在 R-buffer-post6 (08:55 CST 07-27)
- nv_gw/cc4101 R-nvonly 配置持续生效 (由 CC 基础设施侧 R2408 部署)

## 预期效果

1. cc2 恢复正常自优化节律 (每 ~1min 一轮)
2. cc2 自优化方向对齐 R-nvonly: 监控 SR/RemoteDisconnected 恢复/buffer 效果/deadline 链
3. cc2 不再尝试重新启用 ms_gw fallback
4. cc2 数据查询从"fallback 率"转向"nv_gw 自恢复 SR"

## 验证清单

- [x] claude binary 修复 (wrapper --version OK)
- [x] cc2-resume.timer active
- [x] cc2 轮开始标记 `=== cc2 新 session 轮开始 (R-nvonly) ===` 出现在日志
- [ ] 第一轮成功完成 (STATE.md 更新)
- [ ] cc2 拉数据确认 nv_gw SR

## 回滚

- CLAUDE.md: `cp ~/cc_ps/cc2_repair_self/CLAUDE.md.bak.R-nvonly ~/cc_ps/cc2_repair_self/CLAUDE.md`
- cc2_resume.sh: `cp ~/cc_ps/cc2_repair_self/.claude/cc2_resume.sh.bak.R-nvonly ~/cc_ps/cc2_repair_self/.claude/cc2_resume.sh`
- settings.json: `cp ~/cc_ps/cc2_repair_self/.claude/settings.json.bak.R-nvonly ~/cc_ps/cc2_repair_self/.claude/settings.json`
- claude binary: `ln -sf ../lib/node_modules/@anthropic-ai/claude-code/bin/claude.exe ~/.npm-global/bin/claude` (需 AVX2 CPU)
