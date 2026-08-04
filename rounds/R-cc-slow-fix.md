# R-cc-slow-fix: CC 超慢根因修复 — 40066 buffer retry + zombie_empty_completion 重试

**Date**: 2026-08-04  
**Host**: HM2 (opc2sname)  
**Session**: edba3864-d215-4dec-b971-d5474aae85ad

## 问题

CC session `edba3864` 超长时间不能完成。cc4101 大量 PRIMARY-FAIL (502) + FALLBACK-FAIL (502)，breaker 持续 OPEN。

## 根因分析

### 根因 1: dsv4p_nv40066 NVU_BUFFER_CALLERS 为空

40066 容器 (cc4101 的 primary upstream) 的 `NVU_BUFFER_CALLERS=` (空)，而主 nv_gw 40006 有 `NVU_BUFFER_CALLERS=cc4101-primary,openclaw2`。

当 NVCF integrate 流被截断 (IncompleteRead) 时：
- 40006: 触发 buffer 5-key 重试，换 key 换 IP 后成功
- 40066: 无 buffer 重试，直接返回 502

### 根因 2: zombie_empty_completion 不触发 buffer 重试

handlers.py 的 collect 路径 buffer 重试条件 `_is_transport_collect_err` 只匹配 `NVAnthCollect_*` 前缀的错误（传输中断类），不覆盖 `zombie_empty_completion`。

数据证实: `stream=False` + `thinking=disabled` + ~126K chars → NVCF integrate 返回 200 但空内容 (zombie)，原逻辑直接返回 502。

metrics JSONL 数据:
- `a8e650e9`: 125K chars, stream=False, thinking=disabled, 15s, zombie
- `5ddc2e06`: 125K chars, stream=False, thinking=disabled, 11s, zombie  
- `02054750`: 126K chars, stream=False, thinking=disabled, 22s, zombie
- `9ca72f62`: 126K chars, stream=False, thinking=disabled, 28s, zombie
- `73ba8666`: 126K chars, IncompleteRead → buffer retry → SUCCESS
- `f3195450`: 126K chars, stream=False, thinking=disabled, 13s, zombie
- `97c3873a`: 126K chars, stream=False, thinking=disabled, 12s, zombie

### 根因 3: 40666 fallback 也有问题

dsvf0731_nv40666 (flash fallback) 也有 `NVU_BUFFER_CALLERS=` (空)。NVCF 529 过载 + pexec 404 (function 未部署) 导致 fallback 也 502。

## 修复

### 修复 1: 启用 40066 buffer callers

`docker-compose.yml` dsv4p_nv40066 服务:
```yaml
# 旧
NVU_BUFFER_CALLERS=
NVU_BUFFER_MAX_RETRIES=1

# 新
NVU_BUFFER_CALLERS=cc4101-primary
NVU_BUFFER_MAX_RETRIES=5
NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90
NVU_BUFFER_PING_INTERVAL_S=30
NVU_BUFFER_TOTAL_DEADLINE_S=450
```

### 修复 2: 启用 40666 buffer callers

`docker-compose.yml` dsvf0731_nv40666 服务:
```yaml
NVU_BUFFER_CALLERS=cc4101-fallback
```

### 修复 3: 扩展 zombie_empty_completion 触发 buffer 重试

`handlers.py` `_collect_stream_to_anth` 后的 buffer retry 条件:

```python
# 旧
_is_transport_collect_err = (
    _collect_err.startswith("NVAnthCollect_")
    and _collect_err != "NVAnthCollect_")
if (_is_transport_collect_err
        and oai_body is not None
        and not _collect_buf_retried
        and metrics.get("caller", "") in NVU_BUFFER_CALLERS):

# 新
_is_transport_collect_err = (
    _collect_err.startswith("NVAnthCollect_")
    and _collect_err != "NVAnthCollect_")
_is_zombie_collect_err = _collect_err == "zombie_empty_completion"
if ((_is_transport_collect_err or _is_zombie_collect_err)
        and oai_body is not None
        and not _collect_buf_retried
        and metrics.get("caller", "") in NVU_BUFFER_CALLERS):
```

## 验证

### 修复前
- cc4101 PRIMARY-FAIL + FALLBACK-FAIL 频发 (每 2-3 分钟一次)
- stream=True 请求因 40066 无 buffer 而直接 502
- stream=False + thinking=disabled + 126K chars 请求 zombie 502
- Breaker 持续 OPEN

### 修复后
- `55fde611`: zombie_empty → buffer retry → SUCCESS (6s) ✅
- `34e55ada`: zombie_empty → buffer retry → SUCCESS (18s) ✅
- `45db38a7`: IncompleteRead → buffer attempt 1 zombie_partial → attempt 2 SUCCESS ✅
- `bc0a7712`: zombie_empty → buffer retry → SUCCESS (12s) ✅
- 14:55 后 cc4101 无 PRIMARY-FAIL，breaker CLOSED
- stream=True 请求全通过 buffer 成功
- stream=False zombie 请求全通过 buffer retry 恢复

## 参数变更表

| 参数 | 旧值 | 新值 | 容器 |
|---|---|---|---|
| NVU_BUFFER_CALLERS | (空) | cc4101-primary | dsv4p_nv40066 |
| NVU_BUFFER_MAX_RETRIES | 1 | 5 | dsv4p_nv40066 |
| NVU_BUFFER_TIMEOUT_STAIRS | (无) | 90,90,90,90,90 | dsv4p_nv40066 |
| NVU_BUFFER_PING_INTERVAL_S | (无) | 30 | dsv4p_nv40066 |
| NVU_BUFFER_TOTAL_DEADLINE_S | (无) | 450 | dsv4p_nv40066 |
| NVU_BUFFER_CALLERS | (空) | cc4101-fallback | dsvf0731_nv40666 |
| handlers.py collect buffer retry | NVAnthCollect_* only | + zombie_empty_completion | 40066 |
