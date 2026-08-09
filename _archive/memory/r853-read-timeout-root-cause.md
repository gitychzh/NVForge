---
name: r853-read-timeout-root-cause
description: "R853 真根因 — cc4101 _restore_read_timeout 用 conn.sock 但 getresponse 后 conn.sock=None, 30s read 超时从没应用到流式 read, 致 stall-watcher 永不触发 8min 挂死"
metadata: 
  node_type: memory
  type: project
  originSessionId: 3c8d8f5f-50f9-4f31-9c0c-b1eae74a0183
---

R853 (2026-07-14): 8分钟挂死的真根因, 修在 cc4101 upstream.py `_restore_read_timeout`.

**真根因**: `_restore_read_timeout(conn, read_timeout)` 用 `conn.sock` 取 socket 调 settimeout(30s=CC4101_STREAM_POLL_S). 但 http.client 在 `getresponse()` 后把 sock 移到 `resp.fp.raw._sock`, **`conn.sock` 变 None** → `if sock is not None` 失败 → 静默 pass → **30s per-read 超时从没应用到流式 read** → `resp.read(8192)` 无限阻塞 → cc4101 stream.py 主循环的 stall-watcher 双门槛检查(在 read 之后)永远拿不到检查点 → R847(100s)/R850(200s thinking) idle-gap + total-deadline 全是死代码 → GLM5.2 thinking 静默期上游不发 chunk, cc4101 干等 8min+ CC 永远收不到 api_error.

**诊断方法**(可复用): 本地起一个发完 200 header 就挂住不发 body 的 HTTP server, `conn.getresponse()` 后 print `conn.sock` → None, 但 `resp.fp.raw._sock` 是真 socket.socket, gettimeout/settimeout 都可用, settimeout(5) 后 resp.read 果然 5s 抛 socket.timeout. 证明 socket 在 resp.fp.raw._sock 不在 conn.sock.

**修复**: `_restore_read_timeout(conn, read_timeout, resp=None)` — conn.sock is None 时 fallback 到 `resp.fp.raw._sock` 取真 socket. 调用点 `_restore_read_timeout(conn, idle_timeout, resp=resp)`.

**验证**: 修前 probe thinking 请求挂 8min+ 无任何 api_error; 修后 200s(thinking idle gap) stall-watcher 准时触发 → STREAM-IDLE-STALL → api_error "stream interrupted" → CC retry. 见 21:20:06-09 日志.

**为什么 R847/R850 之前"看起来部分有效"**: 那些修的是 idle-gap 阈值和 thinking 翻倍, 阈值本身对, 但前提是 stall-watcher 能跑 — 而它跑不了因为 read 阻塞. R853 是让整个 stall-watcher 机制真正生效的底座修复. 没有 R853, 所有 stream.py 里的 deadline/idle 检查都是纸上谈兵.

关联: [[r850-thinking-silence-miskill-fix]] [[r847-deadline-inversion-root-cause]] [[r846-stream-interrupted-fix]]
