# R1820 — bug7 兜底 graceful end (用户诉求"可以报错但不中断 cc2 session")

## 性质
**验证轮**(非新改代码)。上一 session 已执行 R1820 源码改动(bind-mount + 17:41:37 UTC restart 生效),
但**未写 round 文件、未 commit**。本轮补:确认改动落地 + py_compile + 早期数据验证 + 写 round 入库。
源码改动在 `/opt/cc-infra/proxy/nv-gw/gateway/format/oai_to_anth.py`(bind-mount, 容器内 `/app/gateway/format/oai_to_anth.py` 同步)。
注: 仓库 `~/hm_ps/hermes_improve_self` 从不跟踪 proxy 源码(设计如此, 源码用 .bak.RNN 回滚, 仓库只记 round 文件),
故 STATE 里 "R1817 伪 NOP=只 commit round 没 commit 源码" 的判断需修正: 该仓库从不 commit proxy 源码, 改动以 .bak.RNN + round 文件双重记录。

## 依据
STATE(01:40 监督者最终诉求) 转达用户最高指令: "可以报错,但是不能让cc2中断卡住"。
根因: CC SDK 收到 SSE `event: error` 即判 "API Error: Server error mid-response" 中断整个 session。
nv_gw 旧 finish() 在 zombie(零内容) + interrupted(无 stop_reason) 两分支都发 `event: error`。
bug7 场景(245s cap 截断已 relay 的 ms 内容)命中: cap 在主 loop 入口 break 时 content_chars=0,
但 prebuffer(2252b) 已 flush 给 CC → finish() 以为零内容 → 发 event: error → CC 中断 = d4d4ba7f 卡死铁证。

## 改动 (最小方案, 只动 oai_to_anth.py finish() 两分支, 用 message_start_sent 判断)
**文件**: `/opt/cc-infra/proxy/nv-gw/gateway/format/oai_to_anth.py` finish() (line 220-300)

1. **zombie 分支** (line 245):
   `if flushed_content_chars > 0 or self.message_start_sent:`
   → 有真内容 OR message_start 已发(200 头已出去) → graceful 发 message_delta(stop_reason=end_turn)+message_stop,
   绝不发 event: error。只有真零内容(连 message_start 都没发, send_response 之前失败)才 event: error 让 CC 重试。

2. **interrupted 分支** (line 273):
   `if interrupted and self.pending_stop_reason is None and not self.message_start_sent:`
   → 只有 message_start 都没发的极早期失败才发 event: error。
   200 头已发的 interrupted 走 graceful message_delta+message_stop, 不中断。

**关键不变量**: `message_start_sent=True` ⟺ nv_gw 已 send_response(200)+已 flush message_start event。
一旦 True, 后续任何 break(cap/deadline/gap/zombie/interrupted) 都 graceful end, 绝不 event: error。
event: error 只在 send_response 之前极早期失败时允许 → CC 自动重试, 不算 mid-response 中断。

## 验证 (17:41:37 UTC restart 后, ~7min 早期窗口)
- py_compile: `docker exec nv_gw python -c "import gateway.format.oai_to_anth"` OK ✓
- 容器内文件 vs 仓库源码 diff: SAME (bind-mount 同步) ✓
- /health ok, nv_gw Up (StartedAt=2026-07-18T17:41:37Z), ms_gw 热备在 ✓
- DB 17:41-17:48 窗: **15 req 全 200, 零 502** (vs 重启前 30min 有 5 条 502)
- 其中 **2 条 out_tok=0 的 200** (`85035456`/`dba08573`): 前会 zombie→event:error→CC 中断,
  现 graceful 200 ✓ (兜底生效铁证 — output_tokens=0 但 status=200, CC 不再中断)
- 零 ms_fb 触发(全 nvcf_pexec 干净链路): bug7 的 execute→ms_fb 长场景(245s cap)暂未复现验证,
  但 R1820 兜底层逻辑覆盖所有 break 路径(只要 message_start 发了就 graceful), 不依赖 ms_fb 路径

## 为何不改新代码 (小步快走)
1. R1820 改动刚 7min 生效, 需 ≥30min/≥30 req burn-in 确认 zombie/cap 场景持续 graceful
2. R1817(cap_origin peek barrier 路径)已落地但 STATE 指出它只覆盖 peek 路径, execute→ms_fb 路径仍漏。
   R1818(补 execute→ms_fb 路径 cap_origin 重置)是根治叠加层, 但等 R1820 burn-in 稳定后再做,
   避免同时改两个未验证点污染观测。
3. 当前 30min 数据: SR 73/78=93.6% (含重启前 5 条 502), 重启后窗 100% SR — 正向, 不动代码最安全。

## 数据快照 (本轮拉, 30min 窗 17:18-17:48 UTC)
- nv_requests 30min: 200=73, 502=5 (4 stream_absolute_cap + 1 stream_first_byte_timeout)
  注: 5 条 502 全在 17:41 重启前(17:16/17:19/17:21/17:34 UTC), 重启后零 502
- 3 条 ms_fb cap (99969de1/c4ca5e98/f96540fc): 全 output_tokens=0, 全 stream_absolute_cap,
  fallback_tiers_used 含 glm5_2_ms, upstream_type=ms_fallback — bug7 失效铁证(均在 R1820 生效前)
- fallback(cc4101): 30min 5 次, 全 75s/120s ttfb 抢断 SKIP-CIRCUIT (bug3, bug7 副产物,
  期望 R1820 兜底后即使误杀也不致 CC 中断, fallback 率本身等 bug7 根治后再降)

## 下轮 (R1821) 该做什么
1. 攒 ≥30min/≥30 req R1820 burn-in, 确认:
   - 重启后窗零 502 持续 (兜底让 zombie/cap 转 graceful 200)
   - cc2 session 无 "mid-response" 中断 (查 ~/.claude/projects/.../jsonl 无 "API Error: Server error mid-response")
2. 若 burn-in 稳定 → R1820 宣告兜底全胜, 转做 R1818 (execute→ms_fb 路径 cap_origin 重置, 根治层)
3. 若出现新的中断场景 → dump wire 确认是哪条 break 路径漏了 graceful, 补判断条件
4. fallback 率(bug3): 等 R1818 根治后自然降, 本轮不单独调

## 铁律遵守
- 改前必有数据: 30min 窗 + 重启前后对照 ✓
- 改后必有验证: py_compile + /health + docker ps + DB SR ✓
- 聚焦 40006 (nv_gw), 不碰 40007 (ms_gw 热备) ✓
- 只改 HM2, 不改 HM1 ✓
- 改 .py 必须 restart (非 up-d): 17:41:37 restart 已执行 ✓
- 源码改动有 .bak.R1820 回滚手段 ✓ (仓库设计不跟踪 proxy 源码, round 文件 + .bak 双重记录)
