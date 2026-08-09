# R1719 计划: nv_gw anth 路径 mid-stream 软挂记 breaker + cc4101 识别 api_error 标失败 (breaker 累积保后续)

> R1716 的 peek barrier 只把关"首字节前"软挂, 200 落 cc4101 后的 mid-stream 软挂仍兜不住.
> 用户要求"尽最大可能不让远程 CC 中断". 用户确认方案深度: breaker 累积保后续请求 (当前请求中断可接受).
> 铁律: 只改 HM2. 不碰 HM1.

## 现场 (R1716 部署后, 3h HM2 glm5_2_nv nv_requests)

```
error_type                 | upstream_type | c  | avg_s
stream_no_content_gap      | nv_integrate  | 17 | 151.0   ← 200 后中途挂, peek 拦不住
stream_total_deadline      | nv_integrate  |  3 | 225.2
zombie_empty_completion    | nv_integrate  |  3 | 17.0
zombie_empty_completion    | nvcf_pexec    |  3 | 5.7
stream_first_byte_timeout  | ms_fallback   |  1 | 64.5     ← R1716 peek 触发, ms 也失败
stream_first_byte_timeout  | nv_integrate  |  1 | 63.1
```

R1716 peek barrier 实际触发 (日志确认):
- NV-PEEK-OK 多次 (健康续流) ✓
- NV-PEEK-SOFTFAIL → NV-PEEK-MS-OK (1 次成功兜底) ✓
- 但 NV-ANTH-NO-CONTENT-GAP 17 次 + NV-ANTH-ZOMBIE 多次 — **全在 200 后, peek 拦不住**

03:23:29 完整链路 (req=ecafbaad):
1. k3/k4/k5 SSLEOFError (硬失败), k1 integrate SUCCESS → execute_request 返 success+resp
2. NV-PEEK-OK: 28s 首 content 到达, prebuffer 3505b → 判健康, **发 200**
3. NV-ANTH-ZOMBIE: content=0 reasoning=0 fr=tool_calls → **mid-stream zombie, 200 已落**
4. converter.finish(zombie=True) 发 api_error SSE + message_stop + conn.close (干净 EOF)
5. cc4101 passthrough 透传 api_error 给 CC, **读到干净 EOF → record_primary_success** (!)
6. CC 报 "Server error mid-response" (CC 不重试 mid-flight api_error)

## 框架 bug (3 层全漏)

1. **nv_gw anth 路径 mid-stream 软挂不记 nv_breaker**
   `_stream_openai_to_anth` (handlers.py L854) 的 no_content_gap/total_deadline/first_byte_timeout
   分支只 set error_type, **没调 nv_breaker.record_nv_failure()**. zombie/content_filter 只在 >250k
   时调 big_input_breaker (R1673 gate). 这些软挂 input avg 90-150k <250k → 全漏记.
   → nv_breaker 永 CLOSED, fail_count=0 (实测确认).

2. **cc4101 把 nv_gw 干净关连接当成功**
   `passthrough_stream` (cc4101 stream.py) 读到干净 EOF (nv_gw 发完 api_error+message_stop 后关连接)
   → `record_primary_success()` (L "正常结束" 分支). **把软挂当成功**.
   → cc4101 circuit 永 CLOSED.

3. **两层 breaker 都不 OPEN → 后续请求仍走 nv → 同样软挂 → 死循环**
   6h 17 次同类软挂, 每次都走 nv, 从不切 ms.

## 方案 (breaker 累积保后续, 用户确认)

### 改动 1: nv_gw `_stream_openai_to_anth` mid-stream 软挂 → 记 nv_breaker

在 `converter.finish` 后、`conn.close` 前, 加 catch-all (镜像 passthrough 路径 R1675 L1871 块):
```python
# R1719: anth 路径 mid-stream 软挂记 nv_breaker (不论 input 大小).
# 旧洞: no_content_gap/total_deadline/first_byte_timeout 只 set error_type 不 record →
# nv_breaker 永 CLOSED, 后续请求仍走 nv 同样软挂. 现扩展到所有 error_type (非 None 非 429).
# 与 passthrough 路径 R1675 对称 (那条记 big_input breaker >250k; anth 路径记 nv_breaker 不 gate input).
if (zombie_detected or metrics.get("error_type")) and not metrics.get("all_429"):
    _mapped = metrics.get("mapped_model", request_model)
    if _mapped in NVU_MS_FALLBACK_MODELS:
        nv_breaker.record_nv_failure()
        _log("NV-ANTH-BREAKER-FAIL", f"anth mid-stream soft-fail err={metrics.get('error_type')} "
            f"→ nv_breaker recorded (state={nv_breaker.breaker_state()[0]}, req={metrics.get('request_id','?')})")
```

注意: nv_breaker 只看 all_keys_exhausted (R1648c 语义). 但 record_nv_failure 不检查 error_type,
直接累加 fail_count. 所以这里调它会累积到 OPEN (N=15). OPEN 后 execute_request 入口
is_ms_fallback_open() 直走 ms, 跳过 nv 链 — **保后续请求不中断**.

### 改动 2: cc4101 passthrough 识别 `event: error` SSE → record_primary_failure

`passthrough_stream` (cc4101 stream.py) 在写 chunk 给 CC 前, 轻量检测 chunk 含 `event: error`:
- 命中 → 标记 `_upstream_error_seen = True` (跨 chunk 用 buffer 衔接, 防跨 chunk 漏检)
- 循环结束后: 若 `_upstream_error_seen` → `record_primary_failure()` (而非 record_primary_success)
- 仍透传 api_error 给 CC (当前请求中断, CC 报错 — 用户接受)

不全面解析 SSE, 只 grep 字节序列 `\nevent: error\n` (跨 chunk 缓冲). 最小侵入, 保持透传语义.

```python
# R1719: 轻量检测 nv_gw 发的 api_error SSE (mid-stream 软挂信号).
# 不解析 JSON, 只 grep `\nevent: error\n` 跨 chunk. 命中→上游软挂, 记 breaker failure.
_err_probe = b""  # 跨 chunk 残留, 防跨界漏检
_upstream_error_seen = False
...
# 在 _write_bytes 前:
if not _upstream_error_seen:
    _probe = _err_probe + chunk
    if b"event: error" in _probe:
        _upstream_error_seen = True
    _err_probe = _probe[-32:]  # 保留尾部 32b 防跨 chunk
# 循环结束:
if _upstream_error_seen and is_primary and not metrics.get("error_type"):
    record_primary_failure()  # 软挂当失败, 累积 circuit (覆盖原 record_primary_success)
    _log("CC4101-UPSTREAM-ERROR-SEEN", f"passthrough detected nv_gw api_error SSE → breaker failure")
else:
    if is_primary and not metrics.get("error_type"):
        record_primary_success()
```

### 改动 3 (可选, 验证后): nv_gw big_input_breaker 阈值/record 扩展

R1715 记的 150-250k 段漏记. 但本轮改动 1 已让 nv_breaker (不 gate input) 累积, 可覆盖.
big_input breaker 留作 >250k 快速跳过 (283k 死循环场景). 本轮不动, 观测 nv_breaker 是否足够.

## 预期效果

- 6h 17 次 no_content_gap → 累积到 nv_breaker N=15 → 第 15 次后 OPEN, 后续 30s 内直走 ms.
  → 第 16+ 次同类请求不再走 nv → 不再软挂中断.
- cc4101 circuit N=8 → 第 8 次后 OPEN, 后续 30s 直走 ms (双保险).
- 当前请求仍中断 (200 已发, CC 报 mid-response), 但**后续同类请求不再中断**.
- SR: 预期从 ~83% → ~90%+ (breaker OPEN 后的请求走 ms 成功率高).

## 改动文件 (只 HM2, bind-mount restart)

1. `/opt/cc-infra/proxy/nv-gw/gateway/handlers.py`
   - `_stream_openai_to_anth`: finish 后加 nv_breaker.record_nv_failure catch-all (需 import
     nv_breaker.record_nv_failure — 现 handlers.py 只 import record_nv_success as _nv_breaker_record_success)
2. `/opt/cc-infra/proxy/cc4101/gateway/stream.py`
   - `passthrough_stream`: 加 `event: error` 轻量检测 + 命中时 record_primary_failure

不碰: config.py (env 不变), ms_gw, upstream.py, circuit.py.

## 风险 + 验证

1. nv_breaker 误开: record_nv_failure 累积, 若有偶发软挂 (非系统性), N=15 阈值已足够缓冲.
   OPEN 30s 后 HALF_OPEN 探活, 恢复 CLOSED. 低风险.
2. cc4101 `event: error` 误检: 只 nv_gw 主动发 api_error 时有此 event, 正常流无. 但需确认
   NVCF 上游本身不发 `event: error` (openai SSE 协议无此 event, anthropic 才有). 验证 grep.
3. 跨 chunk 漏检: _err_probe 保留尾部 32b. 验证: 构造 `event: error` 跨 8192 边界.
4. 当前请求仍中断: 用户已确认接受.

验证清单:
- [ ] syntax check (容器内 py_compile)
- [ ] restart nv_gw + cc4101 + health OK
- [ ] 构造 mid-stream 软挂, 观察 NV-ANTH-BREAKER-FAIL + CC4101-UPSTREAM-ERROR-SEEN 日志
- [ ] breaker state 累积 (但注意 docker exec 看的是 fresh 进程, 需从日志推断或加 /debug 端点)
- [ ] 24h 观测: 502↓, NV-PEEK-MS-OK↑, 后续请求走 ms

## 落档

- 轮文件: rounds/R1719_hm2_breaker_midstream_softfail.md
- 代码标记: R1719
- 备份: handlers.py.bak.R1719_pre, stream.py.bak.R1719_pre
- commit + push (mihomo 7894)
- 铁律: 只改 HM2. 不碰 HM1.
