# R2425: nv_gw buffer_stream _drain_upstream 100% CPU spin 根治

## Summary

HM2 cloudcli webui "非常卡" 根因: nv_gw 容器 `gateway_main.py` (PID 2323013) 在
`buffer_stream.py` `_drain_upstream()` 的 `while True` 循环中 100% CPU spin ~2h.
同 R829b cc4101 发现的 http.client "timed out object" 问题: `resp.read(8192)` 在
socket timeout 后进入永久坏状态, 每次调用立即抛异常 → `continue` → 无阻塞 → spin.

## 数据 (改前)

```
HM2 ps aux --sort=-%cpu:
  PID 2323013  96.8% CPU  104min CPU time  python3 gateway_main.py

Thread analysis (/proc/1/task/*/stat):
  Thread  1: S (sleeping)  utime=0     ← 主线程正常
  Thread 10: R (running)   utime=644167 ← CPU spin 零线程, 几乎不进 kernel (stime=179)
  Thread  6,7,8,114: S (sleeping)     ← 其他线程正常

nv_gw 日志: 正常处理 cc4101-primary 大请求 (224K chars input), ProbeWorker 正常.
  → spin 不是 I/O 或 probe 导致, 而是某个请求处理线程的读循环空转.
```

## 根因

`buffer_stream.py:_drain_upstream()` line 169 `while True:` 循环:

```python
# 旧代码 (有 bug):
_poll_sock.settimeout(NVU_STREAM_POLL_S)  # = 15s
...
while True:
    try:
        chunk = resp.read(8192)
    except socket.timeout:
        continue            # ← 15s timeout, continue 回 while True
    except OSError as _re:
        if "timed out object" in str(_re):
            _peek = _sc.recv(8192, MSG_PEEK)
            if _peek:
                chunk = _sc.recv(8192)
                if not chunk:
                    continue    # ← recv 返空, continue
            else:
                continue        # ← 无数据, continue
    ...
```

当 NVCF 长时间不返回数据 (如 key 429 cooling, key conn error):
1. `resp.read(8192)` 15s 超时 → `socket.timeout` → `continue`
2. http.client `HTTPResponse.fp` (BufferedReader) 进入 **"timed out object"** 永久坏状态
3. 下次 `resp.read(8192)` **立即** 抛 `OSError: cannot read from timed out object`
4. recv-fallback: `_sc.recv(MSG_PEEK)` 返回空 (socket 无数据) → `continue`
5. 回到 `while True` 顶部 → 再次 `resp.read(8192)` → 立即抛 → `continue`
6. **无任何阻塞的紧密 CPU 循环**, 96.8% CPU, 持续到 deadline (450s) 或请求超时

## 修复 (同 R829b cc4101 方案)

`/opt/cc-infra/proxy/nv-gw/gateway/buffer_stream.py` `_drain_upstream()`:

1. `settimeout(None)` 代替 `settimeout(NVU_STREAM_POLL_S)` — socket 无限阻塞, 不触发 timeout
2. 循环内加 `select.select([_poll_sock], [], [], 5.0)` — 5s 等 socket 可读, 不可读则 continue 回循环检 deadline
3. `resp.read(8192)` 只在 select 确认可读后调用 — 不会进入 timed-out-object 状态
4. recv-fallback 简化为 `continue` (select 已保证可读, 此分支不再触发, 保留兜底)

```python
# 新代码:
_poll_sock.settimeout(None)  # 无限阻塞, 由 select + deadline 控制
...
while True:
    # deadline checks...
    # select 等 socket 可读 (5s 一次回循环检 deadline)
    if _poll_sock is not None:
        _rfds, _, _ = select.select([_poll_sock], [], [], 5.0)
        if not _rfds:
            continue  # 5s 内无数据, 回循环顶部检查 deadline, 然后继续等
    chunk = resp.read(8192)  # select 已保证可读, 不会阻塞也不会 spin
```

## 参数变化

| 参数 | 旧值 | 新值 | 说明 |
|---|---|---|---|
| `_poll_sock.settimeout()` | `NVU_STREAM_POLL_S` (15s) | `None` (无限) | 避免 http.client timed-out-object |
| select guard | 无 | `select(5.0)` | 等 socket 可读, 防止 busy-loop |

## 验证 (改后)

```
HM2 restart nv_gw 后:
  PID 2353393  3.8% CPU → 1.1% CPU (稳定)
  Health: {"status":"ok"}
  /api/auth/status: 14ms (之前因 CPU 被吃满会超时)
  主页: HTTP 200, 2.3ms
  Streaming 测试请求: "Hi! 👋" + [DONE] 正常返回, CPU 不上升

HM1 同步 patch + restart:
  Health: {"status":"ok"}
  CPU 正常
```

## 影响范围

- HM2 `/opt/cc-infra/proxy/nv-gw/gateway/buffer_stream.py` — 主修复
- HM1 `/opt/cc-infra/proxy/nv-gw/gateway/buffer_stream.py` — 预防性同步
- 备份: `buffer_stream.py.bak.R-cpu-spin-fix` (两台)

## 关联

- R829b: cc4101 stream.py 同根因修复 (select + read1)
- [[r829b-cc4101-dsv4f-ms-timed-out-object]]
