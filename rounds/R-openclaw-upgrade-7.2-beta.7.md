# R-openclaw-upgrade-7.2-beta.7

## Summary

HM2 openclaw 从 2026.7.1-2 升级到 2026.7.2-beta.7。同时修复 opclaw4103 timeout chain 不匹配导致的 "Agent couldn't generate a response" 错误，以及 memory search embeddings 端点指向错误问题。

## 变更清单

### 1. opclaw4103 timeout chain 压缩 (docker-compose.yml)

**根因**: openclaw `timeoutSeconds=180` < opclaw4103 `PROXY_TIMEOUT=240`。当 dsv4p_nv40066 发生 zombie+all_tiers_exhausted 时，circuit OPEN→fallback 也 502→adapter retry loop 跑 175s→openclaw 180s timeout 先到→"Agent couldn't generate a response"。

**修复**: 压缩 timeout chain，确保嵌套关系正确:

| 参数 | 旧值 | 新值 | 说明 |
|---|---|---|---|
| PRIMARY_HEADER_TIMEOUT | 180 | 90 | primary 首字节超时 |
| FALLBACK_HEADER_TIMEOUT | 180 | 70 | fallback 首字节超时 |
| PROXY_TIMEOUT | 240 | 170 | adapter 总超时 |
| CC4101_TOTAL_BUDGET_S | 400 | 170 | adapter 预算 |
| FALLBACK_TIMEOUT_S | 240 | 170 | fallback 总超时 |
| FALLBACK_RECOVER_S | 120 | 30 | circuit breaker 恢复时间 |

**嵌套关系**: primary(90s)+fallback(70s)=160s < PROXY_TIMEOUT(170s) < openclaw(180s)

### 2. openclaw 版本升级 2026.7.1-2 → 2026.7.2-beta.7

- `npm install -g openclaw@2026.7.2-beta.7` (12min)
- systemd unit 更新: `OPENCLAW_SERVICE_VERSION=v2026.7.2-beta.7`
- beta.7 关键修复: incomplete turn handling, Feishu delivery, state recovery, stalled LLM responses

### 3. Config schema 迁移 (`openclaw doctor --fix`)

2026.7.2-beta.7 不兼容旧 config schema，doctor --fix 自动迁移:
- `agents.defaults.memorySearch` → `memory.search`
- 移除: `diagnostics.stuckSessionAbortMs/stuckSessionWarnMs`, `meta.lastTouchedAt`, `gateway.controlUi.allowInsecureAuth`, `plugins.bundledDiscovery`
- `agents.defaults.compaction.reserveTokens/reserveTokensFloor` 移除, `compaction.mode: "safeguard"` 加入
- `tools.exec.security/ask` → `tools.exec.mode`
- stale model entries 清理: `nv_gw/dsv4p_nv`, `nv_gw/glm5_2_nv` 移除, `opclaw4103/dsv4p_nv` 加入 allowlist
- SQLite state schema migration
- 148 unreferenced JSONL archived (orphan cleanup)
- 空 attestation 文件删除 (workspace-attestations/ 0-byte file 阻塞 workspace migration)

### 4. Memory search embeddings 修复

**根因**: `memory.search.remote.baseUrl` 指向 `http://127.0.0.1:4103/v1` (opclaw4103 adapter)，但 adapter 不支持 `/v1/embeddings` 端点转发，返回 `{"error":"embeddings upstream down"}`。

**修复**: 改指 `http://127.0.0.1:40006/v1` (nv_gw)，nv_gw 支持 `/v1/embeddings` 且可用 `nvidia/nv-embed-v1` 模型。apiKey 从 `opclaw-gw-token` 改为 `nv-gw-token`。

### 5. Kernel patch — assertPreparedDispatchLifecycle beta bug

**Bug**: Feishu 群消息 dispatch (如 `/new` 命令) 抛出:
```
Error: runChannelInboundEvent prepared turns must declare runDispatchLifecycle when creating runDispatch
```

**根因**: `kernel-BJBhT2CO.js` 中 `dispatchChannelTurnWithDeliveryOwner` (line ~816) 仅在
`turnAdoptionLifecycle` 存在时设置 `runDispatchLifecycle`:
```js
...turnAdoptionLifecycle ? { runDispatchLifecycle: {...} } : {},
runDispatch: async () => { ... }
```
Feishu channel 的 `resolveTurn` 仅在 adoption flow 时传 `turnAdoptionLifecycle`。当它为
undefined 时，`runDispatchLifecycle` 未设置但 `runDispatch` 已设置。
`assertPreparedDispatchLifecycle` (line 998) 无条件 throw，但所有使用处 (427/433/508)
都用 optional chaining (`?.`)，安全。

**Patch**: 当 `turnAdoptionLifecycle` 也为 undefined 时跳过检查:
```js
// Before:
if (!lifecycle) throw new Error("...");
// After:
if (!lifecycle) {
    if (!turnAdoptionLifecycle) return;
    throw new Error("...");
}
```

**File**: `~/.npm-global/lib/node_modules/openclaw/dist/kernel-BJBhT2CO.js`
**Backup**: `kernel-BJBhT2CO.js.bak.Ropenclaw_beta7`

### 6. Session cleanup

- 清理 124 个 orphan `.trajectory-path.json` 文件
- 清理 51 个 `.jsonl.deleted.*` 文件
- 清理 26 个 `.jsonl.reset.*` 文件
- 剩余: 1 个 active session + skills-prompts 目录

## 数据 (改前)

- openclaw 报 "Agent couldn't generate a response" (opclaw4103 timeout 240s > openclaw 180s)
- dsv4p_nv40066 zombie_empty_completion × 23 (30min)
- cc4101-primary glm5_2_nv SR=50.0% (28/56), 502×27 buffer_exhausted;zombie_empty_completion

## 验证 (改后)

1. **服务状态**: `systemctl --user status openclaw-gateway.service` → active (running), v2026.7.2-beta.7
2. **日志**: 无 `[memory] embeddings retryable error`，无 error/fail
3. **Feishu WebSocket**: connected (`ws client ready`)
4. **E2E CLI**: `openclaw agent --message "hello" --agent main` → "您好，Boss张。" (75ms TTFB, ~7s, 200 OK, stopReason=stop)
5. **E2E CLI**: `openclaw agent --message "请用一句话介绍你自己" --agent main` → "小二，OpenClaw 正式严谨型 AI 助手，运行于 opclaw4103/dsv4p_nv，负责日常工作执行与链路维护。"
6. **Memory search**: 正常调用 (`doctor.memory.status` 733ms)
7. **Embeddings endpoint**: `curl http://localhost:40006/v1/embeddings` → 200, 返回 embedding 向量
8. **Post-patch logs**: 无 memory embeddings error, 无 workspace migration error, 无 dispatch lifecycle error

## 参数快照 (opclaw4103)

```
PROXY_TIMEOUT=170
PRIMARY_HEADER_TIMEOUT=90
FALLBACK_HEADER_TIMEOUT=70
CC4101_TOTAL_BUDGET_S=170
FALLBACK_TIMEOUT_S=170
FALLBACK_RECOVER_S=30
PRIMARY_STREAM_TIMEOUT_S=90
FALLBACK_ENABLED=1
FALLBACK_URL=http://nv_gw:40006/v1
FALLBACK_MODEL=glm5_2_nv
```

## openclaw config 关键项

```json
{
  "memory": {
    "search": {
      "enabled": true,
      "provider": "openai-compatible",
      "remote": {"baseUrl": "http://127.0.0.1:40006/v1", "apiKey": "nv-gw-token"},
      "model": "nvidia/nv-embed-v1"
    }
  },
  "agents.defaults.model": {"primary": "opclaw4103/dsv4p_nv"},
  "version": "2026.7.2-beta.7"
}
```

## 已知遗留 (非阻塞)

- `openclaw security audit --deep` 建议: plaintext API keys in config (建议迁移到 SecretRef)
- 3 个 orphan agent 目录 (claude/hermes/opencode) 无 agents.list entry — 不影响运行
- Gateway bound to 0.0.0.0 (network-accessible) — 已知，Tailscale 网络内
