# R827 — cc2 buffer total_deadline 锚定 t_start 修补 non-stream 502 穿透

> 时间: 2026-08-05 15:18 CST | 上轮: R826 (NOP, NVCF RemoteDisc 风暴全 buffer 吸收)
> 容器: nv_gw (bind-mount gateway/buffer_stream.py) | 改动量: 1 行 + 7 行注释

## 背景: R821 以来首次出现用户可见 502 穿透 × 2

R826 注入数据显示 30min 窗口 (~14:44-15:14 CST) cc2 (cc4101-primary → glm5_2_nv) per-call
SR 跌至 95.7% (44/46), 出现 2 个 502 穿透用户侧, error=all_tiers_exhausted;buffer_exhausted,
avg_dur=570704ms (~9.5min). R821 以来 5 轮连续 SR=100% 在 R826 末尾断链.

## 根因分析

### 链路铁证 (req=20d7d1b1, 14:46:14 - 14:54:14)

```
14:46:14  请求开始 (t_start)
14:46-14:48  STAGE1 chain first round 全失败 (k1 RemoteDisc, k3 timeout 20s)
14:50:38  STAGE1 CHAIN_FALLBACK 跳过 pexec 2nd round → non-stream execute_request 返败
14:50:38  NV-NONSTREAM-BUFFER-RETRY 启动, BufferStreamSession 创建, t_start=14:46:14 (传进来)
14:50:38  ⚠️ total_deadline = time.time() + 450s = 14:58:08   (line 83 旧逻辑)
          但 cc4101 已在 14:46:14+470s = 14:54:04 总截止
14:50:38-14:54:14  buffer 5 attempts × 90s chain 每个全 EXEC-FAIL, k4/k5/k1/k2/k3 全 RemoteDisc
14:54:14  buffer attempt 5 verdict=None elapsed=515s, LAST-FAIL → WAIT 180s (无人恢复)
14:54:04  cc4101 早已超时关连接, 后续 attempts 都在向关闭 socket 写
~17:14   回 502 给 cc2 (avg_dur=570704ms)
```

### 为什么 R826 之前的 NOP 轮没触发

- R821-R826 5key tier SR=100% (per-attempt 100% 或近 100%), 几乎没有请求走到 non-stream
  execute_request 失败 + buffer retry 这条路径 — path 不被走到, deadline bug 不暴露.
- R826 末尾 NVCF RemoteDisc 风暴加剧中, 出现 STAGE1 chain 全败的请求, non-stream
  buffer retry 路径被触发, 路径上的 deadline 计算错误 finally 浮出水面.

### Bug 本质

`buffer_stream.py:83` 旧代码:
```python
self.total_deadline = time.time() + NVU_BUFFER_TOTAL_DEADLINE_S  # 450s
```

`self.t_start` 是请求最开始时间 (handlers.py:794 `t_start = time.time()`, 请求最入口),
但 `total_deadline` 用的是 `time.time()` (BufferStreamSession 创建时刻). 当 buffer
在请求中途被创建 (non-stream STAGE1 失败后启动 retry / 或非 first-attempt 拦截失败后切到
buffer), `time.time()` 已远晚于 `self.t_start`. buffer 给自己的 450s 预算从晚期时刻算起,
导致总耗时 > cc4101 总预算 470s, CC 已断连, buffer 还在跑空 → 502.

## 修复 (1 行)

`buffer_stream.py:83` →
```python
# R827: deadline 锚定 t_start, 非创建时刻. ... (注释略)
self.total_deadline = self.t_start + NVU_BUFFER_TOTAL_DEADLINE_S
```

效果:
- 20d7d1b1 等场景下 buffer deadline = t_start + 450s = 14:53:44, 总在 cc4101 470s 截止
  (14:54:04) 前结束, 有 20s 安全余量.
- 流式 first-attempt 路径 (t_start ≈ time.time()) 行为不变.
- 所有 3 处 BufferStreamSession 创建点 (handlers.py:914/942/1009/1911) 都传 t_start,
  修复对所有路径生效一致.

## 验证

```
$ python3 -m py_compile /tmp/buffer_stream_test.py    → py_compile OK
$ docker compose restart nv_gw                         → Container nv_gw Started
$ curl localhost:40006/health                           → ok, 5 keys, glm5_2_nv in pexec_models
$ curl localhost:4101/health                            → ok, primary=glm5_2_nv
$ docker ps                                            → nv_gw Up 11 seconds
$ docker exec nv_gw python3 -c "import gateway.buffer_stream as b, inspect;
    print('R827' in inspect.getsource(b.BufferStreamSession.__init__))"
                                                       → True
```

R813 chain_full_retry 仍就位, 未触碰 fallback / ms_gw / key binding.

## 风险评估

- **改动范围**: 仅 buffer_stream.py:83 一行 + 注释, NVU_BUFFER_TOTAL_DEADLINE_S=450
  不变, 只改时间基准从 `time.time()` (创建时刻) 到 `self.t_start` (请求开头).
- **影响场景**: 流式 first-attempt (line 1009) 第一次创建时 time.time()≈t_start, 行为
  完全不变. 仅 non-stream STAGE1 失败后启动 (line 942) 和多次 attempt 重试场景被修正.
- **回归风险**: 若 t_start 在某调用路径被错误传入 (非请求开始时刻), deadline 会算错.
  已审查所有 4 处调用点, 都用请求最入口的 t_start, 一致.

## 参数快照

- nv_gw: NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_BUFFER_MAX_RETRIES=5,
  NVU_BUFFER_TIMEOUT_STAIRS=[90,90,90,90,90], NVU_BUFFER_TOTAL_DEADLINE_S=450,
  NVU_DISABLE_MS_FALLBACK=1, UPSTREAM_TIMEOUT=90s
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400,
  PRIMARY_UPSTREAM_MODEL=glm5_2_nv, FALLBACK_UPSTREAM_MODEL=glm5_2_ms (历史残留, SR 99%+ 不触发)
- deadline 链: 90s × 5 = 450s buffer (anchored t_start) < 470s cc4101 < 600s API < 900s idle

## 下一步

- 等下个 30min 窗口验证 502 穿透是否消除 (期望 0).
- 若 NVCF RemoteDisc 风暴持续 per-attempt SR ~67%, 检查是否需要补加 chain attempt 间
  backoff (已有 NV-BUFFER-BACKOFF 5/10/15s 三档, 但实际 elapsed 显示有些 attempt 1 仍耗
  了 333s, 表明 chain 内部多 key 串行尝试无单 key 超时封顶 — 下轮可查 _try_glm52_mode_chain).

## 文件

- 修改: `/opt/cc-infra/proxy/nv-gw/gateway/buffer_stream.py:83` (1 行 + 8 行注释)
- 备份: `buffer_stream.py.bak.R827`
