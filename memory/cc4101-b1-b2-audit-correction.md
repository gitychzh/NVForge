---
name: cc4101-b1-b2-audit-correction
description: "cc4101 B1(content_filter/pending_stop_reason误判200)审计结论被日志证伪; a1db6f13真根因=上游integrate通道120.8s主动断连,非cc4101/nv_gw timeout"
metadata: 
  node_type: memory
  type: project
  originSessionId: 88f513be-ac30-40ea-b01d-436b672c0fa8
---

# cc4101 审计 B1/B2 结论修正 (2026-07-14)

审计 cc4101 时, agent 报了两个 CRITICAL: B1(流中途断连若上游已发finish_reason则当200返回CC不重试) + B2(socket.timeout误归类致根因误判)。核实源码+日志后修正:

## B1 证伪 (对 a1db6f13 不成立)
- a1db6f13 metrics: `finish_reason: null` (上游断连前从未发finish_reason), `status:502`, `error_type:StreamSocketTimeout`, cc4101日志原文 `stream interrupted without finish_reason — emitting api_error SSE so CC retries` → 行117 `if interrupted and pending_stop_reason is None` 条件满足, **正确emit api_error+502**, CC收到retry信号. 这正是用户看到的 "upstream stream interrupted before completion".
- cc4101 stream.py:314-319 (content_filter路径) + 323-333 (自身zombie路径) **都带 return** (R844 F4/F5已修), 不会落到行340设pending_stop_reason. 所以B1的"发过finish_reason就200"只在 `finish_reason=stop/tool_calls正常处理后断连` 这一窄场景成立, 且content_filter/zombie已修. **B1是理论漏洞但低频, 非a1db6f13根因**.

## B2 坐实但根因不在cc4101
- a1db6f13: cc4101记 `error_subcategory=stream_socket_timeout, upstream_timeout_setting_ms=150000, error_message="timed out"`, 但elapsed=120804ms ≠ 150s. cc4101 `except socket.timeout`(stream.py:342) 误归类.
- nv_gw日志铁证: 05:27:25.3 glm5_2_nv `channel=integrate via socks5h://172.18.0.1:7894 timeout=70s` → 05:27:26.4 `NV-GLM52-SUCCESS k3 succeeded` + `NV-THINKING-TIMEOUT extended timeout 150s` → **05:27:26~05:29:26 这2分钟 nv_gw 对该请求无任何后续日志**(无SUCCESS/ERR/DEADLINE/ZOMBIE/IncompleteRead).
- [05:29:45.5]的 `NV stream IncompleteRead after 140245ms` 是另一个dsv4p_nv请求(140s≠120.8s), 时间晚20s, 不是这次.
- **真根因: NVCF integrate上游(经socks5:7894)在~120.8s主动断连**, 既不是cc4101的UPSTREAM_IDLE_TIMEOUT=150s(120.8<150没触发), 也不是nv_gw的NVU_STREAM_TOTAL_DEADLINE_S=90s(若首字节后idle该在~05:28:56触发没触发=上游在发keep-alive byte绕过, 见[[r835b-nv_gw-stream-deadline-ttfb-minimax-fix]]的drip僵尸流同型).
- cc4101先于nv_gw在120.8s抛socket.timeout: cc4101连nv_gw的socket层在对端半关闭/keep-alive语义下read()返回timeout. B10(cc4101默认HTTP/1.0)可能是共谋.

## 待修真bug (按真严重度)
- B2-fix: cc4101区分 `stream_idle_timeout`(真150s无数据) vs `stream_upstream_disconnect`(对端FIN), 看异常类型+sock buffered数据. 不再一律记idle timeout.
- B1-fix(理论): interrupted路径不依赖pending_stop_reason, 强制走api_error(防御finish_reason=stop处理完才断连的窄场景).
- B7: cc4101加stall-watcher对齐nv_gw SILENT_MAX, 防drip僵尸流.
- B5/B6/B3/B4/B8/B9/B10 见审计报告.

**Why:** 审计agent基于dump行号推理, 未交叉日志, 导致B1被高估为a1db6f13根因. 实际cc4101对这次处理正确, 用户报错是上游NVCF integrate主动断连的真实502.
**How to apply:** 下次报"stream interrupted"先看cc4101 metrics的 finish_reason 字段: null=上游断连前没发finish(cc4101处理对, 根因在上游); 非null且status=200=真B1漏洞. 调timeout没用, 该追上游integrate通道稳定性. 关联 [[r842-88k-zombie-window-root-cause]] [[r835b-nv_gw-stream-deadline-ttfb-minimax-fix]] [[glm52-stability-deeptest-r843]].
