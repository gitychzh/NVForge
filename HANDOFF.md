# NVForge Handoff — cc4101/opclaw4103 稳定性修复 (R844–R845)

> 本文档供接手 agent 快速上手。聚焦 2026-07-14 前后的 cc4101 / opclaw4103 链路修复。
> 项目全貌见 `CLAUDE.md`（nv_gw 优化主线）与 `docs/`。本手记补充 CLAUDE.md 未覆盖的
> cc4101/opclaw4103 这条 **CC 链路** 的现状与下一步。

## 双机角色（铁律，先读 [[memory]] 的 `cross-host-collab-roles`）

- **HM1（本机，`opc_uname@100.109.57.26` 之外的另一台）= 我**：本地 CC，优化对象是远程 HM2。
- **HM2（远程，`opc2_uname@100.109.57.26`，SSH 走 222 端口）= 被优化的机器**。
- 我改 HM2，绝不改 HM1 自己；push 前必 `git pull --rebase`（远程 CC 也在改 HM1 的副本）。
- GitHub SSH：22 端口被 reset，走 `ssh.github.com:443` 经 mihomo 7891（见 `~/.ssh/config`）。

## 拓扑（HM2 上的 CC 链路，2026-07-14 现状）

```
Claude Code ─→ cc4101 (:4101) ─┬→ nv_gw (:40006, glm5_2_nv, primary)
                              └→ ms_gw (:40007, glm5_2_ms, fallback)
openclaw    ─→ opclaw4103 (:4103) ─┬→ nv_gw (:40006)
                                 └→ ms_gw (:40007)
```

- **cc4101**：Anthropic /v1/messages 格式，做格式转换（Anthropic↔OpenAI）+ early-judgment fallback（仅在 connect/header 阶段切 fallback；SSE 头已发后中途断连只能 emit api_error 让 CC 重试）。
- **opclaw4103**：OpenAI chat-completions 透传，**不做格式转换**，但带 openclaw 专属适配器（R842c content_filter 僵尸中途拦截、R766 reasoning→content、R790 exception content 补、FALLBACK_NOTICE、prompt precheck）+ late-judgment fallback（中途 content_filter 僵尸可切 fallback）。
- 两条链路**独立**，共享 nv_gw/ms_gw 后端，但各自有 fallback 逻辑。
- CLAUDE.md 里的 legacy_*/40001/glm5.1 链路描述已 **stale**；当前 primary 是 `glm5_2_nv`、fallback 是 `glm5_2_ms`。`PRIMARY_HEADER_TIMEOUT=25s`。

## 部署方式（bind mount，无需 rebuild）

两个容器的 `/app/gateway` 都是从宿主 bind mount：
- opclaw4103 ← `/opt/cc-infra/proxy/cc-adapter/gateway/`
- cc4101 ← `/opt/cc-infra/proxy/cc4101/gateway/`

改源码流程：编辑宿主路径 → `docker exec <c> sh -c 'rm -f /app/gateway/__pycache__/*.pyc'`（容器内 root，宿主 opc_uname 无权删容器写的 pyc）→ `docker restart <c>`。改前**必备份** `*.preR<round>.<ts>`。

## 本次做了什么

### R844 — opclaw4103 fallback 迁移 + 超时分层（已部署，回归 OK）
- 把 cc4101 全套 fallback 机制移植进 opclaw4103。
- 修 connect 抖动卡 90s（根因：旧 `_post_upstream` 在 connect 后设 `sock.settimeout(PRIMARY_STREAM_TIMEOUT_S=90s)`，导致 getresponse 用 90s read timeout）。
- 三层超时：connect 10s / header-TTFB 25s(primary)·30s(fallback) / body-idle 150s / 跨阶段总预算 80s。
- circuit 三态（CLOSED/OPEN/HALF_OPEN，`time.monotonic()`，阈值 5，跳过 60s）。
- retry primary 门控（`RETRY_PRIMARY_AFTER_FALLBACK` + remaining ≥ PRIMARY_HEADER_TIMEOUT + 非 OPEN）。
- 保留 R842c/R766/R790/NOTICE。备份 `*.preR844.20260714_050724` 在原地。
- 产物：`deploy_artifacts/R844_opclaw4103_fallback_timeout/{app,config,forwarder}.py` + `PLAN.md`。

### R845 — cc4101 stall-watcher + B2 分类 + B5 conn 泄漏（已部署，回归 OK，触发路径待验证）
源于 a1db6f13 报错 `upstream stream interrupted before completion` 的系统性审计。

**审计关键结论（修正了 agent 的误判，见 `memory/cc4101-b1-b2-audit-correction.md`）：**
- a1db6f13 的 metrics：`finish_reason=null`、`status=502`、`error_type=StreamSocketTimeout`、`elapsed=120804ms`、cc4101 日志 `stream interrupted without finish_reason — emitting api_error SSE so CC retries`。
- **cc4101 对这次处理是正确的**（正确 emit api_error 502 让 CC 重试）。用户看到的报错是 CC 收到 502 后的正常重试提示，**不是 cc4101 的处理 bug**。
- R844 F4/F5 已修 content_filter/zombie 路径（带 `return`），B1（误判 200）对 a1db6f13 不成立。
- **120.8s 的真根因**：NVCF integrate 上游（经 socks5:7894）主动断连，**不是** cc4101 的 150s idle 也不是 nv_gw 的 90s deadline（两者都没触发，上游在发 keep-alive byte 绕过 per-read timeout = drip 僵尸流）。

**R845 改动（3 文件，产物在 `deploy_artifacts/R845_cc4101_stall_watcher_b2_b5/`）：**
- **B7 stall-watcher 双门槛**（用户选定的"总时长+idle"）：config 新增 `CC4101_STREAM_TOTAL_DEADLINE_S=180s`（ttfb 后绝对总时长兜底）/ `CC4101_STREAM_IDLE_GAP_S=60s`（无真内容 idle 间隙上限）/ `CC4101_STREAM_POLL_S=30s`（per-read 短轮询）。`_call_upstream` 默认 per-read 改用 POLL=30s（原 UPSTREAM_IDLE_TIMEOUT=150s 退为"总预算"语义）。stream.py 主循环顶部加双门槛检查点；`resp.read(8192)` 包 try，socket.timeout 时 `continue` 回检查点——**这是让单线程阻塞 read 模型也能在纯静默期判定 stall 的关键**。
- **B2 三分分类**：`except socket.timeout` 不再一律记 idle——`stall_watcher` 命中 / `elapsed≥150s` 真 idle / 否则 `upstream_disconnect`（覆盖 a1db6f13 那种误记）。让 metrics 说真话。
- **B5 conn 泄漏兜底**：send_response 在主 try 之外，CC 早断 BrokenPipe 会泄漏上游 conn + metrics 漏记。stream_to_anth 的 send_response 段包 try/except + handlers.py 调用层包 try/except，记 `client_gone_pre_stream`/`client_gone_mid_stream`/499。

**验证状态：**语法/import OK，常量 180/60/30 加载正确，collect+stream 正常 200 回归，thinking 不误杀。**stall-watcher 触发路径 + B2 分类待真实上游断连场景验证**（下次自然发生时日志出 `STREAM-DEADLINE`/`STREAM-IDLE-STALL`/`StreamUpstreamDisconnect`）。

**诚实边界：**stall-watcher 只在 chunk 之间生效；纯静默时靠 POLL=30s 短轮询强制 read 返回获得检查点（单线程模型的 80% 解法；真正 drip 根治需线程化/select，本轮不做）。POLL=30s 会让 thinking 静默期每 30s 进一次 except→continue，**日志频繁出现但请求正常完成是预期行为，非故障**。

## 未做的真 bug（审计发现，按优先级，留给后续轮次）

| 优先级 | 项 | 文件 | 说明 |
|---|---|---|---|
| P2 | B6 | converters.py `_estimate_text_chars` | 漏算 API `tools` schema，与 R842 compaction tools 根因同源 |
| P2 | B3+B4 | stream.py zombie 检测 | `stream_saw_real_tool_call` 要求同一 chunk 内 id+arguments 都非空（标准 OpenAI 增量协议下永远 False）+ 5000 char 阈值过低 → 误杀合法短回复/tool_use |
| P2 | B8 | stream.py collect 路径 | generic except 不设 error_type → 200+截断内容静默丢 |
| P2 | B9 | upstream.py `_restore_read_timeout` | conn.sock 为 None 时静默退回 25s，可能误杀长 thinking |
| P3 | B10 | app.py | cc4101 默认 HTTP/1.0（`BaseHTTPRequestHandler` 无 `protocol_version="HTTP/1.1"` override），B2 的共谋嫌疑 |
| 理论 | B1 | stream.py | R844 F4/F5 已修 content_filter/zombie 带 return；B1 只在 finish_reason=stop 正常处理后断连的窄场景成立，低频 |

## 当前正在追的问题

**上游 NVCF integrate 通道 ~120s 主动断连**（a1db6f13 根因）。这不是 cc4101/nv_gw 的 timeout 能治的——调 timeout 治标不治本，得靠 fallback 切通道。关联 memory：
- `glm52-stability-deeptest-r843`（88k 僵尸窗口、mode_idx 放大器）
- `r842-88k-zombie-window-root-cause`（system 38.8k + tools 42.4k 死重占 94% context）
- `r835b-nv_gw-stream-deadline-ttfb-minimax-fix`（注意：记忆里写的 `SILENT_MAX=480s` 在当前 nv_gw 源码里**不存在**，实际是 `NVU_STREAM_TOTAL_DEADLINE_S=90s` 首字节后绝对总时长、不重置——这条记忆 stale，接手时以源码为准）

## 接手第一件事

1. `ssh -p 222 opc2_uname@100.109.57.26` 登 HM2。
2. `docker logs --tail 50 cc4101` + `tail /opt/cc-infra/logs/cc4101/metrics.$(date +%F).jsonl` 看 R845 是否被真实场景触发。
3. 若 `StreamUpstreamDisconnect` 出现 = 上游断连被正确归类（R845 B2 生效）；若仍 `StreamSocketTimeout` 且 elapsed<150s = B2 未生效，查 stream.py 是否是新版。
4. 本地 `~/.claude/projects/-home-opc-uname-cc-ps-NVForge/memory/` 有完整 memory 索引（`MEMORY.md` 是入口）。
