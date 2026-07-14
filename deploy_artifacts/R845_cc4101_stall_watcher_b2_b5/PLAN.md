# cc4101 B2 + B7 修复方案

## 背景
a1db6f13 核实结论：cc4101 对该请求处理正确（emit api_error 502 让 CC 重试），但 metrics 把上游主动断连误记成 `stream_socket_timeout / idle 150s`（实际 120.8s）。根因不在 cc4101/nv_gw timeout，而是 NVCF integrate 上游主动断连。但暴露两个真 bug：
- **B2**：`except socket.timeout` 一律记 idle timeout，区分不了"上游主动断连"。
- **B7**：cc4101 无 stall-watcher，`resp.read(8192)` 阻塞时循环回不到任何 deadline 检查，per-read socket timeout(150s) 被 keep-alive drip 绕过即彻底失明（nv_gw 至少有 `stream_idle_deadline` 检查点，cc4101 连这个都没有）。

## 范围
改 cc4101 的 `stream.py`（`stream_to_anth` + `collect_stream_to_anth`）+ `config.py` + `upstream.py`（B5: `_post_upstream` 返回后 conn 生命周期）。不动 nv_gw。

## B7: stream stall-watcher — 总时长+idle 双门槛（用户选定）

### 核心难题与解法
cc4101 主循环是单线程阻塞 `resp.read(8192)`（stream.py:167/401）。纯静默时 read 阻塞，循环回不到检查点——这是双门槛里"idle 间隙"判定的死穴。

**解法：把 per-read socket timeout 从 150s 拆成短超时循环 read**。`_restore_read_timeout` 后把 per-read 设为 `CC4101_STREAM_POLL_S=30s`，read 每次最多阻塞 30s 就抛 `socket.timeout`，在 except 里**不立即 break**，而是检查 idle 间隙：
- 若 `time.time() - last_progress_time > CC4101_STREAM_IDLE_GAP_S(60s)` → 真 stall，break + 标记
- 若未超 idle 间隙上限 → 继续循环 read（thinking 静默期合法）

这样双门槛都生效：
- **总时长上限**：`CC4101_STREAM_TOTAL_DEADLINE_S=180s`（ttfb 后，chunk 间检查，兜底防无限挂，高于正常长思考）
- **idle 间隙**：`last_progress_time`（收到真 content/reasoning/tool_call 时更新），`time.time() - last_progress_time > 60s` → stall

per-read 从 150s→30s 的副作用：thinking 静默期每 30s 会抛一次 socket.timeout 进 except，需在 except 里识别"非 stall，继续"。代码上 `except socket.timeout` 不再一律 `_emit_graceful_end`，先判 stall。

### config.py 新增
```python
# R845 B7: stream stall-watcher 双门槛 (用户选定 总时长+idle).
CC4101_STREAM_TOTAL_DEADLINE_S = float(os.environ.get("CC4101_STREAM_TOTAL_DEADLINE_S", "180"))  # ttfb 后绝对总时长兜底
CC4101_STREAM_IDLE_GAP_S = float(os.environ.get("CC4101_STREAM_IDLE_GAP_S", "60"))  # 无真内容的 idle 间隙上限
CC4101_STREAM_POLL_S = float(os.environ.get("CC4101_STREAM_POLL_S", "30"))  # per-read socket timeout (短轮询获取检查点)
```
注意：`UPSTREAM_IDLE_TIMEOUT=150s` 语义变更——它不再是 per-read timeout，而是"兜底总预算"。per-read 改用 `CC4101_STREAM_POLL_S`。`_restore_read_timeout(conn, CC4101_STREAM_POLL_S)`。

### stream_to_anth 主循环改造（stream.py:167 + 342）
```python
# 初始化 (ttfb_recorded 附近)
stream_total_deadline = None
last_progress_time = None

while True:
    # B7 双门槛检查点 (chunk 之间)
    if ttfb_recorded and stream_total_deadline and time.time() > stream_total_deadline:
        metrics["error_type"] = "stream_total_deadline"
        _log("STREAM-DEADLINE", f"({request_model}) total {CC4101_STREAM_TOTAL_DEADLINE_S}s after ttfb exceeded")
        _emit_graceful_end(interrupted=True); return
    if last_progress_time and time.time() - last_progress_time > CC4101_STREAM_IDLE_GAP_S:
        metrics["error_type"] = "stream_idle_stall"
        _log("STREAM-IDLE-STALL", f"({request_model}) no content for {CC4101_STREAM_IDLE_GAP_S}s (stall-watcher)")
        _emit_graceful_end(interrupted=True); return
    try:
        chunk = resp.read(8192)
    except socket.timeout:
        # per-read 30s 超时 — 非致命, 上面双门槛会在下一轮循环判定. continue 回到检查点.
        continue
    if not chunk:
        break
    ...
    # 有真内容时更新 last_progress_time (在解析 delta 后)
    if delta.get("content") or delta.get("reasoning_content") or delta.get("tool_calls"):
        last_progress_time = time.time()
```

**ttfb 记录点（行217附近）同步设 `stream_total_deadline = time.time() + CC4101_STREAM_TOTAL_DEADLINE_S` 和 `last_progress_time = time.time()`。**

### except socket.timeout 改造（B2 合并到此）
原行342 `except socket.timeout` 现在分两类来源：
1. stall-watcher 主动 raise 的（B7 双门槛命中）→ 已设 `error_type`，不覆盖
2. 真 per-read 超时但未达 stall 阈值 → 上面用 try/continue 吞了，不会到这里
3. 上游主动断连伪装成 socket.timeout（elapsed<150s）→ B2 分类

```python
except socket.timeout as e:
    elapsed_ms = int((time.time() - t_start) * 1000)
    # B2: 区分 stall-watcher 命中 vs per-read idle vs 上游断连伪装
    if metrics.get("error_type") in ("stream_total_deadline", "stream_idle_stall"):
        error_subcat = metrics["error_type"]
        timeout_kind = "stall_watcher"
    elif elapsed_ms >= UPSTREAM_IDLE_TIMEOUT * 1000 - 500:
        error_subcat = "stream_socket_timeout"; timeout_kind = "idle"
    else:
        # 120.8s < 150s = 上游主动断连被 socket.timeout 误捕 (a1db6f13 同型)
        error_subcat = "stream_upstream_disconnect"; timeout_kind = "upstream_disconnect"
        metrics["error_type"] = "StreamUpstreamDisconnect"
    _log_error_detail({...error_subcategory: error_subcat, upstream_timeout_kind: timeout_kind...})
    _emit_graceful_end(interrupted=True); return
```

### collect_stream_to_anth 同步改造（stream.py:401 循环 + 475 except）
同样的双门槛 + 短 read + continue 模式。

## B5: send_response 在 try 外的 conn 泄漏

### 问题
stream.py:312-317（stream_to_anth）和 collect 的 send_response 阶段在主 try 之外。CC 在 cc4101 拿到上游 200 后、SSE header 发出前断开 → BrokenPipe 冒泡，handlers.py:176 之后无 try/except → 上游 conn 不 close、metrics 漏记。

### 方案
1. **stream.py**：把 `send_response`/`end_headers`（行312-317）挪进主 try 块，或在前面加 `try:`。
2. **handlers.py:176-218**：`execute_request`/`stream_to_anth` 调用包 `try/finally`，finally 里 `conn.close()`（若非 None）+ 异常时记 metrics(status=502, error_type=ClientGoneMidStream)。

### handlers.py 改造
```python
# 176 附近
try:
    execute_request(self, body, mapped_model, request_id, metrics, t_start, ...)
    enqueue_metrics(metrics)
except (BrokenPipeError, ConnectionResetError, OSError) as e:
    _log("ERR", f"client gone mid-stream after {int((time.time()-t_start)*1000)}ms: {e}")
    metrics["error_type"] = "client_gone_mid_stream"
    metrics["status"] = 499  # client closed
    enqueue_metrics(metrics)
    # upstream conn close 由 stream_to_anth 内部 finally 兜底 (见下)
finally:
    # 兜底: 若 stream_to_anth 未正常 close conn
    pass  # conn 生命周期在 stream_to_anth 内, 见 B5-stream
```

### stream.py finally
在 `stream_to_anth` 末尾加 `finally:` 块确保 `conn.close()`（覆盖 send_response 阶段异常路径）。collect 同理。

## 不做（诚实边界）
- **B1**（理论漏洞）：R844 F4/F5 已修 content_filter/zombie 路径带 return，B1 只在 finish_reason=stop 正常处理后断连的窄场景成立，低频，本轮不动。
- **B6/B3/B4/B8/B9/B10**：P2-P3，本轮聚焦 a1db6f13 直接对症的 B2+B7+B5，其余后续轮次。
- 短 per-read(30s) 会增加 thinking 静默期的 socket.timeout 抛出频次（每 30s 一次进 except→continue），有轻微 CPU 开销，但 thinking 静默期本就罕见且短，可接受。

## 部署
bind mount 模式：改宿主 `/opt/cc-infra/proxy/cc4101/gateway/stream.py` + `config.py` + `handlers.py`，`rm __pycache__/*.pyc` + `docker restart cc4101`，无需 rebuild。先备份 `*.preR845.YYYYMMDD_HHMMSS`。

## 验证
1. 语法：`docker exec cc4101 python3 -c "import gateway.stream, gateway.config, gateway.handlers"`
2. stall-watcher 双门槛测：临时 `CC4101_STREAM_TOTAL_DEADLINE_S=10` + 模拟 ttfb 后持续发 chunk 的上游，确认 `STREAM-DEADLINE`+`stream_total_deadline`；临时 `CC4101_STREAM_IDLE_GAP_S=5` + ttfb 后静默上游，确认 `STREAM-IDLE-STALL`+`stream_idle_stall`。
3. B2 分类测：复跑 a1db6f13 同型（上游 ~120s 断连），确认 metrics 记 `StreamUpstreamDisconnect`/`stream_upstream_disconnect` 而非 `StreamSocketTimeout`。
4. 回归：正常短请求 + 正常 thinking 长请求（持续产出 >180s）不受影响。**注意**：total_deadline=180s 是绝对总时长，>180s 的超长思考会被触发——需确认 glm5.2 正常思考上限，若是则调高；否则用 idle 间隙（持续产出时 last_progress_time 持续更新不触发）兜底即可，total 只防纯挂死。
5. B5 回归：curl 大请求中途 Ctrl-C，确认上游 conn 不泄漏、metrics 记 `client_gone_mid_stream`/499。
