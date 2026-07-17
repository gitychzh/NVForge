# R1719: HM2 nv_gw anth 路径 mid-stream 软挂记 nv_breaker + cc4101 识别 api_error SSE 标失败 (breaker 累积保后续)

> R1716 peek barrier 只把关"首字节前"软挂; 200 落 cc4101 后的 mid-stream 软挂 (no_content_gap /
> total_deadline / zombie / content_filter) 仍兜不住 → CC 仍报 "Server error mid-response".
> 用户定性: 严重的框架 BUG, 必须系统性解决, 不应直接中断.
> 方案深度 (用户确认 AskUserQuestion): breaker 累积保后续请求 (当前请求中断可接受) — 标失败让
> cc4101 下次请求切 ms.
>
> 铁律: 只改 HM2. 不碰 HM1.

## 现场 (R1716 部署后, 3h HM2 glm5_2_nv nv_requests)

```
error_type                 | upstream_type | c  | avg_s
stream_no_content_gap      | nv_integrate  | 17 | 151.0   ← 200 后中途挂, peek 拦不住
stream_total_deadline      | nv_integrate  |  3 | 225.2
zombie_empty_completion    | nv_integrate  |  3 | 17.0
zombie_empty_completion    | nvcf_pexec    |  3 | 5.7
stream_first_byte_timeout  | ms_fallback   |  1 | 64.5    ← R1716 peek 触发, ms 也失败
stream_first_byte_timeout  | nv_integrate  |  1 | 63.1
```

R1716 peek barrier 实际触发 (日志确认): NV-PEEK-OK 多次 (健康续流), NV-PEEK-SOFTFAIL→
NV-PEEK-MS-OK (1 次成功兜底). 但 NV-ANTH-NO-CONTENT-GAP 17 次 + NV-ANTH-ZOMBIE 多次 —
**全在 200 后, peek 拦不住**.

03:23:29 完整链路 (req=ecafbaad):
1. k3/k4/k5 SSLEOFError (硬失败), k1 integrate SUCCESS → execute_request 返 success+resp
2. NV-PEEK-OK: 28s 首 content 到达, prebuffer 3505b → 判健康, **发 200**
3. NV-ANTH-ZOMBIE: content=0 reasoning=0 fr=tool_calls → **mid-stream zombie, 200 已落**
4. converter.finish(zombie=True) 发 api_error SSE + message_stop + conn.close (干净 EOF)
5. cc4101 passthrough 透传 api_error 给 CC, **读到干净 EOF → record_primary_success** (BUG)
6. CC 报 "Server error mid-response" (CC 不重试 mid-flight api_error)

## 框架 bug (3 层全漏)

1. **nv_gw anth 路径 mid-stream 软挂不记 nv_breaker**
   `_stream_openai_to_anth` 的 no_content_gap/total_deadline/first_byte_timeout 分支只 set
   error_type, **没调 nv_breaker.record_nv_failure()**. zombie/content_filter 只在 >250k 时
   调 big_input_breaker (R1673 gate). 这些软挂 input avg 90-150k <250k → 全漏记.
   → nv_breaker 永 CLOSED, fail_count=0 (实测确认).

2. **cc4101 把 nv_gw 干净关连接当成功**
   `passthrough_stream` 读到干净 EOF (nv_gw 发完 api_error+message_stop 后关连接) →
   `record_primary_success()`. **把软挂当成功**. → cc4101 circuit 永 CLOSED.

3. **两层 breaker 都不 OPEN → 后续请求仍走 nv → 同样软挂 → 死循环**
   6h 17 次同类软挂, 每次都走 nv, 从不切 ms.

## 改动 (两文件, bind-mount restart)

### 1. `/opt/cc-infra/proxy/nv-gw/gateway/handlers.py` — anth 路径 catch-all 记 nv_breaker

- L52: 加 `from .nv_breaker import record_nv_failure as _nv_breaker_record_failure`
- L1297-1311: 在 `_stream_openai_to_anth` 的 `converter.finish` 后、`conn.close` 前, 加
  catch-all 块 (镜像 passthrough 路径 R1675 L1878 块的形状, 但记 nv_breaker 不 gate input):

```python
if (zombie_detected or metrics.get("error_type")) and not metrics.get("all_429"):
    _mapped_r1719 = metrics.get("mapped_model", request_model)
    if _mapped_r1719 in NVU_MS_FALLBACK_MODELS:
        _nv_breaker_record_failure()
        _log("NV-ANTH-BREAKER-FAIL", ...)
```

语义: nv_breaker 只看 all_keys_exhausted (R1648c 语义), 但 record_nv_failure 不检查
error_type, 直接累加 fail_count. 累积到 N=NVU_MS_FALLBACK_FAIL_THRESHOLD(15) → OPEN →
execute_request 入口 `is_ms_fallback_open()` 直走 ms, 跳过 nv 链 — **保后续请求不中断**.

### 2. `/opt/cc-infra/proxy/cc4101/gateway/stream.py` — passthrough 识别 `event: error` 标失败

- `passthrough_stream`: 加 `_err_probe = b""` + `_upstream_error_seen = False` 状态
- 循环内写 chunk 前: 跨 chunk 缓冲探测 `b"event: error"` (保留尾部 32b 防跨界漏检)
- 干净 EOF 处: 若 `_upstream_error_seen` → `record_primary_failure()` (覆盖原 success)

```python
if is_primary and not metrics.get("error_type") and _upstream_error_seen:
    record_primary_failure()
    _log("CC4101-UPSTREAM-ERROR-SEEN", ...)
elif is_primary and not metrics.get("error_type"):
    record_primary_success()
```

不全面解析 SSE, 只 grep 字节序列. 最小侵入, 保持透传语义 (api_error 仍透传给 CC).
cc4101 circuit N=CC4101_PRIMARY_FAIL_THRESHOLD(8) → OPEN → Stage 0 直走 ms (双保险).

## 不碰

- config.py (env 不变), ms_gw, upstream.py, circuit.py, nv_breaker.py, big_input_breaker.py.
- big_input_breaker 留作 >250k 快速跳过 (283k 死循环场景 R1673). 本轮靠 nv_breaker (不
  gate input) 累积覆盖 <250k 软挂. 观测后下轮再决是否动 big_input 阈值 (R1715 记的
  150-250k 段漏记).

## 预期效果

- 6h 17 次 no_content_gap → 累积到 nv_breaker N=15 → 第 15 次后 OPEN, 后续 30s 直走 ms.
- cc4101 circuit N=8 → 第 8 次后 OPEN, 后续 30s 直走 ms (双保险).
- 当前请求仍中断 (200 已发, CC 报 mid-response), 但**后续同类请求不再中断**.
- SR: 预期从 ~83% → ~90%+.

## 验证

- [x] syntax check (容器内 py_compile, 两文件均 OK)
- [x] restart nv_gw + cc4101, health OK, StartedAt fresh (20:00:08Z)
- [x] E2E streaming test (cc4101 → nv_gw → NVCF glm5_2_nv): full message_start →
      content deltas → message_stop, 无 `event: error`, 无中断. 探针未误触发 (健康流无
      `event: error`, 无 CC4101-UPSTREAM-ERROR-SEEN 日志, 正确).
- [ ] 24h 观测: 下次实弹 mid-stream 软挂时确认 NV-ANTH-BREAKER-FAIL + CC4101-UPSTREAM-ERROR-SEEN
      双日志出现, nv_breaker/cc4101 circuit fail_count 累积, OPEN 后后续请求走 ms (NV-PEEK-MS-OK
      或 cc4101 [FALLBACK] 日志), 502↓, SR↑.

## 风险

1. nv_breaker 误开: record_nv_failure 累积, 偶发软挂 N=15 阈值已足够缓冲, OPEN 30s 后
   HALF_OPEN 探活, 恢复 CLOSED. 低风险.
2. cc4101 `event: error` 误检: 只 nv_gw 主动发 api_error 时有此 event, 正常流无. openai
   SSE 协议无 `event:` 字段 (anthropic 才有), NVCF 上游本身不发. 低风险.
3. 跨 chunk 漏检: _err_probe 保留尾部 32b 覆盖 8192 边界.

## 落档

- 代码标记: R1719
- 备份: handlers.py.bak.R1719_pre, stream.py.bak.R1719_pre (HM2 /opt/cc-infra)
- 计划: R1719_plan.md
- commit + push (mihomo 7894) — pending
- 铁律: 只改 HM2. HM1 同步待 HM2 稳定 2-3 天后另轮.
