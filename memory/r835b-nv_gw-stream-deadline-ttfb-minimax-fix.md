---
name: r835b-nv_gw-stream-deadline-ttfb-minimax-fix
description: "R834审计P0/P2补完: nv_gw流式idle deadline(首字节后42s)治SSE喂饭式卡死+删ttfb=duration兜底暴露无首字节真相+integrate per-model tier budget(minimax 180s治502);补r835-openclaw-tidal-mist留的未做项"
metadata:
  node_type: memory
  type: project
  originSessionId: 25380329-22e9-46a9-be9b-8af44f0d1a9b
---

2026-07-10 03:00 补完 R834 审计的 P0-1/P0-2/P2-8 修复 (r835-openclaw-tidal-mist-systemic-fix 明确留的"未做-修复4 nv_gw单请求TTFB上限"). 铁律合规: 只改 HM1, 不碰 HM2, 不 patch openclaw bundle.

## 3 修复 (handlers.py + upstream.py + config.py + compose + stall-watcher.sh)

### P0-1 流式 idle deadline (首字节后) — 治 SSE 喂饭式卡死
- 根因: `upstream.py:252 conn.sock.settimeout(read_timeout)` 是 **per-read socket 超时**; SSE upstream 持续发 keep-alive chunk (每次都在 read_timeout 窗口内) → 单次 read 永不超时 → 流永不中断 → openclaw 等流结束等到 abort (R834 审计 P0 铁证: 流持续 102s)
- 修: `_stream_openai_passthrough` (handlers.py:666) + `_accumulate_stream_to_nonstream` (handlers.py:472) 的 `while True` 循环加 `stream_idle_deadline` — **从首字节(ttfb)之后算**, 不是从 t_start. 超过就 break + 记 `error_type=stream_total_deadline`
- **关键设计**: 必须从 ttfb 后算, 不是 t_start — 否则砍 glm5.2 thinking 慢 ttfb (实测 max 71s, 由 NVU_INTEGRATE_THINKING_TIMEOUT_S=90 per-attempt 管). 此 deadline 只兜"流已开始但持续不结束"的僵尸流
- env `NVU_STREAM_TOTAL_DEADLINE_S=42` (< openclaw nv_gw timeoutSeconds=45s, 让 nv_gw 先干净 break 给 openclaw failover, 不留半截连接); config.py 默认 90 (env 未设时)

### P0-2 删 ttfb=duration 兜底 — 暴露无首字节真相
- 根因: `handlers.py:642-643` (accumulate 末尾) 的 `if not metrics.get("ttfb_ms"): metrics["ttfb_ms"] = metrics["duration_ms"]` — 流式超时无首字节时 ttfb 被填成 duration, **掩盖"根本没收到首字节"事实** (验证铁证 11575=11575)
- 修: 改 `metrics["ttfb_ms"] = 0` (留 0 让 stall-watcher/DB 能识别). stream_total_deadline 已记 error_type
- 非流式 line 446 `ttfb_ms = int((ttfb_start - t_start)*1000)` 不动 (ttfb_start 在 getresponse 后=首字节, 正确). ms_gw peer fallback relay 两处 (line 921/1037) 不动 (在首 chunk 记真 ttfb, 无兜底 bug)

### P2-8 integrate per-model tier budget — 治 minimax 502
- 根因: minimax_m3_nv reasoning_effort=high 实测 ~156s, 但 integrate 路径 tier budget 用全局 `TIER_TIMEOUT_BUDGET_S=112s` (upstream.py 旧 line 186/191/242 直接用全局, **无 per-model override**). pexec 路径早有 `NVU_TIER_BUDGET_{model}` (line 503), integrate 路径之前没有
- 修: `_try_integrate_keys` 加 `_integ_tier_budget_env = os.environ.get(f"NVU_TIER_BUDGET_{tier_model.upper()}")` + `tier_budget_s` (复用 pexec line 491-503 模式); line 186/191/248 的 `TIER_TIMEOUT_BUDGET_S` → `tier_budget_s`
- compose env `NVU_TIER_BUDGET_MINIMAX_M3_NV=180` (不影响 glm5.2 专属 96s 和 dsv4p/kimi 走 pexec)

### P0-3 stall-watcher SILENT_MAX — 僵尸流硬兜底 (本会话加, 补 r835 tidal-mist 的 FAULT_WIN 分支)
- stall-watcher.sh 加 `SILENT_MAX=480` (8min), 判定逻辑最前加硬兜底: `silent_s >= 480` 不管 last_status 直接重启
- 根因: nv_gw 侧记 status=200 (收到首 chunk) 但 SSE 流持续不结束 → openclaw 静默 9min+ → 原逻辑 last_status=200 只 watch 不重启 → 僵尸流永不救

## 协调点 (重要)
- **r835-openclaw-tidal-mist-systemic-fix** (另一 session, 02:30 做) 已把 openclaw.json `nv_gw timeoutSeconds 100→45s, ms_gw 50→30s` + 加 fallback `nv_gw/dsv4p_nv` + stall-watcher FAULT_WIN_S 硬故障分支 + stuckSession 收紧. 我的 `NVU_STREAM_TOTAL_DEADLINE_S=42` 必须配合它的 45s (42<45). 两者互补不冲突
- 它的 stall-watcher FAULT_WIN 分支 (扫 fetch timeout/All models failed 硬故障) 和我的 SILENT_MAX 分支并存: 一个抓硬故障信号, 一个抓静默时长, 互补

## 验证
- 语法: config/handlers/upstream ast.parse OK, stall-watcher bash -n OK
- 容器: `docker compose up -d --force-recreate nv_gw` (force-recreate 非 restart, env 才生效)
- env 生效: `NVU_STREAM_TOTAL_DEADLINE_S=42`, `NVU_TIER_BUDGET_MINIMAX_M3_NV=180`
- E2E: 非流式 dsv4p 200 OK; 流式 dsv4p SSE 正常输出; minimax 200 OK; **minimax thinking(high) 25.9s 200 OK 393字推理** (旧 112s 能过 25s, 但 156s 慢请求会被砍, 180s 容下)
- ttfb 验证: metrics 502 行 `dur=98823 ttfb=5596` (ttfb 是真实首字节 5.6s, 不再被兜成 98s duration); 正常 200 行 `dur=9915 ttfb=2966` (ttfb<dur 正常)

## 未做/不做
- P1-4 安全 (iptables/allowedOrigins/disableDeviceAuth) — 用户明确豁免
- 不 patch openclaw minified bundle (R830 决定)
- 不动 ms_gw 共享源码 (HM1+HM2 共享, 外科 patch 不整覆盖)
- 不动 pexec 路径 timeout (保护 dsv4p/kimi 精调)
