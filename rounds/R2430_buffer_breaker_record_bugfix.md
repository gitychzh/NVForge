# R2430 — Buffer AKE fail-fast 不记录 breaker 的 bug 修复

**时间**: 2026-08-18
**容器**: nv_gw (40006), buffer_stream.py

## 根因

buffer_stream.py 的 AKE fail-fast (line 617-624) 在连续 3 次 all_keys_exhausted 后 
break 退出 for-loop, **跳过了 line 650 的 `_nv_breaker_record_failure()`**。

结果: breaker 永远 CLOSED (0 failures), 每个 request 都 wastefully 重试 NVCF 5 次 
(~40-90s) 才走 MS fallback, 而不是 breaker OPEN 后直接走 MS (省 ~60s)。

## 修复

在 AKE fail-fast break 之前添加:
1. `_nv_breaker_record_failure()` — 让 breaker 正确记录失败, 3 次后 OPEN
2. `fid_discovery.trigger_immediate()` — 触发即时 fid 发现 (非阻塞)
3. 同样修复 ALL-COOLING fail-fast break (同样跳过 line 650 的 bug)

## 验证

重启后 3 分钟内:
- `NV-BREAKER-RECORD: AKE fail-fast, recording nv failure (state=('OPEN', 3, 14))` ✅
- Breaker 正确 OPEN, 14s cooldown
- `NV-BUFFER-BREAKER-OPEN: skipping NVCF, serving ms_gw directly` ✅
- fid_discovery trigger 正确运行: `Found 1 ACTIVE candidates, No new healthy FIDs`
- NVCF 直接跳过, 不再 wasteful 重试
