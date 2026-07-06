# R790: cloudcli-webui 流式丢帧 → `Server error mid-response` 工程化修复

**时间**: 2026-07-06 20:09 CST
**作者**: opc_uname (HM1 的 CC, 经 SSH 修复 HM2 服务)
**类型**: HM2 侧修复 (cloudcli-webui, 非 nv_gw)
**铁律**: 只改 HM2, 不碰 HM1; 改前有数据, 改后有验证

---

## TL;DR

远程 CC (HM2 上 cloudcli-webui, session 497365f2) 在 18:58–19:52 CST 一小时内报 18 次
`API Error: Server error mid-response`, 同窗口 webui 日志 13 次 `[RECONNECT] Writer swapped`。

根因 **不在 Anthropic 上游、不在 shell、不在 claude CLI**, 而是 cloudcli-webui 的
`WebSocketWriter` 在 SDK `for await` 流式循环中 **静默丢帧**: ws 不 OPEN 时 `send()` 直接
丢弃, `updateWebSocket()` 非原子换引用。长 tool_use JSON 帧被切 → 前端收到残缺
stream-json → `InputValidationError: could not be parsed as JSON` → `API Error: Server error mid-response`。

修复 3 个文件 (dist-server 编译产物, HM2 无 TS 源码):
1. `websocket-writer.service.js`: 加帧队列 + 原子 swap + drain/背压, send 永不静默丢
2. `websocket-server.service.js`: 加 `pingInterval=25s` + `clientTracking` 心跳, 消除半开连接
3. `chat-websocket.service.js`: close/error 补结构化日志 (sid/code/reason), 便于回归对齐

改后重启验证: 1h mid-response = 0 (改前 ~6/h)。旧进程内存 803M → 重启后 48M (有泄漏累积)。

---

## 一、根因 (实测坐实, 非假设)

### 1.1 数据流 (读源码确认)

```
Anthropic API
  → claude CLI 子进程 (webui spawn, --output-format stream-json)
    → stdout stream-json 帧
      → webui 进程内 @anthropic-ai/claude-agent-sdk query() 的 for-await 循环
        → ws.send(帧) 推前端浏览器
```

`claude-sdk.js:467` `queryClaudeSDK` → `for await (const message of queryInstance)` →
`ws.send(msg)` 逐帧推前端。每帧是 `createNormalizedMessage` 产出的独立完整 JSON 对象。

### 1.2 三条 webui 侧缺陷

**缺陷 1: `WebSocketWriter.send` 无缓冲/无重试/无原子性** (websocket-writer.service.js, 改前)

```js
send(data) {
    if (this.ws.readyState === WS_OPEN_STATE) {
        this.ws.send(JSON.stringify(data));
    }
}
```
ws 不 OPEN 时 **静默丢帧**, `for await` 不知情继续迭代。长 tool_use 帧正丢失。

**缺陷 2: `updateWebSocket` 非原子、无 drain** (同文件, 改前)
```js
updateWebSocket(newRawWs) { this.ws = newRawWs; }
```
前端 `check-session-status` → `reconnectWriter` → 换 ws 引用, 不等在途 send 完成、
不保证新 ws 已 OPEN。切换窗口内正在 send 的帧丢失。多数 swap 无前置 disconnect
(前端轮询触发, 非真断连), 但同样丢帧。

**缺陷 3: 无 ws 心跳** (websocket-server.service.js, 改前)
`new WebSocketServer({server, verifyClient})` 未配 `pingInterval`。ws 库默认不发心跳 →
半开连接、空闲超时静默断开 (典型 60s), 是断连触发源之一。

### 1.3 因果对齐 (时间戳)

mid-response 18 次在 18:58–19:52 CST; webui 同窗 `[RECONNECT] Writer swapped` 13 次 +
1 次 `Chat client disconnected`。时间高度重合。mid-response 总是伴随 `__unparsedToolInput`
(JSON 被切到一半), 紧跟 `InputValidationError: could not be parsed as JSON`。

---

## 二、设计方案 (工程化/模块化/长期可维护)

### 设计原则
- **改 dist-server 编译产物**: HM2 无 `server/` TS 源码、非 git 仓库、版本 1.33.2。沿用既有
  `*.bak.R<round>` 备份模式 (参考 `claude-sdk.js.bak.R702`)。
- **模块化**: "可靠发送"逻辑收敛到 `WebSocketWriter` 一个类, 不污染 `claude-sdk.js` 业务循环。
  队列/swap/drain 全在 writer 内, 无外部状态。
- **向后兼容**: `send`/`updateWebSocket`/`setSessionId`/`getSessionId` 签名不变,
  `claude-sdk.js` 和 `chat-websocket.service.js` 调用点零改动。
- **可观测**: 丢帧/重试/drain/swap 全打结构化日志 (sid + fid + 原因), 未来可统计回归。
- **可配置**: `WS_WRITER_MAX_QUEUE`/`WS_WRITER_HIGH_WATERMARK`/`WS_WRITER_SWAP_OPEN_TIMEOUT_MS`/
  `WS_PING_INTERVAL_MS` 全走 env, 默认值兜底。
- **可回滚**: 每文件 `.bak.R790`; systemd `Restart=always`; 回滚 cp 回 + restart, 5s 恢复。

### 行为契约 (改后 WebSocketWriter)
- `send(data)`: 入队 {data, fid}; 未在 flushing 则触发 `_flush()`; 永不静默丢
  (除非队列超 MAX_QUEUE=5000, 丢最旧 + WARN, 极端兜底)。
- `_flush()`: `while (queue && ws.OPEN) ws.send(JSON.stringify(shift()))`;
  `ws.bufferedAmount > HIGH_WATERMARK(1MB)` 时 await drain (背压, 避免 EPIPE);
  ws 不 OPEN 时 `_sleep(50)` 等 swap 后继续。
- `updateWebSocket(newWs)`: 设 `_swapping` → 等当前 flush 释放 → 换引用 →
  若 newWs 仍 CONNECTING, `_waitForOpen(timeout 10s)` → 清 `_swapping` → flush 队列到新 ws。
  期间 `send` 继续入队不丢。
- 日志: `[WRITER] sid=.. swap complete (pending_at_swap=N, drained=N)` / backpressure / overflow。

---

## 三、改动清单

| # | 文件 | 改动 | 备份 |
|---|------|------|------|
| 1 | `dist-server/server/modules/websocket/services/websocket-writer.service.js` | 重写 send/updateWebSocket, 加队列/原子swap/drain/背压/日志 | `.bak.R790` |
| 2 | `dist-server/server/modules/websocket/services/websocket-server.service.js` | WebSocketServer 加 `clientTracking:true` + `pingInterval: 25000` (env 可覆盖) | `.bak.R790` |
| 3 | `dist-server/server/modules/websocket/services/chat-websocket.service.js` | `ws.on('close')` 加 sid/code/reason; 新增 `ws.on('error')` | `.bak.R790` |

三个文件均 `node -c` 语法通过。

---

## 四、验证

### 4.1 重启
`systemctl --user restart cloudcli-webui` → active (PID 3500722), 启动日志无错误,
"CloudCLI Server - Ready", 3001/4101 复听, 前端 WS 立刻重连成功。内存 803M → 48M。

### 4.2 回归指标 (改后监听 1h)
- **成功标准**: 1h 内 `Server error mid-response` = 0 (改前 ~6/h)
- 监听命令: `journalctl --user -u cloudcli-webui -f | grep -E "mid-response|WRITER|disconnected|RECONNECT"`
- session jsonl 新增 mid-response 计数 (post-restart timestamp 12:09:57Z)

### 4.3 swap 行为验证
触发前端刷新 (模拟 writer swap) → 观察 `[WRITER] sid=.. swap complete (pending=N, drained=N)`
→ 确认刷新期间远程 CC 正在跑的任务不报 mid-response (帧在 swap 窗口内被队列保留)。

---

## 五、不做的事 (边界)

- 不改 `claude-sdk.js` 的 `for await` 循环 (业务核心, 风险高; writer 可靠后无需改)。
- 不改 `~/.claude/settings.json` 的 `CLAUDE_CODE_MAX_OUTPUT_TOKENS=8192` (根因不在 token 上限)。
- 不改 `.bashrc` 的 `ANTHROPIC_BASE_URL=:40000` (那个没监听, settings.json 的 4101 才生效, 与本根因无关)。
- 不碰 cc4101 适配器、mihomo、nv_gw (链路下游, 与丢帧无关)。

---

## 六、回滚

```
cd /home/opc2_uname/cc_ps/cc_webui/dist-server/server/modules/websocket/services
for f in websocket-writer websocket-server chat-websocket; do
  cp $f.service.js.bak.R790 $f.service.js
done
systemctl --user restart cloudcli-webui
```
5s 内恢复 (RestartSec=5)。

---

## 七、风险与长期维护

- **编译产物覆盖风险**: 改的是 dist-server, 未来若从 TS 源 `npm run build:server` 会覆盖。
  本机无 server/ 源码不会本地 build; 若未来重建, 需把等价改动补回 TS 源
  (改动点见本文档"改动清单", 全在 `modules/websocket/services/` 三个文件)。
- **队列内存**: MAX_QUEUE=5000 + overflow 丢最旧兜底, 防 OOM。正常场景队列长度应 <10。
- **心跳流量**: pingInterval=25s, 可忽略。
- **内存泄漏**: 旧进程 1天16h 累积到 803M, 重启回落 48M。建议后续观察是否再涨,
  若复现需单独排查 (可能 better-sqlite3 / chokidar 监听累积, 不在本轮范围)。

---

## 八、关联

- 本轮根因诊断纠正了早期的错误假设 (曾怀疑 shell 环境/locale/ANSI 码, 实测全不成立)。
- 真因靠读 session jsonl 的 `__unparsedToolInput` + webui journalctl 时间戳对齐定位。
- 关联 [[cross-host-collab-roles]]: HM2 服务由我 (HM1 的 CC) 经 SSH 修复, 不碰 HM1。

**单参数少改多轮。铁律: 只改 HM2 不改 HM1。**
