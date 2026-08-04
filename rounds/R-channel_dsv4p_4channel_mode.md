# R-channel: dsv4p_nv 通路模式 (4 channel × 5 key rotation)

**Date**: 2026-08-04
**Host**: HM2 (100.109.57.26)
**Model**: dsv4p_nv (deepseek-ai/deepseek-v4-pro)
**Containers affected**: nv_gw(40006), dsv4p_nv40066(40066), dsvf0731_nv40666(40666)

## 背景

dsv4p_nv 三个 pexec function ID 全部 404 (account-wide "function not found"):
- 74f02205 (ai-deepseek-v4-pro): 之前秒回 200, 2026-08-04 起 404/504
- 12acbc62 (dynamo-mn): 404 "not found in account"
- 8915fd28 (sglang-deepseek-v4-pro): 404 "not found in account"

integrate 路径: K4/K5 429 (rate limit), K1-K3 timeout/RemoteDisconnected

旧代码: 404 = non-cycling error → ��接 abort tier, 只试 1 个 key 就放弃, 不试其他 function_id 也不试 integrate.

## 改动

### 1. config.py: dsv4p_nv function_ids 从 1 个扩展到 3 个

```python
# Before:
"function_ids": [os.environ.get("NVCF_DEEPSEEK_FUNCTION_ID", "12acbc62-...")],

# After:
"function_ids": [
    "74f02205-c7ba-438f-b81a-2537955bd7ec",
    "12acbc62-3a9e-461f-8139-142e914b6f16",
    "8915fd28-fe8f-47d6-a35d-d745d78b35d5",
],
```

不再从 env 读 NVCF_DEEPSEEK_FUNCTION_ID (env override 已注释).

### 2. upstream.py: 新增 _try_dsv4p_channel_keys() 函数

**通路模式核心**: 4 channels (3 pexec fids + 1 integrate) × 5 keys = 20 max attempts.

- Ch0: pexec with fid 74f02205
- Ch1: pexec with fid 12acbc62
- Ch2: pexec with fid 8915fd28
- Ch3: integrate (fid=null, via integrate.api.nvidia.com)

每次 attempt 同时轮换 key_idx 和 channel_idx:
- key_idx = (start_key_idx + attempt_idx) % 5
- channel_idx = (start_channel + attempt_idx) % 4
- 当 key K 在 channel N 失败 → 试 key K+1 在 channel (N+1)%4

关键: 404 错误从 non-cycling 改为 cycling — 404 表示该 function_id 在该 account 不可用,
应该试下一个 channel (不同的 function_id). 这解决了旧代码 404 → abort 的问题.

### 3. execute_request(): dsv4p_nv 专属分支

在 R838b/R572/pexec 分支之前插入 dsv4p_nv channel mode 分支:
- is_first_tier and tier_model == "dsv4p_nv" and not _chain_failed
- 调用 _try_dsv4p_channel_keys()
- 成功 → return; 失败 → set tier_result + _dsv4p_channel_done=True
- _dsv4p_channel_done=True 跳过后续 R838b/R572/_try_tier_keys 分支

### 4. docker-compose.yml: 注释 NVCF_DEEPSEEK_FUNCTION_ID env

```yaml
# Before:
- NVCF_DEEPSEEK_FUNCTION_ID=12acbc62-3a9e-461f-8139-142e914b6f16
# After:
# R-channel: NVCF_DEEPSEEK_FUNCTION_ID no longer used — config.py hardcodes 3 fids for channel mode
# - NVCF_DEEPSEEK_FUNCTION_ID=12acbc62-3a9e-461f-8139-142e914b6f16
```

## 数据 (改前)

改前 30min 窗口 (2026-08-04 18:00-18:30 UTC):
- dsv4p_nv pexec: 全 404 "Function id ... not found in account"
- 0/N keys 成功, 0% SR
- 旧代码 404 non-cycling → 只试 1 key 就 abort, 1.7-1.9s 即返回 502

## 验证 (改后)

### E2E test 1 (nv_gw:40006, curl):
- 4 channels × 5 keys 全部尝试
- Ch0 (74f02205) → 504 timeout (63s)
- Ch1 (12acbc62) → 404 not found (1.4s, cycling ✓)
- Ch2 (8915fd28) → 404 not found (0.8s, cycling ✓)
- Ch3 (integrate) → RemoteDisconnected (35s)
- 404 正确 cycling (旧代码会 abort), 4 轮后 conn_err fast-break
- 不再 fall through 到 pexec _try_tier_keys (fix verified)

### E2E test 2 (dsv4p_nv40066:40066, curl):
- 9 attempts, 180s budget
- K1 Ch0 → 429, K2 Ch1 → 404, K3 Ch2 → 404, K4 Ch3 → 429, K5 Ch0 → 504
- K2 Ch2 → 404, K3 Ch3 → RemoteDisconnected, K4 Ch0 → timeout
- Budget 180s 耗尽 → fail

### E2E test 3 (glm5_2_nv regression, nv_gw + dsv4p_nv40066):
- glm5_2_nv 200 OK "Hello!" 1.5s — 无回归

## 影响

- dsv4p_nv 当前全通道失效 (NVCF account-level 问题, 非 config 可修)
- 通路模式已就位, NVCF 恢复任一 function 或 integrate 恢复时自动发现可用通道
- glm5_2_nv/kimi_nv/dsv4f_nv 不受影响 (channel mode 仅对 dsv4p_nv 触发)
- openclaw (opclaw4103) + hermes (hm4104) 当前走 dsvf0731_nv40666 (dsv4f_nv) primary,
  dsv4p_nv40066 作为 fallback — fallback 路径已有通道模式
