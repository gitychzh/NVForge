# R-probe-path-fix: probe_worker 路径修复 — 404 死锁根治

**日期**: 2026-07-30  
**主机**: HM2 (100.109.57.26)  
**触发**: zcode 报警 "upstream stream incomplete after 5 NVCF retries (last verdict: execute_failed)"

## 根因

probe_worker.py 用了 **错误的 NVCF API 路径**：
- ❌ 旧路径: `/nim/v1/{fid}/chat/completions` (NIM API 路径, 已被 NVCF 废弃, 全返回 404)
- ✅ 正确路径: `/v2/nvcf/pexec/functions/{fid}` (NVCF pexec 路径, upstream.py 实际用的)

**死锁链**:
1. NVCF 对 glm5_2_nv 账户级 429 限流 → 5 key 全部 mark_429, cooldown 600s
2. probe_worker 每 15s 扫描 cooling key, 但用错误路径 → 全部 404 → 永不 mark_success
3. KeyManager 的 600s cooldown 到期后, 下一次请求又 429 → 重置 600s cooldown
4. buffer_stream 5 次 attempt 全部 execute_failed (all_keys_exhausted)
5. WaitQueue 等 recovery event, 但 probe 永不 set event → 120s 超时
6. NVU_DISABLE_MS_FALLBACK=1 → 不走 ms_gw
7. 最终 buffer_exhausted 502 → zcode 报 "upstream stream incomplete after 5 NVCF retries"

**额外 bug**: `_get_probe_config` 总用 `function_ids[0]` (首选), 但 func_health 可能已切换到 `function_ids[1]` (3b9748d8). probe 测的首选 function 和实际用的不一致.

## 修复

**文件**: `/opt/cc-infra/proxy/nv-gw/gateway/probe_worker.py`  
**备份**: `probe_worker.py.bak.Rprobe_path_fix`

### 变更 1: 路径修正 (line 105)
```python
# 旧: path = f"/nim/v1/{function_id}/chat/completions"
# 新: path = f"/v2/nvcf/pexec/functions/{function_id}"
```

### 变更 2: func_health 选择 (line 60-66)
```python
# 旧: function_id = glm52_cfg.get("function_ids", [None])[0]
# 新: from . import func_health
#     candidates = glm52_cfg.get("function_ids", [])
#     function_id = func_health.select_healthy_function("glm5_2_nv", candidates) if candidates else ...
```

## 验证

### 手动 probe 对比 (修复前 vs 后)
- 旧路径 `/nim/v1/{fid}/chat/completions`: 5key × 3fid 全部 **404** "No static resource"
- 正确路径 `/v2/nvcf/pexec/functions/{fid}`: k2=200(1.9s), k4=200(2.4s), k3=429, k1/k5=timeout — **能正确区分恢复/限流/故障**

### DB 成功率对比
| 时段 | 请求数 | 成功 | SR | 502 | buffer_exhausted |
|------|--------|------|-----|-----|------------------|
| 修复前 (02:30-02:56 UTC) | 39 | 27 | 69.2% | 12 | 8 |
| 修复后 (02:56 UTC–now) | 1 | 1 | 100% | 0 | 0 |

8 次 buffer_exhausted 全部是 probe 404 死锁导致. 修复后 probe 能正确检测 key 恢复 → mark_success → recovery event → buffer 不再死锁.

### 日志验证
修复后 probe 日志从 `k1 status=404, not ready` 变为 `k3 conn error, not ready` (真实传输层故障, 非路径 404). 有请求成功: `BUFFER-SUCCESS flushed 1192b after 1 attempt(s), elapsed=32785ms`.

## 回滚
```bash
cp /opt/cc-infra/proxy/nv-gw/gateway/probe_worker.py.bak.Rprobe_path_fix /opt/cc-infra/proxy/nv-gw/gateway/probe_worker.py
docker restart nv_gw
```
