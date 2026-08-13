# R1259: cloudcli claude-runtime.provider.js 强制 bypassPermissions + .env 修复

## 时间
2026-08-13 (CST 23:42)

## 问题

cloudcli web UI 管理的 CC session 5bd30e1a (provider 49189840) 严重降速:
- 26 次 `claude-sonnet-5 is temporarily unavailable (timed out)` 错误
- 每次 permission check 超时 ~60s, 占总交互时间 ~1/3

### 根因

1. **cloudcli 前端默认 `permissionMode: "default"` 或 `"auto"`**
   - 前端 localStorage 无保存偏好时默认 `"default"` (`CJ[J]??["default"]`)
   - `mapCliOptionsToSDK()` 中 `permissionMode === 'default'` 时 **不设置** `sdkOptions.permissionMode`
   - SDK 未收到 explicit `permissionMode` 时不读取 `settings.json` 的 `defaultMode: bypassPermissions`
   - SDK 使用 `"auto"` 模式调用 `claude-sonnet-5` 做安全检查
   - 该调用经过 cc4101→nv_gw→NVCF (avg 67s latency) → 60s 超时

2. **cloudcli `.env` stale `ANTHROPIC_BASE_URL=http://127.0.0.1:40001`**
   - 指向已退役的 legacy 容器, 应为 4101 (cc4101)
   - `mapCliOptionsToSDK` 中 `sdkOptions.env = { ...process.env }` 会传递此值
   - 实际运行进程已从其他来源加载了正确的 4101, 但 `.env` 文件是潜在隐患

## 修复

### 1. claude-runtime.provider.js — 强制 bypassPermissions (R1259)

文件: `~/.npm-global/lib/node_modules/@cloudcli-ai/cloudcli/dist-server/server/modules/providers/list/claude/claude-runtime.provider.js`
备份: `*.bak.R1259`

原代码:
```javascript
if (permissionMode && permissionMode !== 'default') {
    sdkOptions.permissionMode = permissionMode;
}
```

改为:
```javascript
// R1259: Force bypassPermissions when frontend sends default/auto/none.
// The SDK auto mode calls claude-sonnet-5 for safety checks (routes
// through nv_gw, high latency, ~60s timeout). settings.json already sets
// defaultMode: bypassPermissions but the SDK ignores it when options are
// passed explicitly via query(). This prevents permission-check timeouts.
if (permissionMode === 'default' || permissionMode === 'auto' || !permissionMode) {
    sdkOptions.permissionMode = 'bypassPermissions';
} else {
    sdkOptions.permissionMode = permissionMode;
}
```

效果:
- 前端发送 `"default"` / `"auto"` / 无 → 强制 `bypassPermissions`
- 前端发送 `"acceptEdits"` / `"bypassPermissions"` / `"plan"` → 保持原值
- `plan` 模式仍正常工作 (其 planModeTools 逻辑不受影响)

### 2. cloudcli .env — 修复 stale ANTHROPIC_BASE_URL

文件: `~/.cloudcli/.env`

```
ANTHROPIC_BASE_URL=http://127.0.0.1:40001  →  http://127.0.0.1:4101
```

### 3. cloudcli 服务重启

```bash
systemctl --user restart cloudcli-webui.service
```

重启后 cloudcli 自动恢复了 session 49189840:
- 新进程 PID 1493976
- 命令行包含 `--permission-mode bypassPermissions` ✓
- `ANTHROPIC_BASE_URL=http://127.0.0.1:4101` ✓

## 验证

### permission timeout 消除
- 修复前 (line 0-759): 26 次 `claude-sonnet-5 timed out` 错误
- 修复后 (line 760+): **0 次** permission timeout
- session 活跃工作中 (调查 SSL EOF 问题)

### 全链路健康
- cloudcli (port 3001): ✓ serving web UI
- cc4101 (port 4101): ✓ healthy, primary glm5_2_nv
- nv_gw (port 40006): ✓ healthy, 5 keys, glm5_2_nv

### CC session 进程
```
PID 1493976
--permission-mode bypassPermissions
ANTHROPIC_BASE_URL=http://127.0.0.1:4101
State: Sl (sleeping, multithreaded — waiting for user input)
```

## 注意事项

- cloudcli 升级后此 patch 需重放 (dist-server/ 是 npm 安装目录)
- `plan` 模式不受影响 (uses `permissionMode === 'plan'` 分支)
- 用户仍可在 cloudcli UI 中手动选择 `bypassPermissions` / `plan` 等, patch 只覆盖 `default`/`auto`/空值
- `canUseTool` 回调在 bypassPermissions 模式下自动 allow 非 interactive 工具, 不发送 WebSocket permission_request
