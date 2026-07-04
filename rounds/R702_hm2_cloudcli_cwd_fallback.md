# R702: HM2 cloudcli webui "binary failed to launch" — cwd 不存在 fallback 修复

**Date**: 2026-07-05 03:00 UTC
**Host**: HM2 (opc2_uname @ 100.109.57.26)
**Scope**: cloudcli webui (port 3001) — 不属 nv_gw 优化目标，但 CC 自身依赖 (R699 BUG-7 误删 cc4101 已导致 CC 不能用, 同一类教训)

## 现象 (改前必有数据)

用户反馈: `http://100.109.57.26:3001/` 能打开，但不能对话。
日志 (60min window, `journalctl -u cloudcli.service`):

```
02:24:38  SDK query error: ReferenceError: Claude Code native binary at
          /home/opc2_uname/.npm-global/bin/claude exists but failed to launch.
02:30:40  (同上)
02:33:41  (同上)
02:37:27  (同上)
02:41:07  (同上)
```

5 次失败，全部同一错误。stack 指向 `@anthropic-ai/claude-agent-sdk/sdk.mjs:60:7759`。

## 根因分析

1. SDK 内部用 `child_process.spawn` (Node `Bx`=spawn) 启动 claude binary:
   ```
   sdk.mjs: spawnLocalProcess → Bx(Q,J,{cwd:Y, ...})
   ```
   `Y` = `sdkOptions.cwd`，由 `claude-sdk.js:mapCliOptionsToSDK` 从 `options.cwd` 直接传入。

2. spawn 在 `cwd` 目录不存在时 emit `"error"` 事件，code=ENOENT/EACCES/EPERM/ENOTDIR/ELOOP。
   SDK `gw(d$)` 函数判定这些 code → 抛 `ReferenceError("Claude Code native binary at ... exists but failed to launch")`。
   **这是误导性错误**: 不是 binary 本身问题，是 cwd 不存在。

3. 浏览器前端 (`dist/assets/index-*.js`) 发送:
   ```
   ve = e.fullPath || e.path || ""
   {type:"claude-command", command, options:{cwd:ve, projectPath:ve, ...}}
   ```
   `e.fullPath` 来自用户在 webui 选中的 project。

4. HM2 上 `/api/projects` 返回的注册项目:
   | path | 状态 |
   |------|------|
   | /home/opc2_uname/cc_ps/cc_repair_self | **MISSING** |
   | /home/opc2_uname/cc_ps/hskt | **MISSING** |
   | /home/opc2_uname/cc_ps/jobSpider | **MISSING** |
   | /home/opc2_uname/cc_ps/cc_to_oc | **MISSING** |
   | /home/opc2_uname/cc_ps/cc_webui | EXISTS |

   HM2 home 是 `/home/opc2_uname` (不是 HM1 的 `/home/opc_uname`)。这些 MISSING 项目要么是 HM1 路径残留、要么是已删除目录。用户浏览器打开其中任一并发消息 → cwd 不存在 → spawn ENOENT → "binary failed to launch"。

5. WS chat 路径 (`chat-websocket.service.js`) 把 `data.options.cwd` 原样传给 `runtime.query` → `queryClaudeSDK` → `mapCliOptionsToSDK` → `sdkOptions.cwd`，**无任何校验**。HTTP `/api/agent` 路径 (`agent.js:818`) 有 `fs.access(finalProjectPath)` 校验，但 WS 路径没有 — 这是不对称的 bug。

## 复现 (改前)

`/tmp/ws_test.js` 模拟浏览器 WS 连接，发 `claude-command`:
- cwd=`/home/opc2_uname` (存在) → 成功，回 "hello"
- cwd=`/nonexistent/path/foo` → **复现**: `Claude Code native binary at ... exists but failed to launch`

确认: 失败条件 = cwd 不存在，与 binary 本身无关 (`claude --version` = 2.1.193, CLI `claude -p` 工作正常)。

## 修改

`/home/opc2_uname/cc_ps/cc_webui/dist-server/server/claude-sdk.js` (`mapCliOptionsToSDK`):

```js
// R702: validate cwd exists before passing to spawn — the SDK uses raw
// child_process.spawn, which emits ENOENT when cwd is missing and surfaces
// it as "Claude Code native binary failed to launch". Browser-sent project
// paths (e.g. HM1 paths or removed dirs) may not exist on this host; fall
// back to os.homedir() so the session can still start.
if (cwd) {
    try {
        fsSync.accessSync(cwd);
        sdkOptions.cwd = cwd;
    } catch {
        console.warn(`[WARN] R702: cwd does not exist, falling back to home: ${cwd}`);
        sdkOptions.cwd = os.homedir();
    }
}
```

新增 import: `import * as fsSync from 'fs';`
备份: `claude-sdk.js.bak.R702`

设计选择:
- 修复点选 `mapCliOptionsToSDK` (claude 所有 query 必经之路)，而非 `chat-websocket.service.js` — 这样 HTTP `/api/agent` 路径也受益 (虽然它已有 access 校验，但双保险)。
- fallback 到 `os.homedir()` 而非报错 — 用户体验: 项目目录不存在时仍能对话 (在 home 下)，比直接失败好。前端已显示 "Session started"，后端静默 fallback + 日志 warn 最合理。
- 没碰 SDK 本身 (node_modules 不改)，只改 cloudcli 自己的 wrapper。

## 验证 (改后必有验证)

`sudo systemctl restart cloudcli.service` 后:

| 测试 | cwd | 结果 |
|------|-----|------|
| 回归 (存在) | /home/opc2_uname/cc_ps/cc_webui | ✅ "pong" |
| 修复 (缺失) | /home/opc2_uname/cc_ps/cc_repair_self | ✅ "hello" (fallback 到 home) |
| 修复 (不存在路径) | /nonexistent/path/foo | ✅ "hello" (fallback 到 home) |

日志确认 fallback 触发:
```
[WARN] R702: cwd does not exist, falling back to home: /home/opc2_uname/cc_ps/cc_repair_self
```

WS 端到端测试 (模拟浏览器 `claude-command` 消息) 全部通过，无 "binary failed to launch" 错误。

## Checklist

- [x] 改前数据: 5 次失败日志 + 根因 (cwd ENOENT) + 复现
- [x] 改后验证: 3 个 WS 端到端测试通过
- [x] 未碰 nv_gw / agent 模型选择 / thinking / tool_calls (CC infra-side 边界)
- [x] 未碰 SDK node_modules
- [x] 备份 .bak.R702
- [x] 提交到仓库

## 教训 (写入记忆)

cloudcli WS chat 路径传 cwd 给 SDK spawn 时无校验 → cwd 不存在会以 "binary failed to launch" 形式误报。修复后 fallback 到 home。这是 R699 BUG-7 (误删 cc4101) 同一类教训的延伸: cloudcli 的实际行为依赖很多隐式契约 (cwd 必须存在、backend 必须存活、settings.json 覆盖 .env)，CC 改前要 grep 全链路。
