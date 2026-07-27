# R-buf5key: 5-key rotation + ms_gw final fallback

**Date:** 2026-07-27
**Host:** HM2 (100.109.57.26)
**Base:** R-buf2key (commit d3bd7ed, cf8bd4a)

## Summary

用户终极目标: "仅凭 glm5.2_nv 就能稳住, 不 fallback 到 ms". R-buf2key 实现了 2-key 轮转
(k2→k5), 98.1% 纯 NVCF 成功率. 但仍有 1.9% 两 key 同时失败 → 502.

R-buf5key 扩展为 4-key 轮转 (k2→k5→k3→k4) + ms_gw 最终兜底:
1. 4 个 NVCF key 各走不同代理 IP (mihomo 7895/7899/7896/7897)
2. 每个 key 150s, 总 600s 上限
3. 429 在 2-4s 内快速失败, 实际消耗远小于 150s → 4 key 总实际耗时通常 <30s
4. 4 key 全败后 → ms_gw (ModelScope) 兜底, 不让 CC 拿 502

## Data (改前)

R-buf2key 部署后 1h 数据 (11:02-11:38 UTC+8):
- 54 请求, 53 成功 (98.1%), 1 exhausted (1.9%)
- key2 429 = 22 次 (46%), 全被 key5 救回
- 唯一 1 次 exhausted: req ecf2c7a2 — key2 429 (4s) + key5 "Remote end closed" (42s)
- ms_gw fallback = 0 (buffer 路径绕过 execute_request)

## Changes

### buffer_stream.py
1. `_KEY_ROTATION` 表: 4 个 key 的 caller 映射 [(cc4101-primary,k2), (opencode,k5), (hermes,k3), (openclaw,k4)]
2. `_execute_and_drain`: 按 attempt 索引轮转表, 不再硬编码 "opencode"
3. `_try_ms_gw_fallback` 新方法: 4 key 全败后调 `_ms_fallback_request` 取 ms_gw 流,
   走 `_drain_upstream` → converter → buffer → flush (与 NVCF 成功路径同构)
4. `run()`: exhausted 后先调 `_try_ms_gw_fallback()`, 成功则记 200+ms_fallback, 失败才发 error+502

### docker-compose.yml
- `NVU_BUFFER_MAX_RETRIES=4` (was 2)
- `NVU_BUFFER_TIMEOUT_STAIRS=150,150,150,150` (was 150,150)
- `NVU_BUFFER_TOTAL_DEADLINE_S=600` (unchanged)

### config.py (no code change, env-driven)

## Verification

部署后首个请求 (req=59574d7f):
- attempt 1/4: key2 429 (1.7s) → KEYSWAP
- attempt 2/4: key5 → success (33.7s)
- flush 5011b to CC, verdict=success_tool_call

Monitoring for 3+ key rotation and ms_gw fallback events.
