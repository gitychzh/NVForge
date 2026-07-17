# R1674: cc4101 collect 路径补 recv-fallback + nv_gw R1673 breaker 首次即触发

**状态**: 已部署 HM2, 生产日志验证 A 生效. 只改 HM2 (R1648 系列豁免铁律).
**提交**: (本轮 commit)

## 背景 (R1673 部署后深挖 "{ Request timed out}" 根因)

R1673 big_input_breaker 部署后, 用户报告远程 CC 又出现 `{ Request timed out}`。全镜像 grep 确认:
**`{ Request timed out}` 是 CC 客户端自身 (claude code CLI) 发出的** — nv_gw / ms_gw / cc4101
源码 + site-packages 都没这个字符串。CC 在 `API_TIMEOUT_MS=600000`(10min) 内对单个请求等不到
完整响应时打印此本地超时提示并自动重试。

### 根因链 (16:57:00 真实复现)
1. CC 发 nonstream 大请求 (72msg 30tools, 序列化 **input_chars=294929**) → cc4101 → nv_gw
2. R1673 breaker 还 CLOSED: 重启后状态清零, FAIL_N=3 需连续 3 次 hang 才 OPEN, 这是首次大 input,
   走了正常 nv 链 (R1673 fast-fail 没生效)。
3. NVCF glm5.2 对 294929 超大 input 系统性 200-then-hang (R1672 根因)。
4. nv_gw FULL_BUFFER (R1627) 缓冲期间不 flush, cc4101 nonstream `resp.read(8192)` 阻塞等首字节。
5. nv_gw first-byte deadline 45s 命中 (16:57:50), 发 content_filter error chunk 给 cc4101 —
   **为时已晚且读不到** (见 6)。
6. **cc4101 collect 路径致命缺陷**: per-read 短轮询超时后 `http.client` 的 `fp` 进入 "timed out
   object" 崩坏状态, `resp.read()` 永远抛 OSError。**`collect_stream_to_anth` (L648) 对此只 `continue`,
   没有 `stream_to_anth` (L258) 那样的 `sock.recv(MSG_PEEK)` recv-fallback 兜底** → read 死循环,
   stall-watcher 救不了 (ttfb 未记录没启动)。
7. CC 等 ~62s (16:57:00→16:58:01) 无响应 → CC 自超时 `{ Request timed out}` → 改 stream 重试
   (stream 路径有 recv-fallback, 能完成)。

**两个独立问题**:
- 主因 (R1673 已修但首次未生效): breaker 需 3 次 hang 才 OPEN, 重启后首次大 input 仍走死循环。
- cc4101 缺陷 (新发现, 未修): collect 路径缺 recv-fallback, http.client fp 崩坏后 read 死循环。

## 改动 (A+B+C, 只 HM2)

### A (治本-cc4101): collect_stream_to_anth 补 recv-fallback
`/opt/cc-infra/proxy/cc4101/gateway/stream.py` (容器内 `/app/gateway/stream.py`, bind-mount).
镜像 `stream_to_anth` (L258) 早有 R1415 recv-fallback (`sock.recv(MSG_PEEK)` 看 socket buffer 有无
已到达但 http.client 读不出的数据, 有则 `recv` 取出当 chunk), **collect 路径 (L648) 漏修**。

补丁: collect 的 `except OSError` 分支, 把裸 `continue` 换成同款 recv-fallback 逻辑 (try PEEK →
有数据则 recv 取出赋值 chunk, 落到 except 后的正常 chunk 解析; 无数据才 continue 让 stall-watcher 判)。

**坑1 (部署)**: cc4101 bind-mount 路径是 `/opt/cc-infra/proxy/cc4101/gateway`, 不是
`/opt/cc-infra/proxy/cc-adapter/gateway` (cc-adapter 是镜像名, 有份 stale 副本)。先写错路径,
容器内 md5 没变 → 改正后容器内 md5 同步 (796bb8...)。

### B (治标-nv_gw): R1673 breaker FAIL_N 3→1
`docker-compose.yml` `NVU_BIG_INPUT_FAIL_N=1` (R1673 原是 3)。重启后首次大 input hang 即触发 OPEN,
下次大 input 直走 ms_gw (~9s) 而非等满 45s deadline 死循环。风险: 正常偶发大 input 1 次 hang 即
OPEN 180s 内直走 ms (ms 是 glm5.2 同系, 质量近似, 可接受)。

### C (治本-nv_gw): FULL_BUFFER + first-byte deadline 协同
**核查后确认 nv_gw 端已正确**: first-byte deadline 命中时设 `error_type=stream_first_byte_timeout` →
break → L1508 `buffer_chunks is not None and error_type` 跳过 FULL_BUFFER flush (丢弃缓冲) →
L1540 `_r1627_should_emit_cf=True` → 同步 `self.wfile.write(err_chunk); self.wfile.flush()` 发
content_filter error chunk 给下游。无需改 nv_gw。真正的读不到缺口在 cc4101 端 (A 已修)。

## 验证 (HM2, 改后生产日志)

17:22:52.5 真实 CC 大请求 (msgs=82 tools=30) 触发 nv_gw stream_no_content_gap deadline,
nv_gw 发 content_filter error chunk:
```
17:22:42.5 [DBG] read got 2445b tail=...[DONE]              ← 正常 read 成功
17:22:52.5 [DBG] recv-fallback got 93b tail=...content_filter...[DONE]  ← A 的 recv-fallback 触发!
17:22:52.5 [ZOMBIE-CONTENT-FILTER] emitting api_error so Claude Code retries (req=ecbab8bd)
17:22:52.6 [REQ] ... cc_stream=False msgs=82 tools=30      ← CC 立即重试 (+0.1s)
```
**A 前**: cc4101 `resp.read` 永久卡 (timed-out-object fp 崩坏), CC 等 62s → `{ Request timed out}`。
**A 后**: recv-fallback 同秒读出 content_filter chunk, 同秒发 api_error, CC +0.1s 即重试。
**死循环在 cc4101 层根治。**

## 参数表 (最终)

| 参数 | 值 | 来源 |
|---|---|---|
| NVU_BIG_INPUT_FAIL_N | 1 (R1673 原 3) | B, 首次即触发 |
| NVU_BIG_INPUT_THRESHOLD | 250000 | R1673 |
| NVU_BIG_INPUT_COOLDOWN_S | 180 | R1673 |
| NVU_MS_FALLBACK_ENABLED | 1 | R1673 副作用激活 R1648c |
| cc4101 collect recv-fallback | 补 (镜像 stream_to_anth L258) | A |

## 风险与回退
- **A 回退**: 恢复 stream.py.bak.R1674 (collect 回到裸 continue, fp 崩坏时死循环回归)。
- **B 回退**: `NVU_BIG_INPUT_FAIL_N=3` (更保守, 但首次大 input 仍走死循环, 靠 A 兜住 cc4101 端)。
- **HM1 未同步**: 本轮只改 HM2。

## 后续
- R1648e: cc4101 纯透传 (删 R1643 fallback + breaker; handlers 转发到 nv_gw:40006/v1/messages
  主 + ms_gw:40007/v1/messages 备; 启用 NVU_MS_FALLBACK_ENABLED=1 长跑)。
- R1648f: 切换 + ≥6h 长跑, 更新 compose + memory, HM1 同步。
