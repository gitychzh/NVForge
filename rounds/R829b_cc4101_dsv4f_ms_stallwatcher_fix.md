# R829b cc4101: dsv4f_ms fallback StreamStallWatcher 根因修复 — select()+read1() 摆脱 timed-out-object

## 摘要

cc4101 fallback 到 ms_gw (dsv4f_ms) 时，`"Response stalled mid-stream"` 错误反复出现。根因是 `socket.settimeout(30s)` 短轮询 + `resp.read()` 模式在数据被 BufferedReader 预读进内部缓冲区后，socket 超时触发 http.client `timed-out-object` 永久崩坏，剩余数据（含 `[DONE]`）读不出，死循环 200s 后 stall-watcher 才 kill。7 天 89 次，今日 6 小时 17 次，SR 89.4%。

## 数据 (改前)

- **7天 89 次** `StreamStallWatcher`，全部在 `dsv4f_ms` fallback 路径，avg duration=252s
- **今日 6 小时 17 次** (12:50-13:52)，持续发生，SR 从 ~97% 降到 89.4%
- 平均浪费 252s/请求，最长 334s
- HM2 不受影响（fallback 链路不同：dsv4f0731_nv→40666，非 ms_gw）

## 根因

### 机制链
1. ms_gw 2s 内发完全部数据 (121KB) 并关闭连接 (`Connection: keep-alive` + HTTP/1.0 无 Content-Length → 靠关连接判 EOF)
2. cc4101 逐步 `resp.read(8192)` 读到 114KB 后，剩余 ~7KB（含 `[DONE]`）已被 `BufferedReader` 从 socket 预读进**内部缓冲区**
3. socket 已空 → 下次 `resp.read(8192)` 阻塞 30s → `socket.timeout` → SocketIO 设 `_timeout_occurred=True`
4. http.client 永久进入 **timed-out-object 状态**：所有后续 `resp.read()` 抛 `OSError("cannot read from timed out object")` (socket.py:701)
5. R1415 recv-fallback 用 `sock.recv(MSG_PEEK)` 查 socket → 空（数据在 BufferedReader 内部缓冲区，不在 socket）→ 误判"无数据" → continue
6. 死循环空转 200s（thinking=Y → idle gap 200s）→ stall-watcher kill → 502

### 核心矛盾
- **R1415 只查 socket buffer (MSG_PEEK)，遗漏 BufferedReader 内部缓冲区**——数据在 `resp.fp` 里，`MSG_PEEK` 看不到
- `BufferedReader.read1()` 在内部缓冲区有数据时走 fast path（不碰 socket），能绕过 timed-out-object 守卫读出数据，但代码用了 `resp.read()`（触发 `_peek_unlocked` → raw.read → OSError）

### 与 R1415 关系
R1415 修的是"**socket** 缓冲有数据但 http.client 读不出"。本次是 R1415 遗漏的**同类 bug 的另一面**：数据在 **BufferedReader 内部缓冲区**而非 socket，R1415 的 `MSG_PEEK` 完全看不到。

## 修复

### stream.py — select() + resp.fp.read1() 替代 socket.settimeout + resp.read()
```python
import select  # 新增

# 主循环内：
# 旧: chunk = resp.read(8192)  # 阻塞30s → timed-out-object
# 新: 1) resp.fp.read1() 先从 BufferedReader 内部缓冲读 (fast path, 不碰 socket)
#     2) 缓冲空时 select() 等 socket 可读 (不设 timeout, 不进 timed-out-object)
#     3) select 超时 → continue 空转 → stall-watcher 检查
chunk = b""
try:
    chunk = resp.fp.read1(8192)  # 内部缓冲 fast path
except (OSError, socket.timeout):
    chunk = b""
if not chunk:
    try:
        _sc = resp.fp.raw._sock
        _readable, _, _ = select.select([_sc], [], [], CC4101_STREAM_POLL_S)
    except Exception:
        _readable = []
    if _readable:
        try:
            chunk = resp.fp.read1(8192)  # socket 有数据, 安全读
        except (OSError, socket.timeout):
            chunk = b""
    # else: select 超时 → chunk=b"" → 空转 → stall-watcher
if chunk:
    _log("DBG", f"read got {len(chunk)}b tail={chunk[-40:]!r}")
```

### upstream.py — `_restore_read_timeout` 改为 emergency backstop
```python
# 旧: sock.settimeout(read_timeout=30s) → per-read 30s 超时 → timed-out-object
# 新: sock.settimeout(max(read_timeout*10, 300s)) — 纯兜底, stall-watcher 200s 先触发
_emergency_timeout = max(float(read_timeout) * 10, 300.0)
```

### 移除 R1415 OSError recv-fallback 路径
不再设 30s socket timeout，http.client 永不进 timed-out-object。`except OSError` 只处理真 OSError（连接重置）→ raise。

## 验证

- [x] `ast.parse` 编译通过
- [x] `docker restart cc4101` + `/health` 200
- [x] 正常流式请求：`[DONE]` 正常到达，无 stall
- [x] ms_gw dsv4f_ms 直连测试正常
- [x] 监控中：无 `STREAM-STALLED`/`timed-out-object`/`recv-fallback`

## 影响

- 消灭 7 天 89 次 stall（每次浪费 ~250s）
- 对正常路径无影响：`select()` 有数据时立即返回（0ms），只在无数据时等待
- 只改 cc4101（HM1 独有路径），HM2 不受影响
- 备份：`stream.py.bak.R-stall-dsv4f`, `upstream.py.bak.R-stall-dsv4f`