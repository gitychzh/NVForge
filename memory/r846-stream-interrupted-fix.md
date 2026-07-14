---
name: r846-stream-interrupted-fix
description: "系统修复 cc4101 的 \"upstream stream interrupted before completion\" 报错; 真根因=R845 OSError bug + total_deadline 误杀 + content_filter chunk 被 malformed 吞掉; 6 个 Fix 已全应用"
metadata: 
  node_type: memory
  type: project
  originSessionId: 3c8d8f5f-50f9-4f31-9c0c-b1eae74a0183
---

# R846 修复 "upstream stream interrupted before completion"

报错字符串只由 cc4101 `/app/gateway/stream.py:140` 的 `if interrupted and pending_stop_reason is None` 路径 emit。R846 深挖出三个真根因，全部已应用 Fix 并验证。

## 三层根因 + 修复

### 根因 1（已修，Fix 3）：R845 per-read OSError 误判
R845 的 stall-watcher 用 `CC4101_STREAM_POLL_S=30s` per-read 短轮询，但 `sock.settimeout` 超时后 `socket.SocketIO.read()` 抛的是**裸 `OSError("cannot read from timed out object")`**（socket.py:717 `_timeout_occurred`），不是 `socket.timeout` 子类。R845 的 `except socket.timeout: continue` 接不住 → 落到致命 `except OSError` → `interrupted=True` → emit "upstream stream interrupted"。

**Fix 3**: `except OSError as _read_e:` 里检查 `if "timed out object" in str(_read_e) or "timeout" in str(_read_e).lower(): continue`（stream.py:212-219 + collect 路径 530-532）。
**验证**: Fix3 后 StreamInterrupted 归零（15:33 后 0 例，之前是主要变体）。

### 根因 2（已修，Fix 4）：total_deadline=180s 误杀正常长请求
glm5.2 thinking(90s) + 长文输出(200s) 正常超过 ttfb+180s total_deadline → 硬断 → emit interrupted。实测 `51493627`：模型产出 99 个 content chunk（raw_bytes 铁证，content "测量时间..."）被 180s 硬断。对比 `84733357`（190s 成功 7551 tokens，边界稍严即误杀）。

**Fix 4**: `CC4101_STREAM_TOTAL_DEADLINE_S` 180→360s（config.py）。容纳 thinking+长文。真静默仍由 `IDLE_GAP_S=60s` 兜底。

### 根因 3（已修，Fix 5+6，最关键）：content_filter chunk 被 malformed 吞掉
Fix 1（R846 阶段一）让 nv_gw 在 deadline break 时写 `finish_reason=content_filter` error chunk。但验证发现 cc4101 收到后**仍返回 200+null**（`f1784cb7`/`983d0437`/`cbd5da4b` 多例）。

用 mal_buf.jsonl 捕获 wire 真相：cc4101 收到的 event_str 是
```
data: {...reasoning_content:" Time"...}],data: {"choices":[...finish_reason":"content_filter"...]}
```
**两个 SSE event 被拼成一个，中间缺 `\n\n`**。原因：上游最后一个 passthrough chunk 的 `\n\n` 残留在 nv_gw sse_buffer 未 flush（或被 8192 read 切断），nv_gw 直接写 `data: {...content_filter...}\n\n`（无前置 `\n\n`），与 cc4101 buffer 里未终止的上个 event 拼成 `}],data: {...}` → `json.loads` 整体失败 → malformed → `continue` 吞掉 content_filter → 返回空 200。

**Fix 6（nv_gw 治本）**: err_chunk 前置 `\n\n` 确保上个 event SSE 终止符完整（handlers.py:841）：
```python
err_chunk = ('\n\ndata: {"choices":[...content_filter...]}\n\n'
             'data: [DONE]\n\n').encode("utf-8")
```
**Fix 5（cc4101 兜底）**: `except json.JSONDecodeError` 块里检查 `data_str` 含 `"finish_reason":"content_filter"` 子串 → 当 zombie 处理 emit api_error（stream.py:265-274）。防 Fix6 失效。

**验证**（`3c41554b`，Fix5/6 后）：nv_gw 写 content_filter → Fix6 让其独立成 event → cc4101 正常 json.loads 解析出 `finish_reason=content_filter` → 触发 `ZOMBIE-CONTENT-FILTER` → status=**502** + error_type=`upstream_content_filter` → emit api_error → CC 重试命中 fallback。对比之前同场景返回 200+null+0token（空响应 CC 不重试）。

## 全部 Fix 清单
| Fix | 位置 | 内容 |
|---|---|---|
| 1 | nv_gw handlers.py 833-843 | deadline/except break 时写 content_filter error chunk（阶段一） |
| 2a | cc4101 stream.py 223-238 | 干净 EOF 无 finish_reason 判 zombie_clean_eof |
| 2b | cc4101 stream.py 88 | 放宽 empty 守卫至 `next_block_idx==0 or (content极少+大input)` |
| 3 | cc4101 stream.py 212-219,530-532 | per-read OSError("timed out object") 非致命 continue |
| 4 | cc4101 config.py | TOTAL_DEADLINE_S 180→360s |
| 5 | cc4101 stream.py 265-274 | malformed chunk 含 content_filter 子串当 zombie |
| 6 | nv_gw handlers.py 841 | err_chunk 前置 `\n\n` 确保 SSE event 分离 |

## 关联
- 修 [[r845-cc4101-stall-watcher-b2-b5-fix]] 的 OSError bug 残留（socket.py:717 裸 OSError 不被 socket.timeout 接住）
- 复用 [[r840-openclaw-zombie-empty-stall-fix]] 的 content_filter 信号机制
- 详见 plan: /home/opc_uname/.claude/plans/r846-stream-interrupted-fix.md
