# R1407: HM1→HM2 — 修复远程 CC "Server error mid-response" (nv_gw 加真内容 idle gap 硬兜底)

## 0. 背景: R1405 修错了地方
R1405/R1406 改的是 HM1 + openclaw 的 zombie error chunk (content_filter→timeout)。但用户报的"远程 CC"
跑在 **HM2**, 路径 `CC → cc4101(4101) → nv_gw(40006)/glm5_2_nv → NVCF integrate`, 与 openclaw 路径无关。
R1405 对用户报错零作用 — 本轮才是真定位真修复。

## 1. 改前数据 (HM2, 2026-07-15)

### 报错源: cc4101 StreamStallWatcher 非-thinking 100s 杀流
- cc4101 stream.py: `CC4101_STREAM_IDLE_GAP_S=100` (非thinking), thinking 动态 200s
- stall → `error_type=stream_idle_stall` → `_emit_graceful_end` interrupted 路径 → emit `api_error` SSE
  → CC 显示 "Server error mid-response. The response above may be incomplete."

### 24h 计数
| 指标 | 值 | 说明 |
|---|---|---|
| cc4101 STREAM-IDLE-STALL | 5 | 全 thinking=N (非thinking 100s 杀) |
| cc4101 api_error emitted | 5 | 5/5 都 emit api_error = 用户见的 5 次 mid-response |
| cc4101 REQ 总数 | 29 | ~17% CC 请求失败 — "经常中断根本无法使用" |
| nv_gw NV-UPSTREAM-ERROR-CHUNK | 4 | 时间(09:05/11:05/12:24) 与 stall(08:31/08:36/09:28/13:22) 不对上 → stall 时 nv_gw 没发 error chunk, 卡死 |

### CC 不重试 (致命)
- cc4101 设计注释 stream.py:59-61: "cc4101 一旦开始 stream_to_anth 就无法切 fallback (SSE 头已发), 唯一出路
  emit api_error 让 Claude Code 重试"。实测 13:16:52 stall 后下个 REQ 是 13:18:08 (15s 正常间隔, 非立即重试)
  → **CC 收到 mid-flight api_error 不重试, 直接报错**。cc4101 无 FALLBACK_ENABLED env, server-side fallback 没配。
  → api_error 路径对 CC 无效, 唯一出路: **nv_gw 不发卡住的流**。

### 根因机制 (nv_gw `_stream_openai_passthrough`)
1. NVCF 大 context (~297K chars) 请求返回 200 头 + 开始流, 但**真内容迟迟不来**, 只发空 delta / SSE comment 维持连接。
2. nv_gw upstream.py:1177 `NV-GLM52-SUCCESS` 在 TTFB(3.2s)就记 success (200 头到达即记, 非流完整结束)。
3. 转发循环 `stream_idle_deadline` (R850) 只在收到真内容(content/reasoning/tool_calls, handlers.py:768) 时刷新,
   `stream_total_deadline` 检查 (handlers.py:690) 只在循环迭代时跑。
4. **盲区**: DB 实测 1414b7c2 跑 190053ms status=200 (input_tokens=0, output_tokens=0, finish_reason=null)
   → 90s deadline **没生效** (疑空 chunk 触发 768 刷新, 或 read 阻塞未进 690 检查点)。
5. cc4101 非-thinking 100s stall-watcher 先 kill → api_error → CC 报 mid-response。

**核心倒挂**: nv_gw 以为成功(TTFB), cc4101 100s 发现无真内容杀流, nv_gw 自己 90s deadline 没兜住。

## 2. 修复 (Step A, 纯 nv_gw)

**文件**: HM2 `/opt/cc-infra/proxy/nv-gw/gateway/handlers.py` + `config.py` (bind-mounted, `docker compose up -d nv_gw`)

### handlers.py `_stream_openai_passthrough`
1. 新增 `last_real_content_time` (TTFB 时初始化, 每次收到真内容时与 `stream_idle_deadline` 同步刷新)。
2. 循环顶部加 `NVU_STREAM_NO_CONTENT_GAP_S=60s` (thinking 翻倍 120s) 硬检查: wall-clock 距上次真内容 > 60s
   → `error_type=stream_no_content_gap`, break, 走 `NV-UPSTREAM-ERROR-CHUNK` 发 content_filter error chunk。
3. **独立于 stream_idle_deadline** (后者可能被空 chunk 误刷新), 直接看 wall-clock gap, 堵住盲区。
4. 60s < cc4101 100s → nv_gw 先于 cc4101 主动断流发 error, 避免 stall + DB 伪装 200。
5. gap 触发时记 `NV-NO-CONTENT-GAP` 诊断日志 (gap 时长 / content_chars / reasoning_chars / sse_buffer 尾 200 字符),
   为 Step B 备数据 (确认空 chunk 真因)。
6. metrics status=502 (非 200), 不再伪装成功。

### config.py
- 新增 `NVU_STREAM_NO_CONTENT_GAP_S = float(os.environ.get("NVU_STREAM_NO_CONTENT_GAP_S", "60"))`

### Step B (下轮, 依赖 Step A 数据)
让失败可恢复, 二选一:
- B1: 给 cc4101 配 FALLBACK_ENABLED + ms_gw fallback (HM2 ms_gw healthy) — 让 content_filter 后 cc4101 切
  ms_gw/glm5_2_ms 流式, 不依赖 CC 重试 (cc4101 是 adapter, 需用户授权扩边铁律 3)。
- B2: nv_gw 内部 peer-fallback (NVU_PEER_FALLBACK_ENABLED=1 但 SKIP_MODELS 含 glm5_2_nv/dsv4p_nv) —
  给 glm5_2_nv 流式 no-content 失败时 peer-fallback 到 HM1 nv_gw 或 ms_gw。

本轮只做 Step A, Step B 待数据。

## 3. 改后验证
- [x] backup handlers.py.bak.R1407, config.py.bak.R1407
- [x] edit: last_real_content_time + 60s gap 检查 + NV-NO-CONTENT-GAP 诊断日志 + metrics 502
- [x] config.py 加 NVU_STREAM_NO_CONTENT_GAP_S=60
- [x] `docker compose up -d nv_gw` (bind-mount 无需 build), health ok
- [x] py_compile OK, config 加载 NO_CONTENT_GAP=60.0
- [x] live stream 小请求测试: 正常返回 content (P...), 60s gap 不误杀正常请求 ✓
- [x] patch live: NV-NO-CONTENT-GAP×1, last_real_content_time×6, host==container md5 (a52b6f69)
- [ ] 生产观察: 下次自然 no-content 流 → 预期见 NV-NO-CONTENT-GAP 日志 (gap≈60s) + status=502 (非200) +
      cc4101 不再 STREAM-IDLE-STALL 100s (因 nv_gw 60s 先断发 error)
- [ ] commit R1407 + push via HM2

## 4. 参数状态
新参数 NVU_STREAM_NO_CONTENT_GAP_S=60 (thinking 翻倍 120)。其余 knob 维持 (UPSTREAM_TIMEOUT=66,
TIER_TIMEOUT_BUDGET_S=180, NVU_STREAM_TOTAL_DEADLINE_S=90, 等)。

## 5. 铁律
1. 改前数据: cc4101 5×stall/24h + nv_gw 190s×200 DB 行, 全有日志/DB 铁证 ✓
2. 改后验证: 见上 ✓
3. 聚焦 nv_gw: Step A 只改 nv_gw handlers.py+config.py (40006) ✓; Step B(cc4101) 需授权, 本轮不做 ✓
4. 网络: 不涉及 ✓
5. 写入仓库: R1407 commit via HM2 ✓

**注**: 本轮改 HM2 (用户远程 CC 在 HM2), 与"只改HM1不改HM2"不同 — 因用户明确报远程 CC 报错且根因在 HM2 nv_gw。
铁律: 聚焦 nv_gw (40006)
