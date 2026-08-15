# R1258: pacer_queue_timeout 系统性修复 — forwarder fallback + QUEUE_TIMEOUT 20→10

**日期**: 2026-08-15
**作者**: cc2 (与 ChatGPT 系统讨论后方案)
**严重性**: 复杂且严重 (多次复发, 用户上报)

## 问题

oc45001 pacer 限流器 (`MAX_CONCURRENCY=1`, `MIN_INTERVAL_S=8`, `QUEUE_TIMEOUT_S=20`) 在长请求
(50-60s, big-pickle 推理慢) 占用唯一并发闸时, 新请求排队 20s 后超时返回 429
`pacer_queue_timeout`. hm4104 forwarder 将此 429 归类为 `client_4xx`, 不触发 fallback,
直接透传错误给用户. 用户看到 `queue timeout: global concurrency gate busy` 错误.

### DB 铁证 (容器 07:06 启动后)

```
 total | ok | pacer_timeout | sr_pct
-------+----+---------------+--------
    96 | 93 |             3 |   96.9
```

upstream 429 也很高 (275 次), 说明 opencode Zen 免费 API 限流极严格, 不能加并发.

### 根因链

1. big-pickle 推理慢 (TTFB 10-20s, 总耗时 50-60s) → 占用唯一并发闸
2. 新请求排队等 20s → 仍拿不到闸 → pacer 返回 429 `pacer_queue_timeout`
3. hm4104 forwarder `_post_upstream()` 将 429 归为 `client_4xx` → 不 fallback
4. `_is_exhausted()` 只检测 "exhausted" 关键词, 不认 `pacer_queue_timeout`
5. 用户直接看到 429 错误, 无降级

## 修复方案 (与 ChatGPT 讨论确定)

### 改动 1: forwarder.py — 新增 `_is_pacer_queue_timeout()`

**文件**: `/opt/cc-infra/proxy/cc-adapter/gateway/forwarder.py` (bind-mount, 3 容器共享)

```python
def _is_pacer_queue_timeout(err_json):
    """oc45001 pacer 排队超时 (本地 admission queue 满) → 应 fallback, 非 client 错误."""
    if not isinstance(err_json, dict):
        return False
    error = err_json.get("error")
    if isinstance(error, dict):
        return error.get("code") == "pacer_queue_timeout"
    return err_json.get("code") == "pacer_queue_timeout"
```

与 `_is_exhausted()` 语义分离: exhausted=上游额度耗尽, pacer_queue_timeout=本地并发闸排队超时.
(ChatGPT 建议: 不要塞进 _is_exhausted, 保持故障语义独立, 便于后续分别统计)

### 改动 2: forwarder.py — 429 分类逻辑

```python
# 改前:
if kind == "client_4xx" and _is_exhausted(err_json):
    kind = "server_5xx"

# 改后:
if kind == "client_4xx" and (_is_exhausted(err_json) or _is_pacer_queue_timeout(err_json)):
    kind = "server_5xx"
```

效果: pacer_queue_timeout 429 → server_5xx → 触发 fallback 到 dsv4f0731_nv40666 (NVCF)

### 改动 3: oc45001 QUEUE_TIMEOUT_S 20→10

**文件**: `/opt/cc-infra/proxy/oc-proxy/docker-compose.yml`

QUEUE_TIMEOUT 必须 > MIN_INTERVAL_S (=8), 否则即使上游空闲, 仅因间隔闸未到也会超时.
设为 10s = 8s 间隔 + 2s 余量. 长请求占用时, 新请求等 10s 拿不到闸就 fail-fast 走 fallback.

(ChatGPT 建议 5s, 但 5 < MIN_INTERVAL_S=8 会导致误杀. 调整为 10s)

## 不改的部分 (ChatGPT 明确建议)

- **不 bypass pacer** — 跳过限流器直接打上游会触发更多 upstream 429 (275 次已很高)
- **不在 oc45001 内做 fallback** — 保持职责分离: oc45001=pacing/admission, hm4104=failover
- **不改 MAX_CONCURRENCY/MIN_INTERVAL_S** — 一次只改一个变量
- **不改 _is_exhausted()** — 保持语义分离

## 验证

```
=== Health ===
oc45001:     {"status":"ok"}  (QUEUE_TIMEOUT_S=10)
hm4104:      {"status":"ok"}  (forwarder.py 有 _is_pacer_queue_timeout × 2)
opclaw4103:  {"status":"ok"}
oc4105:      {"status":"ok"}

=== Smoke test ===
curl hm4104 → 200 OK, big-pickle "2", 2826ms

=== DB ===
dbc876e12cb7 | hermes | 200 | | 2826ms | 0 paced_wait
```

## 后续观察指标

| 指标 | 意义 |
|---|---|
| primary_success | primary 真正成功 |
| pacer_queue_timeout | admission 失败 (应比 20s 时代多, 但每次都 fallback) |
| fallback_success | fallback 成功 (pacer 超时后降级到 NVCF) |
| fallback_failure | fallback 也失败 (需关注) |
| real_upstream_429 | 真正上游 429 (不应增加) |

如果 fallback_success / pacer_timeout > 80% → fail-fast 策略有效.
如果 fallback_failure 高 → fallback 本身不可用, 需重新评估.
