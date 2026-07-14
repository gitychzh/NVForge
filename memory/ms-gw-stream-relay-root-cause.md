---
name: ms-gw-stream-relay-root-cause
description: "ms_gw 流式中断的真正根因 — HTTP/1.0 + keep-alive + 无 Content-Length/chunked 导致客户端无法判定响应边界, 卡 120s"
metadata: 
  node_type: memory
  type: project
  originSessionId: 9f86955b-051d-43b2-9038-4442ccdeff80
---

**根因 (R806d 修复, 2026-07-08):** ms_gw `_relay_stream` (handlers.py) 发送 `Connection: keep-alive` 头, 但用 HTTP/1.0 (BaseHTTPRequestHandler 默认 protocol_version, 未覆盖) 且 **无 Content-Length, 无 Transfer-Encoding:chunked**。客户端 (urllib/http.client, 以及 CC) 无法判定响应边界 → 阻塞等待更多数据或连接关闭, 直到 120s UPSTREAM_TIMEOUT。ms_gw 自己其实 1.1s 就 relay 完了 (metrics status=ok duration_ms=1139 bytes_relayed=1699), 但客户端永远收不到 EOF 信号。

**误导线索 (都修了但不是根因):**
- R806 upstream.py: 429/limit_burst_rate 误判 + cycle 无 backoff → 修了 (is_rate_limit + 3s backoff + key kept warm), 真实有效但不是 CC 中断主因
- R806b: `resp.read(8192)` → `resp.read1(8192)` → 修了 (read(n) 阻塞填缓冲), 但 read1 返回 0B (EOF) 后 break 正常, 也不是根因
- 思考模式: thinking ON 比 OFF 多 ~2s/70 tokens, 不是卡住原因 (用户 msg5 已质疑, 测试证实)

**定位方法 (关键):** ms_gw 的 `_log_metrics` 写**文件** (ms_metrics.{date}.jsonl) 不写 stdout, 所以 `docker compose logs` 看不到。必须 `docker exec <ms_gw容器> tail /app/logs/ms_metrics.*.jsonl` 才能看到 status=ok duration_ms=1139。这一行直接证明 relay 成功, 问题在客户端侧。

**最终修复 (handlers.py _relay_stream):**
```
self.send_header("Connection", "close")  # was: keep-alive
self.close_connection = True
```
让客户端 read-to-EOF, BaseHTTPRequestHandler 在 handler 返回时关 wfile。

**验证:** 直连 ModelScope 0.85s/5chunks → 经 ms_gw 修复后 1.36s/5chunks (修复前 121s 超时)。cc4101 e2e: 修复前 123s 超时 empty_stream, 修复后 3.49s clean message_stop。

**铁律相关:** 本机 (HM1) 只读不改, 所有 patch 打在 HM2 的 /opt/cc-infra/proxy/ms-gw/gateway/。glm5.2 模型未换。见 [[host-roles-and-self-positioning]]。
