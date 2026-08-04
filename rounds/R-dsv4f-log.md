# R-dsv4f-log: dsv4f_nv 日志完整性修复 — function_id 全路径记录

**Date:** 2026-08-04
**Container:** dsvf0731_nv40666 (port 40666, HM2)
**Commit:** (this round)

## 背景

R-dsv4f-dynamic 部署后, 发现 502 失败记录在 DB 中缺少 function_id/upstream_type/nv_key_idx 等字段。需确保所有路径 (成功/失败/流式) 都完整记录 function_id, 方便长期数据分析。

## 修复前数据 (问题)

```
ts               | status | upstream_type | function_id              | nv_key_idx | litellm_model
-----------------+--------+---------------+--------------------------+------------+-------------
15:07:52         | 502    | (null)        | 52e1ddb6...              | (null)     | (null)       ← 缺失
15:06:57         | 200    | nvcf_pexec    | 52e1ddb6...              | 4          | nvcf_pexec_..  ← 完整
```

502 记录的 upstream_type/nv_key_idx/litellm_model 全部为空 — handlers.py 失败路径未从 result 复制这些字段。

## 修复

### handlers.py (3 处补丁)

**1. 失败路径 (all_keys_exhausted)**: 新增从 result 复制到 metrics:
```python
if getattr(result, "function_id", None):
    metrics["function_id"] = result.function_id
if getattr(result, "upstream_type", None):
    metrics["upstream_type"] = result.upstream_type
if getattr(result, "nv_key_idx", None) is not None:
    metrics["nv_key_idx"] = result.nv_key_idx
if getattr(result, "nv_model_label", None):
    metrics["litellm_model"] = result.nv_model_label
if getattr(result, "egress_route", None):
    metrics["egress_route"] = result.egress_route
if getattr(result, "egress_ip", None):
    metrics["egress_ip"] = result.egress_ip
if result.key_cycle_attempts:
    metrics["key_cycle_details"] = result.key_cycle_attempts
```

**2. 成功路径**: 新增 function_id + upstream_type 的 belt-and-suspenders 复制:
```python
if getattr(result, "function_id", None):
    metrics["function_id"] = result.function_id
if getattr(result, "upstream_type", None):
    metrics["upstream_type"] = result.upstream_type
```

### upstream.py (1 处补丁)

**_log_error_detail (all_tiers_failed)**: 新增 function_id + key_cycle_attempts:
```python
"function_id": metrics.get("function_id", ""),
"key_cycle_attempts": [{"nv_key_idx": ..., "error_type": ..., "function_id": ..., 
                          "upstream_type": ..., "path": ..., "tier": ...} ...],
```

## 修复后数据验证

### DB 查询 (1 小时窗口)
```
function_id              | upstream_type | reqs | ok | sr_pct | avg_latency_s
-------------------------+---------------+------+----+--------+---------------
52e1ddb6...              | nvcf_pexec    |   39 | 34 |   87.2 |        19.66
52e1ddb6...              | (null=旧502)  |   14 |  0 |    0.0 |
integrate                | nv_integrate  |   12 | 12 |  100.0 |        17.62
6166b605... (旧FID)      |               |    9 |  0 |    0.0 |
```

### 502 记录现在完整
```
status=502, upstream_type=nvcf_pexec, function_id=52e1ddb6..., nv_key_idx=0
```

### error_detail JSONL 现在包含每次尝试的 function_id + path
```json
{
  "function_id": "52e1ddb6...",
  "key_cycle_attempts": [
    {"nv_key_idx": 2, "error_type": "529_nv_overloaded", "function_id": "52e1ddb6...", "upstream_type": "nvcf_pexec", "path": "pexec"},
    {"nv_key_idx": 3, "error_type": "529_nv_overloaded", "function_id": "integrate", "upstream_type": "nv_integrate", "path": "integrate"},
    ...
  ]
}
```

## 文件改动

| 文件 | 改动 | 说明 |
|------|------|------|
| `gateway/handlers.py` | +10 行 | 失败路径复制 result 字段到 metrics + 成功路径 function_id |
| `gateway/upstream.py` | +4 行 | _log_error_detail 新增 function_id + key_cycle_attempts |
