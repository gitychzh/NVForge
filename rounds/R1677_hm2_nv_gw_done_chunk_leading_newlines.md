# R1677: HM2 nv_gw 路径B done_chunk 加前导 `\n\n` — 治 malformed SSE 吞掉 [DONE] 致 cc4101 stall-kill mid-response

> 铁律遵守: 改前有数据(req=256c48ff 两端逐字节日志) / 改后有验证(AST+restart+md5) / 聚焦 nv_gw / 写入仓库.
> 破例改 HM2, 沿用 R1672~R1676 方向. 不动 HM1.

## 直接根因 (有逐字节铁证)

R1676 步 B (去掉 `_r1627_should_emit_cf` 的 `or buffer_chunks is None` 析取项) 生效后, 中等 input 的
`stream_no_content_gap` 失败已正确改走路径 B (`NV-STREAM-DONE-FLUSH` 发 `[DONE]`+`connection.close()` 收尾),
不再注入 content_filter. **但 cc4101 仍报 mid-response** — 实测 req=256c48ff:

```
19:39:01 cc4101 [DBG] read got 8192b   ← nv_gw 边读边 flush 的真 content (177c text + reasoning)
19:40:04 nv_gw  [NV-NO-CONTENT-GAP] content_chars=177 — breaking (60s 无真内容)
19:40:04 nv_gw  [NV-STREAM-DONE-FLUSH] sent [DONE] ... closing downstream   ← 路径B 发裸 [DONE]
19:40:04 cc4101 [DBG] recv-fallback got 14b tail=b'data: [DONE]\n\n'         ← 读到了
19:40:04 cc4101 [WARN] malformed SSE chunk: {"id":"chatcmpl-1a82c70e-736e-4e00-9fa0-04679bcb8b5a"data: [DONE]
19:40:44 cc4101 [STREAM-IDLE-STALL] no real content for 100s (stall-watcher)
19:40:44 cc4101 [ERR] stream interrupted without finish_reason — emitting api_error  ← CC mid-response
```

**根因**: 路径 B 的 `done_chunk = b'data: [DONE]\n\n'` (handlers.py:1581) **没有前导 `\n\n`**.
NVCF 最后一个 content chunk 残留在 cc4101 buffer 里没有 `\n\n` 终止符, nv_gw 路径 B 直接发 `data: [DONE]`
就拼成了一坨 malformed event:
```
{"id":"chatcmpl-1a82c70e-736e-4e00-9fa0-04679bcb8b5a"data: [DONE]
```
cc4101 `buffer.split("\n\n")` 切不开 (整坨里只有一个 `\n\n` 在最末, 前半是未终止的 JSON), `json.loads` 失败,
走 stream.py:338 `malformed SSE chunk` 分支 — 该分支的 R846 Fix5 兜底**只识别 `"finish_reason":"content_filter"`
子串** (stream.py:350), 不识别裸 `[DONE]`, 于是 `[DONE]` 信号被吞, cc4101 不知道流已结束, 等 100s 被
stall-watcher kill → `stream interrupted without finish_reason` → api_error → CC mid-response.

对比路径 A (`err_chunk`, handlers.py:1543): 它**有**前导 `\n\n` —
`'\n\ndata: {...content_filter...}\n\ndata: [DONE]\n\n'`, R846 Fix6 专门为防这个 malformed 问题加的.
路径 B 漏了对齐这个 Fix6.

## 改前数据

- req=256c48ff 两端完整日志 (见上), 逐字节证明 [DONE] 到达 cc4101 但被 malformed 吞.
- 重启后 10min 窗口: `STREAM-DONE-FLUSH` 1 次 (路径 B 生效, R1676 步 B OK), `UPSTREAM-ERROR-CHUNK` 5 次
  (均为重启前旧内存, 时间戳 18:58~19:30 < 重启时刻 19:31:41). `NameError/Traceback` = 0 (步 A 修好崩溃).
- `BIGINPUT-FAIL` 0, `breaker OPEN/ms_fallback` 0 — 该窗口无 >250k 大 input 失败, 步 A 的 breaker 兑现
  需等大 input 复发才观测.

## 改动 (一行)

`handlers.py:1581`:
```python
# 改前
done_chunk = b'data: [DONE]\n\n'
# 改后 (加前导 \n\n, 对齐路径A err_chunk R846 Fix6)
done_chunk = b'\n\ndata: [DONE]\n\n'
```

前导 `\n\n` 确保: 即使 NVCF 最后一个 content chunk 残留 cc4101 buffer 无 `\n\n` 终止, 路径 B 的 `\n\n` 也能
强制切断, `data: [DONE]` 成为独立 event, cc4101 `split("\n\n")` 正确切出 → `data_str=="[DONE]"` (stream.py:325)
→ `_emit_graceful_end()` → end_turn → CC 收到完整响应, 不再 mid-response.

- 备份: `handlers.py.bak.R1677` (md5 0dbefb3, R1676 态).
- AST parse OK (容器内 py3.12).
- md5: 0dbefb3 → daa6df6.
- restart 生效, 容器内 grep `R1677` = 1, md5 与宿主一致.

## 预期效果

1. 中等 input `stream_no_content_gap` 失败 (R1676 步 B 已让它走路径 B): 路径 B 的 [DONE] 不再被 malformed
   吞, cc4101 走 `_emit_graceful_end()` 发 end_turn, CC 收到已 flush 的部分内容当完整响应, **不再 mid-response**.
2. 零内容路径 A (content_filter 注入) 不受影响 (err_chunk 本就有前导 \n\n).
3. big_input breaker 兑现 (步 A) 需等大 input 复发观测.

## 验证清单 (待 CC 打够请求, 目标 30~60min 窗口)

- [ ] 中等 input `stream_no_content_gap` 失败后, cc4101 日志无 `malformed SSE chunk` 拼接 [DONE],
      无 `STREAM-IDLE-STALL` 100s kill, 走 `graceful_end` / `message_stop` (end_turn).
- [ ] cc4101 `stream interrupted without finish_reason` + `api_error` 在路径 B 场景下消失.
- [ ] CC 不再报 `Server error mid-response` (至少中等 input content_filter 类不再触发).
- [ ] nv_gw 无 NameError/Traceback.
- [ ] DB 成功率上升.
- [ ] 若大 input (360607 类) 复发: 看 `NV-BIGINPUT-FAIL` → breaker OPEN → ms_fallback (步 A 兑现).

## 累积修复链 (R1672~R1677, mid-response 完整闭环)

| 轮 | 改动 | 治的症状 |
|---|---|---|
| R1672 | first-byte deadline 按 input 分档 | 283k 大 input 被固定 20s 误杀死循环 |
| R1673 | big_input_breaker (input 维度) | 283k hang 连续失败 → OPEN → ms fallback |
| R1674 | cc4101 collect recv-fallback | CC 自身 {Request timed out} (nonstream collect fp 崩坏) |
| R1675 | FULL_BUFFER=0 + breaker 记所有 error_type | 成功响应被全量缓冲吞 (但没 restart 未生效) |
| R1676 | restart nv_gw + 去掉 `_r1627_should_emit_cf` 析取项 | 旧内存未加载 + 已flush内容被注入content_filter |
| **R1677** | **路径B done_chunk 加前导 \n\n** | **路径B [DONE] 被 malformed 吞 → cc4101 stall-kill** |

## 未尽事项

- HM1 代码同步滞后 (本地仓库仅到 R1672 快照). R1676/R1677 改动需择期同步 HM1 + restart, 优先级低.
- cc4101 stream.py:350 的 malformed 兜底只认 content_filter 子串不认裸 [DONE] — R1677 在 nv_gw 侧治本
  (加前导 \n\n 让 [DONE] 不再 malformed), cc4101 侧那个兜底可不动. 若将来有别的 malformed 场景吞 [DONE],
  再考虑扩 cc4101 兜底 (R1678 候选).
