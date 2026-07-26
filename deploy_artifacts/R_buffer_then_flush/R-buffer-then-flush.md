# Plan: nv_gw buffer-then-flush 模式 (cc2 zombie 根治)

## 目标

对 cc4101-primary caller 的流式请求，在 nv_gw 的 `_stream_openai_to_anth` 中：
- **不立即转发 chunks 给 CC**，buffer 在内存里
- **每 30s 发 `event: ping` 占位符**，重置 CC SDK idle timer
- 流结束后用 `judge_stream()` 判定三者齐全（content + finish_reason + [DONE]）
- **成功** → 一次性 flush 全部 buffered content 给 CC
- **失败** → 废弃 buffer，同 key 重试，最多 3 次
- **3 次全败** → 发 `event: error` 给 CC
- 总预算 600s（150+200+200+余量），在 R2254 watchdog 600s 之内

## 门控

- 只对 `metrics["caller"] == "cc4101-primary"` 生效
- 其他 caller（hermes/openclaw/opencode/交互式 session）照常流式
- 新 env `NVU_BUFFER_CALLERS=cc4101-primary`（逗号分隔，可扩展）
- 新 env `NVU_BUFFER_MAX_RETRIES=3`
- 新 env `NVU_BUFFER_TIMEOUT_STAIRS=150,200,200`（毫秒也行，这里用秒）

## 实现方案

### 1. 新文件：`gateway/buffer_stream.py`

封装 buffer+判定+重试逻辑，被 handlers.py 调用。

```python
class BufferStreamSession:
    """一次 buffer 会话，管理一次 NVCF 流的完整生命周期。"""
    
    def __init__(self, handler, oai_body, metrics, t_start, request_model, 
                 converter, execute_fn):
        self.handler = handler          # BaseHTTPRequestHandler 子类
        self.oai_body = oai_body
        self.metrics = metrics
        self.t_start = t_start
        self.request_model = request_model
        self.converter = converter      # OaiSseToAnthropicConverter
        self.execute_fn = execute_fn    # execute_request 函数引用
        
        self.buffered_bytes = b""       # converter 输出的 anthropic SSE bytes
        self.state = StreamState()      # 来自 stream_success_judge.py
        self.ping_interval_s = 30
        self.attempt = 0
        self.max_retries = 3
        self.timeout_stairs = [150, 200, 200]  # 秒
    
    def _send_ping(self):
        """发 anthropic event:ping 占位符给 CC"""
        ping = b"event: ping\ndata: {}\n\n"
        self.handler.wfile.write(ping)
        self.handler.wfile.flush()
    
    def _send_sse_headers(self):
        """发 200 + SSE headers（commit point）"""
        self.handler.send_response(200)
        self.handler.send_header("Content-Type", "text/event-stream")
        self.handler.send_header("Cache-Control", "no-cache")
        self.handler.send_header("Connection", "close")
        self.handler.close_connection = True
        self.handler.end_headers()
    
    def _drain_upstream(self, resp, conn, timeout_s):
        """
        从 NVCF 读流，feed 给 converter，buffer 输出 bytes，不转发给 CC。
        用 StreamState 跟踪。
        
        返回: (verdict, error_reason)
          verdict = StreamVerdict 枚举值
          error_reason = str | None（超时/异常信息）
        """
        import socket as _sock
        _poll_sock = conn.sock
        if _poll_sock is None and resp is not None:
            try:
                _poll_sock = resp.fp.raw._sock
            except:
                _poll_sock = None
        if _poll_sock is not None:
            _poll_sock.settimeout(15)  # NVU_STREAM_POLL_S
        
        deadline = time.time() + timeout_s
        last_ping = time.time()
        sse_buffer = ""
        
        while True:
            # 总 deadline 检查
            if time.time() > deadline:
                return judge_stream(self.state), "total_deadline"
            
            try:
                chunk = resp.read(8192)
            except socket.timeout:
                # 30s ping（用 timeout 周期发 ping）
                if time.time() - last_ping >= self.ping_interval_s:
                    self._send_ping()
                    last_ping = time.time()
                continue
            except OSError as e:
                # R1704 recv-fallback（同主循环）
                if "timeout" in str(e).lower():
                    try:
                        _sc = resp.fp.raw._sock
                        _peek = _sc.recv(8192, _sock.MSG_PEEK)
                    except:
                        _peek = b''
                    if _peek:
                        try:
                            chunk = _sc.recv(8192)
                        except:
                            chunk = b''
                        if not chunk:
                            continue
                    else:
                        if time.time() - last_ping >= self.ping_interval_s:
                            self._send_ping()
                            last_ping = time.time()
                        continue
                else:
                    mark_connection_closed(self.state, e)
                    return judge_stream(self.state), f"OSError:{type(e).__name__}"
            
            if not chunk:
                # 连接关了
                mark_connection_closed(self.state)
                return judge_stream(self.state), "connection_closed"
            
            sse_buffer += chunk.decode("utf-8", errors="replace")
            
            # parse SSE events
            while "\n\n" in sse_buffer:
                event_str, sse_buffer = sse_buffer.split("\n\n", 1)
                data_str = ""
                for line in event_str.split("\n"):
                    if line.startswith("data:"):
                        data_str = line[5:].strip()
                
                if not data_str:
                    continue
                if data_str == "[DONE]":
                    mark_done(self.state)
                    continue
                
                try:
                    chunk_data = json.loads(data_str)
                except:
                    continue
                
                update_state_from_chunk(self.state, chunk_data)
                
                # feed converter, buffer output
                out_bytes = self.converter.feed_chunk(chunk_data)
                if out_bytes:
                    self.buffered_bytes += out_bytes
            
            # 检查是否已收到 finish_reason + [DONE]（可以提前结束）
            if self.state.finish_reason and self.state.saw_done:
                # 流完整结束
                return judge_stream(self.state), None
    
    def _execute_and_drain(self, timeout_s):
        """
        调 execute_request 获取 NVCF 流，drain 到 buffer，判定。
        返回 (verdict, error_reason, resp, conn)
        """
        from .upstream import execute_request
        
        result = execute_request(
            self.handler, self.oai_body, 
            self.metrics.get("mapped_model", self.request_model),
            self.metrics.get("request_id", "?"),
            self.metrics, self.t_start
        )
        
        if not result.success:
            return None, "execute_failed", None, None
        
        resp = result.resp
        conn = result.conn
        self.metrics["nv_key_idx"] = result.nv_key_idx
        
        verdict, reason = self._drain_upstream(resp, conn, timeout_s)
        
        try:
            conn.close()
        except:
            pass
        
        return verdict, reason, resp, conn
    
    def run(self):
        """
        主入口：运行 buffer+判定+重试循环。
        
        返回 True = 成功（已 flush 给 CC）
        返回 False = 3 次全败（已发 error 给 CC）
        """
        self._send_sse_headers()
        
        total_deadline = time.time() + 580  # 留 20s 余量
        
        for attempt in range(self.max_retries):
            self.attempt = attempt
            timeout_s = self.timeout_stairs[min(attempt, len(self.timeout_stairs)-1)]
            
            if time.time() + timeout_s > total_deadline:
                timeout_s = max(30, total_deadline - time.time())
            
            _log("NV-BUFFER-ATTEMPT", 
                 f"({self.request_model}) attempt={attempt+1}/{self.max_retries} "
                 f"timeout={timeout_s}s caller={self.metrics.get('caller')} "
                 f"req={self.metrics.get('request_id','?')}")
            
            verdict, reason, resp, conn = self._execute_and_drain(timeout_s)
            
            _log("NV-BUFFER-VERDICT",
                 f"({self.request_model}) attempt={attempt+1} "
                 f"verdict={verdict.value if verdict else 'None'} "
                 f"reason={reason} "
                 f"content={self.state.content_chars}c "
                 f"reasoning={self.state.reasoning_chars}c "
                 f"fr={self.state.finish_reason} "
                 f"done={self.state.saw_done} "
                 f"buffered={len(self.buffered_bytes)}b "
                 f"req={self.metrics.get('request_id','?')}")
            
            if verdict is not None and not should_retry(verdict):
                # 成功！flush buffer 给 CC
                if self.buffered_bytes:
                    try:
                        self.handler.wfile.write(self.buffered_bytes)
                        self.handler.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError, OSError):
                        _log("NV-BUFFER-FLUSH-FAIL",
                             f"({self.request_model}) CC gone during flush")
                        return True  # 内容已发，CC 自己断
                
                # 发终末事件
                fin = self.converter.finish(
                    interrupted=False, zombie=False,
                    input_tokens_real=self.state.content_chars,
                    flushed_content_chars=self.state.content_chars
                )
                if fin:
                    try:
                        self.handler.wfile.write(fin)
                        self.handler.wfile.flush()
                    except:
                        pass
                
                self.metrics["status"] = 200
                self.metrics["finish_reason"] = self.state.finish_reason
                self.metrics["duration_ms"] = int((time.time() - self.t_start) * 1000)
                _log_metrics(self.metrics)
                return True
            
            # 失败，重置 buffer + state + converter
            self.buffered_bytes = b""
            self.state = StreamState()
            self.converter = OaiSseToAnthropicConverter(
                self.request_model, 
                request_id=self.metrics.get("request_id")
            )
            
            _log("NV-BUFFER-RETRY",
                 f"({self.request_model}) attempt={attempt+1} failed "
                 f"({verdict.value if verdict else reason}), retrying")
        
        # 3 次全败，发 error
        _log("NV-BUFFER-EXHAUSTED",
             f"({self.request_model}) all {self.max_retries} attempts failed, "
             f"sending error to CC")
        
        err_evt = _sse_bytes("error", {
            "type": "error",
            "error": {"type": "api_error",
                      "message": "upstream stream incomplete after 3 retries"},
        })
        try:
            self.handler.wfile.write(err_evt)
            self.handler.wfile.flush()
        except:
            pass
        
        self.metrics["status"] = 502
        self.metrics["error_type"] = "buffer_exhausted"
        self.metrics["duration_ms"] = int((time.time() - self.t_start) * 1000)
        _log_metrics(self.metrics)
        return False
```

### 2. handlers.py 修改：`_stream_openai_to_anth` 入口分流

在 `_stream_openai_to_anth` 方法开头（~line 920），在现有逻辑之前加一个门控分支：

```python
def _stream_openai_to_anth(self, resp, conn, metrics, t_start, request_model, oai_body=None):
    # ── R-buffer: cc2 buffer-then-flush 模式 ──
    # 对 cc4101-primary caller，不立即转发流，buffer 到判定成功后一次性发
    _caller = metrics.get("caller", "")
    if _caller in NVU_BUFFER_CALLERS:
        from .buffer_stream import BufferStreamSession
        from .format.oai_to_anth import OaiSseToAnthropicConverter
        converter = OaiSseToAnthropicConverter(
            request_model, request_id=metrics.get("request_id"))
        session = BufferStreamSession(
            handler=self, oai_body=oai_body, metrics=metrics,
            t_start=t_start, request_model=request_model,
            converter=converter, execute_fn=None)
        session.run()
        # 清理 resp/conn（如果 execute_request 在 session 内部创建的）
        try:
            conn.close()
        except:
            pass
        return
    
    # ── 原有流式逻辑（其他 caller）──
    converter = OaiSseToAnthropicConverter(...)
    # ... 现有代码不动 ...
```

**关键**：buffer 模式下 `execute_request` 在 `BufferStreamSession._execute_and_drain` 内部调用，不需要外部传入的 `resp/conn`。外部的 `execute_request` 结果（已成功获取的 resp/conn）需要被关闭释放，由 buffer session 自己重新发起请求。

**但更简单的方案**：直接利用外层已经调用的 `execute_request` 结果——resp/conn 已经在手，不需要重新调。改为：

```python
def _stream_openai_to_anth(self, resp, conn, metrics, t_start, request_model, oai_body=None):
    _caller = metrics.get("caller", "")
    if _caller in NVU_BUFFER_CALLERS:
        from .buffer_stream import BufferStreamSession
        converter = OaiSseToAnthropicConverter(
            request_model, request_id=metrics.get("request_id"))
        session = BufferStreamSession(
            handler=self, resp=resp, conn=conn, oai_body=oai_body,
            metrics=metrics, t_start=t_start, request_model=request_model,
            converter=converter)
        session.run()
        return
    
    # 原有逻辑...
```

BufferStreamSession 直接用传入的 resp/conn 做第一次 drain，重试时才重新调 `execute_request`。

### 3. config.py 新增 env

```python
# ─── R-buffer: cc2 buffer-then-flush 模式 ───
NVU_BUFFER_CALLERS = {c.strip() for c in os.environ.get('NVU_BUFFER_CALLERS', '').split(',') if c.strip()}
NVU_BUFFER_MAX_RETRIES = int(os.environ.get('NVU_BUFFER_MAX_RETRIES', '3'))
NVU_BUFFER_TIMEOUT_STAIRS = [int(x) for x in os.environ.get('NVU_BUFFER_TIMEOUT_STAIRS', '150,200,200').split(',')]
NVU_BUFFER_PING_INTERVAL_S = int(os.environ.get('NVU_BUFFER_PING_INTERVAL_S', '30'))
NVU_BUFFER_TOTAL_DEADLINE_S = int(os.environ.get('NVU_BUFFER_TOTAL_DEADLINE_S', '580'))
```

### 4. stream_success_judge.py 放入 gateway/ 目录

已有的 `stream_success_judge.py` 放到 `/opt/cc-infra/proxy/nv-gw/gateway/stream_success_judge.py`，被 buffer_stream.py import。

### 5. docker-compose.yml 新增 env

```yaml
  nv_gw:
    environment:
      NVU_BUFFER_CALLERS: "cc4101-primary"
      NVU_BUFFER_MAX_RETRIES: "3"
      NVU_BUFFER_TIMEOUT_STAIRS: "150,200,200"
      NVU_BUFFER_PING_INTERVAL_S: "30"
      NVU_BUFFER_TOTAL_DEADLINE_S: "580"
```

### 6. 数据记录（用户要求详细日志）

每次 attempt 记录：
```
NV-BUFFER-ATTEMPT: attempt=1/3 timeout=150s caller=cc4101-primary req=xxx
NV-BUFFER-VERDICT: attempt=1 verdict=zombie_partial reason=total_deadline content=234c reasoning=0c fr=None done=False buffered=1240b req=xxx
NV-BUFFER-RETRY: attempt=1 failed (zombie_partial), retrying
NV-BUFFER-ATTEMPT: attempt=2/3 timeout=200s ...
NV-BUFFER-VERDICT: attempt=2 verdict=success_text reason=None content=1523c fr=stop done=True buffered=8200b req=xxx
```

最终结果记录到 metrics：
- `metrics["buffer_attempt"]` = 成功的 attempt 编号
- `metrics["buffer_verdict"]` = 最终 verdict
- `metrics["buffer_total_retries"]` = 总重试次数
- `metrics["error_type"]` = "buffer_exhausted" 如果全败

## 部署步骤

1. **写文件**：
   - `gateway/stream_success_judge.py`（已有，复制过去）
   - `gateway/buffer_stream.py`（新文件）
   - 修改 `gateway/handlers.py`（加门控分支，~10 行）
   - 修改 `gateway/config.py`（加 env，~6 行）

2. **改 compose**：加 env 到 `docker-compose.yml` nv_gw 段

3. **部署到 HM2**：
   ```bash
   cd /opt/cc-infra
   # backup
   cp docker-compose.yml docker-compose.yml.bak.R-buffer
   # 改 compose
   # gateway/ 是 bind-mount，直接改文件
   docker compose up -d nv_gw  # restart 即可，不需要 rebuild
   ```

4. **验证**：
   - `curl http://localhost:40006/health`
   - 检查 `docker exec nv_gw env | grep BUFFER`
   - 等 cc2 发请求，看日志 `NV-BUFFER-*`
   - 确认交互式 session（非 cc4101-primary caller）不受影响

5. **回滚**：
   - `NVU_BUFFER_CALLERS=""`（空字符串 = 对所有 caller 禁用）
   - 或 `docker compose up -d nv_gw` 用备份 compose

## 风险评估

| 风险 | 严重度 | 缓解 |
|---|---|---|
| ping 不被 SDK 识别 | 高 | anthropic 协议原生支持 event:ping，SDK yield 它 |
| TTFB 变高（buffer 等完整流） | 中 | cc2 无人值守，TTFB 不重要 |
| thinking 被误杀重试 | 中 | 有详细日志，total_deadline 兜底，用户已接受 |
| NVCF 额度消耗 ×3 | 中 | 同 key 重试（用户指定），后期可换 key |
| R2254 watchdog 600s 冲突 | 低 | 总预算 580s，留 20s 余量 |
| buffer 内存占用 | 低 | 单次请求 max ~300K，3 次重试不累积（每次清空） |
