# R1774 — HM2 nv_gw+cc4101 mid-response 崩溃根治: wire graceful end + breaker 时间窗语义

> cc2 session `2c248bab` 在 2026-07-18 14:15:22 +0800 崩溃(CC 报 "API Error: Server error
> mid-response. The response above may be incomplete.")，暴露 R1719/R1716 的 breaker 链"检测+记录
> 都工作但永不收敛"的系统性设计缺陷。本轮三层根治，HM2 only。

## 链路
```
cc2 → cc4101(4101, 透传 /v1/messages) → nv_gw(40006, glm5_2_nv) → NVCF
                                  ↘ ms_gw(40007, glm5_2_ms) [breaker OPEN 后兜底]
```

## 改前数据(2026-07-18 14:15:22 崩点 + 全日趋势)

### 崩点 req=d36ae094 (同一秒两条日志对上)
- nv_gw `[14:15:22.6] NV-ANTH-BREAKER-FAIL err=zombie_empty_completion state=('CLOSED',1,0) req=d36ae094`
  (path=/v1/messages, mapped=glm5_2_nv, upstream=nvcf_pexec, in_tok=28565, out_tok=313,
  ttfb=14164, duration=14172, error_type=zombie_empty_completion, fallback_occurred=f)
- cc4101 `[14:15:22.6] CC4101-UPSTREAM-ERROR-SEEN req=04955d27 ttfb=14195ms`
  (passthrough 探针 b"event: error" 命中, record_primary_failure 被调用)

### 全日 breaker 失效证据(两层都"记录但不收敛")
- nv_gw: 22 次 NV-ANTH-BREAKER-FAIL **全是 state=('CLOSED',1,0)** —— fail_count 永 0↔1 振荡
- cc4101: 10 次 CC4101-UPSTREAM-ERROR-SEEN, `_fail_count=0` 永远到不了 N=8
- cc4101: 34 次 STREAM-STALLED(376-543s!), stall 路径有 record_primary_failure 但同样被中间成功重置
- R1716 peek barrier: NV-PEEK-OK=421 / NV-PEEK-SOFTFAIL=15 —— 崩点 ttfb=14195(已过 peek),
  313 token 后才 zombie, peek 早退出兜不住

## 根因(三层设计缺陷叠加)

### 缺陷 1: breaker 阈值+成功重置语义 → 永远 CLOSED,死循环不收敛
`record_nv_failure`/`record_primary_failure` 是"连续 N 次失败才 OPEN, 成功归 0"。
glm5_2_nv 成功率 >80%, 两次失败之间必有成功把 _fail_count 重置归 0, 永远到不了 N(15/8)。
**R1719 的"累积保后续"在当前成功率下数学上不可能收敛。** 这是"彻底失控"的真根因。

### 缺陷 2: 当前请求 wire 发 event: error → CC SDK 当致命错中断 session
nv_gw zombie 后 `converter.finish(zombie=True)` 发 anthropic `event: error` SSE。
cc4101 透传给 CC。**CC SDK 把 event: error 当致命错**, 合成 "API Error mid-response" 中断 session,
不重试当前请求。即便 breaker 工作, 当前请求的 session 必崩。R1719 备忘"当前中断可接受"被实测推翻。

### 缺陷 3(已在 R1719 存在, 非本轮): R1716 peek 只把关首字节前
崩点是流到一半才 zombie, peek 早退出。本轮靠 breaker 收敛 + wire graceful end 兜住, 不再改 peek。

## 改动(三层, 用户已确认全做)

### 修复 A: wire 不再发 event: error — 已有内容时发 graceful end(治"当前请求崩")
- `nv_gw/gateway/format/oai_to_anth.py` `finish()`: 新增 `flushed_content_chars` 参数。
  zombie + flushed_content_chars>0 → 不发 event: error, 改发 message_delta(stop_reason=
  pending_stop_reason 或 end_turn)+message_stop, CC 把已收内容当完整响应收尾不中断。
  零内容 zombie 保留原 event: error(无内容可收尾, 必须让 CC 重试)。
- `nv_gw/gateway/handlers.py` `_stream_openai_to_anth` finish() 调用处: 传 `flushed_content_chars=content_chars`。

### 修复 B: breaker 改"时间窗失败率"语义, 成功不重置(治"永 CLOSED")
- `nv_gw/gateway/nv_breaker.py`: 加 `_fail_timestamps` deque(W=300s), `record_nv_failure` push+清理过期,
  窗内失败数>=N 则 OPEN; `record_nv_success` **不再清空 deque**(只清 OPEN 的 _open_until,
  只有 HALF_OPEN probe 成功才清)。新增 `NVU_BREAKER_WINDOW_S=300`。
- `cc4101/gateway/circuit.py`: 镜像改动, 加 `CC4101_BREAKER_WINDOW_S=300`。
- compose env: `NVU_MS_FALLBACK_FAIL_THRESHOLD` 15→5; `CC4101_PRIMARY_FAIL_THRESHOLD` 8→3。

### 修复 C: cc4101 stall 路径加观测日志(stall 记 failure 本已存在)
- `cc4101/gateway/stream.py` socket.timeout 分支: `record_primary_failure()` 已存在(R1719 前就有),
  本轮加 `CC4101-STREAM-STALL-FAIL` 日志, 24h 观测 stall 是否真正累积(配合修复 B 不再被重置)。

## 参数表

| 参数 | 改前 | 改后 | 位置 |
|---|---|---|---|
| NVU_MS_FALLBACK_FAIL_THRESHOLD | 15 | 5 | compose env (nv_gw) |
| CC4101_PRIMARY_FAIL_THRESHOLD | 8 | 3 | compose env (cc4101) |
| NVU_BREAKER_WINDOW_S | (无) | 300 | nv_breaker.py 默认 |
| CC4101_BREAKER_WINDOW_S | (无) | 300 | circuit.py 默认 |
| NVU_MS_FALLBACK_SKIP_S | 30 | 30 | 不变 |
| CC4101_PRIMARY_SKIP_S | 30 | 30 | 不变 |

## 部署+验证(HM2)

1. 备份 5 文件(oai_to_anth.py / nv_breaker.py / circuit.py / stream.py / handlers.py + compose)。
2. python 脚本精确补丁(避免 heredoc 引号地狱), py_compile 4 文件容器内全 OK。
3. `docker compose up -d nv_gw cc4101` → 两容器 Recreated+Started。
4. 三看验证(记忆 nv-gw-bindmount-edit-needs-restart):
   - StartedAt: nv_gw=07:30:23Z, cc4101=07:30:24Z(刚才) ✓
   - /health: 两容器 ok ✓
   - 新阈值: nv THRESHOLD=5 WINDOW=300 state=CLOSED/0/0; cc1 THRESHOLD=3 WINDOW=300 CLOSED/0/0 ✓
5. 单元逻辑验证: 容器内连调 4 次 record_nv_failure → state=('CLOSED',4,0); record_nv_success 不重置 → 仍 4。
   cc4101 同理 3 次 failure 后 success 不重置。✓
6. E2E: curl cc4101 /v1/messages 流式 → 完整 anthropic SSE 序列(message_start→content_block_start
   →delta×N→content_block_stop→message_delta→message_stop)正常返回 ✓
7. 启动日志已见 R1716 fallback 工作: `NV-ANTH-COLLECT-SOFTFAIL → NV-MS-FB-OK`(req=9ed81f16, 3311ms)✓

## 预期效果

- 当前请求不崩: zombie 有内容时 CC 不再收 event: error, 把已收内容当完整响应(缺陷 2 治)。
- 后续收敛: 5min 内 5 次(nv)/3 次(cc1)失败 → breaker OPEN → 30s 走 ms → 不死循环(缺陷 1 治)。
- stall 兜住: 34 次 stall 终于累积 breaker(配合缺陷 1 修复, 不再被成功重置)。
- 目标: 24h 内 mid-response 中断次数 → 0; breaker 出现 OPEN 状态(说明收敛机制工作)。

## 不改的东西

- 不碰 config / upstream / pexec / agents 配置。
- 不改 R1716 peek barrier(治首字节前, 有效)。
- 不改 big_input_breaker(治 >250k, 独立维度)。
- 不改 R1719 catch-all 块本身(检测+记录正确, 只是阈值/语义不够)。
- 不改 HM1(铁律), HM1 cc4101 仍缺 format/, 待 HM2 稳定后另轮同步。

## 24h 观测点

- `grep NV-ANTH-BREAKER-FAIL nv_proxy.YYYY-MM-DD.log` 的 state 出现 ('OPEN',*,>0) 或 fail_count>1。
- `grep CC4101-STREAM-STALL-FAIL` 日志出现且 breaker 累积。
- `grep CC4101-UPSTREAM-ERROR-SEEN` 的 circuit_state 累积过 3。
- cc2 session mid-response 中断次数(目标 0)。
