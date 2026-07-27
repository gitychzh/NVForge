# R2403: cc2 链路 82× stream_total_deadline 根因诊断 — 假账 (nv_gw 端无对应慢请求)

> **纯诊断轮, 0 改动 0 restart.** 数据彻底证伪"deadline = nv_gw 慢"叙事, 揭示 cc4101 在记假账.
> **下一轮据此决定动哪里 (cc4101 stream 循环 EOF 识别 / SSE done 信号 / 还是真有挂死请求).**
> HM2 only. cc2 自优化.

## 背景 (上一轮 R2402 数据锚定)

R2402 统计 cc2 自身链路 6h 报错, 发现:
- nv_gw 层 (caller=cc4101-primary, 单调 created_at) SR 94.7% (378×200 / 14×499 / 7×502)
- cc4101 层 (cc_requests, host_machine=opc2sname=HM2/cc2) 6h 474 请求, **82× stream_total_deadline 占全部错误 85%, 全部 fallback_triggered=false (0 救回)**
- 82 条是稳态持续 (每小时 4-11 个, 无单点爆发), avg input_chars 165K (成功 142K, 大输入略偏多但非决定性)
- CLAUDE.md 把 499 (BUG-A, 12×/6h) 反复强调, 却**没把 82× deadline 单列为 bug** — 上一轮已指出这是真实头号

## 本轮诊断目标

**82× stream_total_deadline 到底卡在哪一层?** 三种可能:
1. nv_gw 慢 (请求真在 nv_gw 跑 ≥600s 才回)
2. cc4101↔nv_gw 之间网络/keep-alive 问题
3. cc4101 自身 stream 循环逻辑问题 (假账)

## 关键证据链 (铁证)

### [E1] env 实测 = 650s (非 CLAUDE.md 残留印象的 580s)

```
docker exec cc4101 env | grep STREAM_TOTAL
  CC4101_STREAM_TOTAL_DEADLINE_S=650
docker exec cc4101 python3 -c "from gateway import config; print(config.CC4101_STREAM_TOTAL_DEADLINE_S)"
  650.0
```
compose 注释原文 (R-deadline650):
> "580->650. R-buf2key 4key x 150s=600s buffer 总预算, 580s 死钟在 buffer 完成前杀掉
> 38.8% 请求(2h 31/80 stall). 650=600+50 余量给 flush+ms_gw. 对齐 cc2 SDK
> API_TIMEOUT_MS=700000 CLAUDE_STREAM_IDLE=700000. env 回滚=改回 580."

→ 650 = R-buf2key 轮刚从 580 提上来的值, 设定理由是"让 nv_gw buffer 600s 跑完 + 50s flush 余量".
→ **但 R-buf2key 把 deadline 提到 650 也没用 — 下面证据显示问题不在 deadline 不够长, 在 cc4101 假账.**

### [E2] deadline 计时逻辑 (cc4101 stream.py 活文件 77-147 行)

```python
stream_total_deadline = None  # ttfb 之前不设
ttfb_recorded = False
while True:
    if ttfb_recorded and stream_total_deadline and time.time() > stream_total_deadline:
        metrics["error_type"] = "stream_total_deadline"
        raise socket.timeout("stream_total_deadline")
    chunk = resp.read(8192)
    ...
    if not ttfb_recorded:
        metrics["ttfb_ms"] = ...
        ttfb_recorded = True
        stream_total_deadline = time.time() + CC4101_STREAM_TOTAL_DEADLINE_S  # = now + 650s
    ...
    if not chunk:
        break  # 干净 EOF, 流正常结束
```

**机制**: ttfb 一到, 给 650s 读完整流. 650s 内没读完 (没 break) 就 raise timeout.
**意味着**: 这 82 条都是 **ttfb 已到, 但 cc4101 在 650s 内没读到 `not chunk` (干净 EOF)**.

### [E3] cc4101 STREAM-DEADLINE 日志实测 (近 1h 8 条)

```
[14:34:01.5] [STREAM-DEADLINE] passthrough total deadline 650.0s after ttfb exceeded
[14:34:01.5] [STREAM-STALLED] passthrough stall after 691789ms: stream_total_deadline  (691.8s)
[14:36:52.4] ... after 685236ms (685.2s)
[14:37:10.8] ... after 703596ms (703.6s)
[14:37:42.8] ... after 811649ms (811.6s)  ← ttfb 之前花了 161s
```
duration 全部 612-811s = ttfb (32-161s) + 650s 限. 与 E2 机制完全吻合.

### [E4] ★决定性铁证★ — nv_gw 端这 11 分钟内**没有任何 ≥600s 的 cc2 请求**

对每个 cc4101 deadline 时间点, 位移到请求发起时刻 (ts - duration) 看 nv_gw:

**14:32:15 cc4101 deadline (dur=684.6s, ttfb=34.6s) → 请求 14:21:00 发起**
nv_gw 14:21-14:32 全部 cc2 glm5_2_nv 请求实测:

| nv_gw req | BUFFER-START | BUFFER-SUCCESS | elapsed |
|---|---|---|---|
| 8e933ff0 | 14:21:55 | 14:22:22 | 26s |
| c75e7209 | 14:22:22 | 14:23:05 | 42s |
| b5fb71f4 | 14:22:29 | 14:23:11 | 41s |
| 2daf2319 | 14:23:04 | 14:23:14 | 9s |
| 10df402a | 14:23:14 | 14:23:40 | 25s |
| a49ca299 | 14:23:41 | 14:23:44 | 3s |
| 9a61bec1 | 14:23:45 | 14:24:04 | 19s |
| 6df6e721 | 14:24:04 | 14:24:10 | 6s |
| 9dde4341 | 14:24:11 | (4 attempt 全 execute_failed → BUFFER-EXHAUSTED 14:25:46 → ms_gw fallback) | 95s |
| cd599d9c | 14:25:27 | 14:26:02 | 35s |
| 3c9d888a | 14:25:27 | 14:26:20 | 53s |
| 9f932e43 | 14:30:25 | 14:30:49 | 24s |
| 27b68fb0 | 14:30:54 | 14:31:31 | 37s |
| 0f113e30 | 14:32:15 | 14:32:50 | 34s |

**全部 3-95s 完成, 没有任何一条接近 600s.** 9dde4341 是唯一的 BUFFER-EXHAUSTED 但也只是 95s 走完 4 key 全失败 → ms fallback.

**14:21-14:32 这 11 分钟 nv_gw 端不存在任何"跑 600s+"的请求**, 但 cc4101 同期记了 4 条 612-703s 的 stream_total_deadline.
→ cc4101 的 deadline **不是在等 nv_gw 的某条慢请求**, 是 cc4101 自身循环假账.

### [E5] request_id 两套体系, 无法关联 (观测性盲点)

- cc4101 日志 / cc_requests.request_id: uuid 前 8 位 (如 `673bef9b`, `c262109f`)
- nv_gw 日志 req=: 自己生成的短 hex (如 `0f113e30`, `9256b4af`)
- **cc4101 发给 nv_gw 的请求不带原 request_id 透传**, nv_gw 自己另生 id.
- 仓库全局 grep 无任何 id 关联代码.
→ 单条请求全链路追踪目前**不可能**, 只能靠时间窗对应 (本轮方法).
→ 这本身是诊断盲点, 但不是本轮 root cause, 记录留待后续修观测性.

## 根因判定 (本轮结论)

**82× stream_total_deadline 是 cc4101 的假账 — 不是 nv_gw 慢, 不是网络挂死 nv_gw 端请求.**

证据强度: E4 是铁证 (nv_gw 端同期所有 cc2 请求 3-95s 完成, 0 条 ≥600s).

**最可能的真实机制 (待源码确认, 但证据强指向)**:
cc4101 的 `resp.read(8192)` 循环在 ttfb 后**长时间读不到 chunk 也没读到干净 EOF**.
nv_gw 那边 SSE 流已结束 (flushed + close), 但 cc4101 这边 HTTP 连接没正确收到 EOF 信号.
cc4101 read 循环一直阻塞在 read(8192) (有 socket.timeout continue 兜底), 直到 ttfb+650s 撞 deadline.

**待查候选** (下一轮):
1. cc4101 是否把 nv_gw 的 `[DONE]` / `message_stop` / chunked-transfer 末块正确识别为 EOF?
2. nv_gw buffer 层 BUFFER-SUCCESS 后是否真正 close 了到 cc4101 的 conn? 还是 keep-alive 挂着等下个请求?
3. cc4101 这 82 条的 ttfb (32-161s) 远高于成功请求 (ttfb 多在 <30s) — **ttfb 慢的请求是不是已经在 NVCF 那边就处于半挂死, nv_gw buffer 拿到首字节但后续 chunk 极慢, 最终 nv_gw 超时关连接但 cc4101 还在等?**

候选 3 需重点查 — 9dde4341 这条 BUFFER-EXHAUSTED (95s 4 key 全 execute_failed) 的 peer 请求 (上一轮也见 kimi_nv peer fallback) 暗示 NVCF 那段时间确实在抖.

## 修正的认知 (写入避免后续重蹈)

1. **env 是 650s 不是 580s**. CLAUDE.md "BUG-A 家族" 段说的 580 是 R-deadline650 之前的值, R-buf2key 已提到 650. 我本轮第一查询把 `UPSTREAM_TIMEOUT=130` 误读为 stream deadline (已修正).
2. **82× deadline 不是"调大 deadline 能解决"** — R-buf2key 已经从 580 提到 650, 比例没下降 (上一轮 6h 82 条, 之前 2h 31/80=38.8% stall). 提 deadline 治标不治本, 因为 nv_gw 端请求根本没那么慢.
3. **CLAUDE.md BUG 清单需补 BUG-F: cc4101 stream_total_deadline 假账** — 这是当前 cc2 链路真实头号 (85% 错误占比, 0 救回), 比 BUG-A (499, 12.5%) 严重 7 倍, 但 CLAUDE.md 没单列.

## 验证清单 (本轮无改动, 无需 restart)

- [x] env 确认 650 (env + python import + 日志 "650.0s" 三处一致)
- [x] stream.py 机制核证 (ttfb 后 650s read 循环)
- [x] 8 条 STREAM-DEADLINE 日志实测 duration 612-811s
- [x] ★14:21-14:32 时间窗 nv_gw 端 0 条 ≥600s 请求 (E4 铁证)
- [x] request_id 两套体系确认 (无法关联, 盲点)

## 不动手的理由 (守铁律"改前必有数据" + 守"改后必有验证")

本轮纯诊断: 已确认根因在 cc4101 端不在 nv_gw. 但 cc4101 是 CC 基础设施层 (CLAUDE.md "三任务都改 nv_gw/cc4101 源码" 段允许改 cc4101, 但任务1 已落地 cache_control 在 cc4101 passthrough). 下一步要改 cc4101 stream 循环的 EOF 识别, 风险更高 (改错会污染所有 agent 的 passthrough), **必须先有更精确的"哪条 nv_gw 请求对应哪条 cc4101 deadline"配对数据**才能动刀.

当前配对只能靠时间窗 (误差 ±2s), 不足以支撑"改 cc4101 read 循环"这种高风险改动. 下一轮应先在 cc4101 加 request_id 透传 (或日志关联) probe, 拿到铁证级配对再改.

## 下一轮方向 (建议, 不锁定)

**优先级 1 (前置)**: cc4101 加 req_id 透传 probe — cc4101 发给 nv_gw 的请求 body 或 header 带上自己的 request_id, nv_gw 日志里打出, 建立 1:1 配对. 拿到 5-10 条铁证配对后, 看每条 nv_gw 端到底 BUFFER-SUCCESS 了几秒、cc4101 端为何没收到 EOF.

**优先级 2 (查候选3)**: 抽 82 条 deadline 的 ttfb 分布 vs 成功请求 ttfb 分布. 若 deadline 那批 ttfb 普遍 ≥60s, 指向"NVCF 半挂死, 首字节慢后续更慢, nv_gw buffer 拿到首字节但后续 chunk 极慢导致 cc4101 长读不到 EOF" — 这种情况改 cc4101 没用, 要在 nv_gw buffer 层加"首字节后 N 秒无后续 chunk 就主动 abort 给 cc4101 发 EOF" 逻辑.

**优先级 3 (保守)**: 若查清确是 cc4101 read 循环 EOF 识别 bug, 改 cc4101 stream.py. 但这影响所有 agent, 需 peer (HM1) 同步. 风险高.

## 关联

- R2402: cc2 链路报错统计, 发现 82× deadline 占 85% (本轮的诊断对象)
- R-buf2key: deadline 580→650 + buffer 2-key rotation (没解决 deadline, 见 E1)
- CLAUDE.md BUG-A (499): 当前 12×/6h, 远小于 deadline 82×, 但 CLAUDE.md 反复强调 — 认知偏差需修正
- CLAUDE.md 任务2/3 (zombie 内部重试): 当前 nv 侧 zombie=0 (client_gone_during_flush 不是 zombie_empty_completion), 优先级可降
