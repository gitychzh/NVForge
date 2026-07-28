# R2417: cc4101 stair-timeout 残留根治 (HM2)

## 时间
2026-07-28 15:24 CST

## 根因

R-cc_s3 (R2308 计划) 部署了两层机制: cc4101 阶梯超时 (`TIMEOUT_STAIRS=[60,120,240]`)
+ nv_gw 固定 key 绑定. R2416 解除了固定 key 绑定 (cc4101-primary 从 CALLER_KEY_MAP
移除), 但 **cc4101 handlers.py 的阶梯超时逻辑没有同步移除**, 造成两个 bug:

### Bug 1: 阶梯超时覆盖 R2154 input-size header_timeout

`TIMEOUT_STAIRS = [60, 120, 240]` 通过 `header_timeout_override=60` 强制覆盖
R2154 的分档表. 170K chars 的请求本应给 180s (R2202), 但被 stair 强制 60s →
NVCF TTFB 60-142s 的请求全被 60s 砍断 → 100% 502.

### Bug 2: _try_primary 不设 result.error_kind → stair 循环第一次就 break

`_try_primary()` 在 timeout/conn/server_5xx 失败时只 `return False`, 不设
`result.error_kind` (仅 client_4xx 设). 阶梯循环检查 `_ek = result.error_kind or ""`,
得到空串 ≠ "timeout" → 日志 "non-timeout error_kind= -> stop stair, return original
error" → **阶梯重试从未生效, 60s timeout 后直接返回 502**.

### 连锁效应
- 每 60s 一次 502 → CC 重试 → 新请求又 60s → 死循环
- fallback 已禁用 (FALLBACK_UPSTREAM_URL=none) 但仍走 `_try_fallback` 判定
  (返回 False), 浪费一轮函数调用 + 日志噪音
- cc2 (自优化 agent) 和用户交互式 session 都受影响

## 数据 (改前 30min)

```
cc_requests: 200=34, 502=11 (upstream_error, avg 60.1s)
nv_requests (cc4101-primary): 200=37, 502=5 (all_tiers_exhausted=4, buffer_exhausted=1)
```

所有 502 都是 60s timeout, 铁证 stair override 覆盖了 R2154 的 150-180s 分档.

## 修复

### 1. handlers.py: 移除阶梯逻辑, 恢复直接 execute_request 调用

```python
# 旧 (R-cc_s3):
TIMEOUT_STAIRS = [60, 120, 240]
for _stair_attempt, _hdr_to in enumerate(TIMEOUT_STAIRS, 1):
    result = execute_request(anth_body, request_id, metrics, t_start,
                             header_timeout_override=_hdr_to)
    ...

# 新 (R2417):
result = execute_request(anth_body, request_id, metrics, t_start)
# 不传 header_timeout_override → R2154 input-size 分档生效
```

### 2. upstream.py: _try_primary retryable 分支补设 result.error_kind

```python
# 旧: return False (error_kind=None)
# 新:
result.error_kind = e.kind
result.error_message = e.message
result.elapsed_ms = ms
metrics["upstream_used"] = "primary"
metrics["mapped_model"] = PRIMARY_UPSTREAM_MODEL
metrics["key_cycle_details"] = attempts
return False
```

## 验证 (改后 5min)

```
cc_requests: 200=11, 502=1 (60s, 间歇性 NVCF)
nv_requests (cc4101-primary): 200=15, 502=0
```

cc4101 日志确认:
- `hdr_to=160` (R2154 90-150K 档生效, 旧 stair 强制 60s)
- `hdr_to=60` 仅出现在 <30K 小请求 (R2154 默认档)
- 无 `REQ-STAIR` 日志 (阶梯逻辑已移除)

## 备份
- `handlers.py.bak.R2417`
- `upstream.py.bak.R2417`

## 回滚
```bash
cp /opt/cc-infra/proxy/cc4101/gateway/handlers.py.bak.R2417 /opt/cc-infra/proxy/cc4101/gateway/handlers.py
cp /opt/cc-infra/proxy/cc4101/gateway/upstream.py.bak.R2417 /opt/cc-infra/proxy/cc4101/gateway/upstream.py
cd /opt/cc-infra && docker compose restart cc4101
```
