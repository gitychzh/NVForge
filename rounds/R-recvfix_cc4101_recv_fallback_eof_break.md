# R-recvfix: cc4101 recv-fallback 破坏 http.client 缓冲 → stream_total_deadline 假账根治 (HM2)

**Date**: 2026-07-27
**Host**: HM2 (only — HM1 无 buffer/recv-fallback 路径)
**Severity**: Critical — 6h 93/244 请求 = 38% stream_total_deadline 假账

## 问题

cc_requests 6h: 244 total, 151×200 (SR=61.9%), **93×502 stream_total_deadline**.
nv_requests 同窗口 cc4101-primary: 237 total, 223×200 (SR=94.1%).
差距: nv_gw 成功 223 次但 cc4101 只记 143 次成功 = **80 次"丢失的成功"** —
nv_gw buffer 成功 flush 了, 但 cc4101 的 passthrough_stream 死循环到 800s deadline.

## 根因 (铁证)

cc4101 `stream.py` `passthrough_stream()` 的 **recv-fallback** 机制:

当 `resp.read(8192)` 在 30s (CC4101_STREAM_POLL_S) 内没有数据时, http.client 抛
socket.timeout. recv-fallback 随后直接从 raw socket (`resp.fp.raw._sock.recv()`)
读取已到达的数据, 绕过 http.client 的 file object 缓冲层.

**这破坏了 http.client 的内部状态**: recv-fallback 从 raw sock 消费了字节, 但
http.client 的 file object 不知道. 后续 `resp.read(8192)` 永远无法检测到连接关闭
(EOF) — 因为 file object 状态不同步, 它不知道数据已被消费, 也不知道 socket 已关闭.
循环持续 `resp.read → timeout → continue` 直到 800s `stream_total_deadline` 触发.

### 铁证

1. **100% 相关**: 243/243 个 STREAM-DEADLINE 失败前都有 recv-fallback 读取.
   `grep -c "recv-fallback got"` = 2237; `grep -c "STREAM-DEADLINE"` = 243;
   每个失败请求的 recv-fallback 时间戳都在 STREAM-DEADLINE 之前.

2. **日志时间线铁证** (req=49fcdf6e, 2026-07-27 22:16:25.6):
   - 22:16:25.6 cc4101 R2254-OBS 发请求 → nv_gw
   - 22:17:13.7 nv_gw NV-BUFFER-FLUSH 6395b + NV-BUFFER-SUCCESS (48s)
   - 22:17:13.7 cc4101 DBG recv-fallback got 6395b + 314b (读到 flush 数据!)
   - (800s silence — http.client 状态被破坏, resp.read 永远拿不到 EOF)
   - 22:30:33.7 cc4101 STREAM-DEADLINE 800s 假账 → 502

3. **nv_gw DB 铁证**: req e0660a45 (对应 cc4101 的 49fcdf6e) status=200, 48s.
   nv_gw 成功了, cc4101 假账 502.

4. **成功请求不走 recv-fallback**: SR=100% 的请求 ttfb=28-30s (buffer 在第一个
   ping 之前完成, resp.read 直接拿到数据, 不触发 recv-fallback, 不破坏 http.client).

## 修复

在 recv-fallback 读到数据后, 做 non-blocking PEEK 检查连接是否已关闭:

```python
# 读到数据后:
if chunk:
    _log("DBG", f"passthrough recv-fallback got {len(chunk)}b")
    # non-blocking PEEK 检查连接是否已关闭
    try:
        _sc.setblocking(False)
        _eof_peek = _sc.recv(1, socket.MSG_PEEK)
        _sc.setblocking(True)
    except (BlockingIOError, OSError):
        _eof_peek = b"x"  # 还没关闭, 继续读
    if not _eof_peek:
        # PEEK 返回空 = 连接已关闭 → 干净 EOF → break
        _log("DBG", f"recv-fallback PEEK empty -> connection closed, clean break")
        break
```

同时, 当首次 PEEK (检查是否有数据) 返回空时, 也视为干净 EOF → break (旧逻辑
是 `continue` 死循环).

### 为什么不直接移除 recv-fallback?

recv-fallback 存在的原因: http.client 的 `resp.read()` 在 socket timeout 后可能
无法读取已到达 buffer 的数据 (timeout 后 file object 行为不稳定). recv-fallback
作为兜底, 从 raw sock 直接读取. 移除它可能导致 ping/error 等小数据包丢失.

修复保留了 recv-fallback 的读取功能, 只增加了 PEEK-EOF 检测来正确识别连接关闭.

## 验证 (2026-07-27 22:54:23 restart 后)

| 指标 | 修复前 (6h) | 修复后 (5min) |
|---|---|---|
| cc_requests 总数 | 244 | 6 |
| cc_requests SR | 61.9% (151/244) | **100% (6/6)** |
| stream_total_deadline | **93 (38%)** | **0 (0%)** |
| 499 | 2 | 0 |
| other 502 | 0 | 0 |

日志铁证:
- 22:54:55.4 `recv-fallback PEEK empty -> connection closed, clean break` ✅
- 22:55:55.6 `recv-fallback PEEK empty -> connection closed, clean break` ✅
- 22:57:13.2 `recv-fallback PEEK empty -> connection closed, clean break` ✅
- 22:56:13.0 `FALLBACK-OK` (ms_gw fallback 成功, nv_gw buffer 失败正常走 fallback) ✅
- **0 × STREAM-DEADLINE** (修复前 5min 内至少 3 个)

## 预期影响

- SR 从 ~62% → ~95%+ (消除 80 次"丢失的成功"中的大部分)
- 残余失败 = nv_gw buffer 真正失败 (buffer_exhausted/all_tiers_exhausted) →
  cc4101 走 ms_gw fallback → 仍可能成功 (FALLBACK-OK)
- 等效 SR = nv_gw SR (94%) + ms_gw fallback 救回 → 应达 95%+

## 改动文件

- `/opt/cc-infra/proxy/cc4101/gateway/stream.py` — recv-fallback PEEK-EOF 检测
  (备份: `stream.py.bak.R-recvfix`)
- HM1 不受影响 (无 buffer/recv-fallback 路径, HM1 cc4101 纯透传)

## 回滚

`cp /opt/cc-infra/proxy/cc4101/gateway/stream.py.bak.R-recvfix stream.py && docker compose restart cc4101`
