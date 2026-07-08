# R818: HM2 ms_gw 流式中断真正根因 — HTTP/1.0 keep-alive 边界不可判定

> 承接 R817 (R816 settimeout 效果验证 + dsv4p NOP). 远程 HM2 8轮定时优化 R5.
> 铁律: 改前有数据, 改后有验证, 改动 ≤5 处.

## 根因 (区别于 R816)

R816 修的是 `settimeout` 因 NameError 失效 → read1 阻塞到默认超时 (p95 161s)。
本轮修的是**另一个独立根因**: ms_gw `_relay_stream` 给流式响应发了
`Connection: keep-alive` 头, 但用 HTTP/1.0 (BaseHTTPRequestHandler 默认
protocol_version, 未覆盖) 且**无 Content-Length、无 Transfer-Encoding: chunked**。
客户端 (urllib / Claude Code) 无法判定响应边界 → 阻塞等待更多数据或连接关闭,
直到 120s `UPSTREAM_TIMEOUT` → CC 中断。

**关键误导**: ms_gw 自己其实 1.1s 就 relay 完了 (metrics `status=ok
duration_ms=1139 bytes_relayed=1699`), 但客户端永远收不到 EOF 信号。
而 `_log_metrics` 写**文件** (`/app/logs/ms_metrics.*.jsonl`) 不写 stdout,
`docker compose logs` 看不到 — 必须进容器 `tail /app/logs/ms_metrics.*.jsonl`
才看得到。这正是前几轮没揪出根因的原因。

## 定位过程

1. 直连 ModelScope (stream, reasoning_effort=none): 0.85s / 5 chunks (基线正常)
2. 经 ms_gw 同请求: **121s 超时** (empty_stream_response)
3. ms_gw 日志只有 `MS-OK-STREAM first=1699B`, 无 STREAM-EOF/ERR
4. 进容器 tail ms_metrics 文件 → `status=ok duration_ms=1139 bytes_relayed=1699`
   → **relay 成功, 问题在客户端侧**
5. 加 R806c debug log (READ1-ENTER/EXIT) → read1 返回 0B (EOF) 后 break 正常
   → relay 确实完成, 客户端没收到边界
6. 查响应头: `Connection: keep-alive` + HTTP/1.0 + 无长度 → 边界不可判定, 确认根因

## 改动 (3 处, 共享源码外科式 patch)

### handlers.py `_relay_stream`
- **R806d (根因)**: `Connection: keep-alive` → `Connection: close` +
  `self.close_connection = True`. 客户端 read-to-EOF, BaseHTTPRequestHandler
  在 handler 返回时关 wfile。
- **R806b**: `resp.read(8192)` → `resp.read1(8192)` (read(n) 阻塞填缓冲,
  read1 有数据即返回; 真实有效但非主因)。
- **R806c**: relay 前 `resp.fp.raw._sock.settimeout(UPSTREAM_TIMEOUT)` 保险
  (R816 settimeout 修复后的二次兜底, 无害)。

### upstream.py `_check_ms_stream_first_chunk` + cycle
- **R806**: 加 `resp_status` 参数, 非常 200/429/limit_burst_rate 识别为
  `is_rate_limit` → cycle 分支遇之 `time.sleep(3.0)` backoff + **key kept warm**
  (不 mark_cooling, 不换 key 扩散限流)。调用点传 `resp.status`。
  MSResponseCheck 加 `is_rate_limit` + `backoff_s` 字段。
  (真实有效: 429 不再误判为 stream_no_data 扩散冷却, 但非 CC 中断主因)

## 验证

| 路径 | 修复前 | 修复后 |
|---|---|---|
| 直连 ModelScope (stream) | 0.85s / 5 chunks | 0.85s / 5 chunks (基线) |
| 经 ms_gw (stream, think off) | **121s 超时** | **1.36s / 5 chunks** |
| cc4101 e2e (NV 挂→fallback ms) | 123s 超时 empty_stream | **3.49s clean message_stop** |
| cc4101 e2e (含 429 backoff) | 124s 超时 | 17.45s clean (429 backoff 占主要) |

ms_gw metrics 文件确认 relay 稳定 `status=ok`。429 限流期 R806 backoff 正常
触发 (MS-RL-BACKOFF 日志), key kept warm, 不再级联冷却。

## 思考模式影响 (回应用 msg5 评估请求)

A/B (ms_gw non-stream, "reply OK"):
| 模式 | 延迟 | reasoning | completion tokens |
|---|---|---|---|
| thinking ON (默认) | 6.53s | 286 chars | 70 |
| thinking OFF (reasoning_effort=none) | 4.39s | 0 | 1 |

trivial 提示下 thinking 多 ~2s/70 tokens (主要 reasoning_content)。不是卡住
原因 (R1 无 thinking 仍 120s 超时已证)。未改 thinking 逻辑 (铁律: agent-owned)。

## 当前链路状态

- glm5_2_nv: 0% (NVCF func 3b9748d8 仍 DEGRADED, R814 短路生效)
- ms_gw: 100% ok, stream p95 ~1.4s (R818 修复后, 远优于 R816 的 17.7s)
- cc4101 fallback: NV 502 → ms_gw 3.5s clean, 无中断

## 下轮 R819 候选 (8 轮 R814-R821, 已完成 R814-R818, 剩 R819-R821)

1. ms_gw 长期稳定性观测 (R818 keep-alive→close 改动后 p95 长期曲线)
2. dsv4p_nv empty-200 持续观测 (R817 频率上升是否持续)
3. glm5_2_nv DEGRADED 周期性探测是否恢复

角色见 [host-roles-and-self-positioning], 铁律见 [nvcf-testing-methodology],
共享源码外科式 patch 见 [shared-source-cross-host], 8 轮设计见 [r815-summary].
