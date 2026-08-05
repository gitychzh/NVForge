# R829: 全 key 不可用 fail-fast — 缩短 buffer 无谓重试

**日期**: 2026-08-05
**主机**: HM2 (100.109.57.26)
**目标**: 提高 NV 成功请求吞吐量 — 失败请求从 ~465s 降到 <30s

## 问题数据 (R828 后 6h 窗口, cc4101-primary)

| 指标 | 值 |
|---|---|
| 总请求 | 238 |
| 成功 (NV) | 213 |
| 失败 | 18 (14 buffer_exhausted + 2 all_tiers + 2 client_gone) |
| 成功请求 avg | 45s |
| **失败请求 avg** | **465s** (buffer_exhausted) |
| 失败请求 max | 554s |
| per-attempt SR | 97.8% (221/226) |
| per-call SR | 92.2% (213/231) |

14 个 buffer_exhausted × 465s = 6510s (~108min) 浪费, 本可跑 ~145 个成功请求。

## 根因

`buffer_stream.py:run()` 固定跑 5 次 attempt, 每次调 `_try_glm52_mode_chain`。
当全 5 key 都在 cooling 状态 (429 风暴/连续 conn error) 时:
- chain 内部跳过 cooling key → 秒回 all_keys_exhausted
- buffer 层无视此信号 → 继续 attempt + backoff (5s/10s/15s)
- 5 次 attempt + WaitQueue 180s = ~200s+ 纯浪费
- 最终 ms_gw fallback 时 cc4101 deadline 已耗大半

## 改动

### 1. buffer_stream.py — 全 key cooling fail-fast

在 for 循环中 `_execute_and_drain` 返回后, 检查 KeyManager 是否所有 key 都 cooling。
全 cooling → 直接 break, 不继续无谓 attempt。

```python
# R829: 全 key cooling → fail-fast
_all_cooling = all(
    not _KeyManager.is_available(self.request_model, k)
    for k in range(NVU_NUM_KEYS)
)
if _all_cooling:
    _log("NV-BUFFER-ALL-COOLING", ...)
    break
```

### 2. buffer_stream.py — WaitQueue 前长冷却检查

全 key 长冷却 (>30s remaining) → 跳过 WaitQueue, 直接走 ms_gw fallback。
短冷却 (≤30s, transport error 5s penalty) 不跳过, 仍走 WaitQueue 等恢复。

### 3. imports

- `from .config import NVU_NUM_KEYS` (已有, 加入 import)
- `from .key_manager import KeyManager as _KeyManager`

## 不改的部分

- KeyManager 本身 (cooling 逻辑已正确)
- upstream.py (chain 内部已正确跳过 cooling key)
- nv_breaker.py (R828 breaker 独立运作)
- cc4101 (fallback 逻辑独立)

## 预期效果

| 场景 | 改前 | 改后 | 节省 |
|---|---|---|---|
| 全 key 429 风暴 | ~450s + 180s WaitQueue | ~5s → ms_gw | ~625s |
| 全 key conn error (3+ fails) | ~450s + 180s | ~5s → ms_gw | ~625s |
| 部分 key 可用 (正常) | 不变 | 不变 | 0 |
| NVCF 瞬态风暴 (5s penalty) | 不变 (5s 后恢复) | 不变 | 0 |

## 验证

- [x] `python3 -c "py_compile.compile(...)"` → syntax OK
- [x] `docker compose restart nv_gw` → OK
- [x] `curl /health` → ok, 5 keys, models 含 glm5_2_nv
- [x] Python introspection: `ALL-COOLING` in src = True, `SKIP-WAIT` in src = True, `_KeyManager` in src = True
- [x] E2E: `curl cc4101 /v1/messages` → 200 OK in 4.7s (不回归)
- [ ] 下一窗口日志确认 (待观察)

## 参数快照

无新增参数。全 cooling 判定使用 KeyManager 现有 `is_available()` 和 `get_state()`。
WaitQueue 跳过阈值硬编码 30s (可后续提取为 env)。

## 备份

- `buffer_stream.py.bak.R829`
