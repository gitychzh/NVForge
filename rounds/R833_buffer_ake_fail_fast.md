# R833: buffer 连续 all_keys_exhausted fail-fast — 补 R829 盲区

**日期**: 2026-08-05
**主机**: HM2 (100.109.57.26)
**目标**: 缩短 R829 fail-fast 未覆盖的"瞬态但持续全挂"场景耗时 (421s → ~190s)

## 问题数据 (R832 后 30min 窗口 20:37 CST)

cc4101-primary SR=97.4% (38/39), 1 个 502 `buffer_exhausted` (421s):
- `req=fcec79e3` 20:26:58 起, 5 attempts × NVCF chain 全返回 `all_keys_exhausted=True`
- 每 attempt chain 内 5 key 依次 RemoteDisc/SSL_EOF/529 → 全败
- 5 次 attempt + backoff 跑满 ~290s → EXHAUSTED → ms_gw fallback 421s 总耗时
- **R829 fail-fast 未触发**: 0 条 `NV-BUFFER-ALL-COOLING` 日志

## 根因

R829 检查 `KeyManager.is_available(k)` (cooling 状态), 但:
- NVCF RemoteDisc/SSL_EOF 触发 `mark_transport_error` → **5s/10s 短惩罚**
- `mark_transport_error` 明确**不累计 conn_count** (key_manager.py:158)
- attempt 间 backoff 5s/10s > penalty 5s → key 在下次 attempt 前已恢复 → `is_available()=True`
- → `_all_cooling = False` → R829 fail-fast 永不触发

R728 的 5s 短惩罚是有意设计 (transport 瞬态, key 后续 100% 成功), 单次瞬态正确。
但**连续多 attempt 全 all_keys_exhausted** 说明这不是单次瞬态, 是 NVCF 持续衰退, R829 该 fail-fast 却没信号。

## 改动 (buffer_stream.py)

### 1. `__init__` 加计数器 (line 89-95)

```python
self._last_all_keys_exhausted = False
self._consecutive_ake_count = 0
```

### 2. `_execute_and_drain` 暴露 chain 信号 (line 344-348)

chain 失败时 `self._last_all_keys_exhausted = bool(chain_result.all_keys_exhausted)`,
chain 成功时清 False。

### 3. for 循环 R829 检查后加 AKE fail-fast (line 566-580)

```python
if self._last_all_keys_exhausted:
    self._consecutive_ake_count += 1
else:
    self._consecutive_ake_count = 0
_ake_fast_threshold = int(os.environ.get("NVU_BUFFER_AKE_FAST_N", "3"))
if self._consecutive_ake_count >= _ake_fast_threshold:
    _log("NV-BUFFER-AKE-FASTM", ...)
    break
```

阈值 `NVU_BUFFER_AKE_FAST_N=3` (env 可调): 连续 3 次 all_keys_exhausted → break。
- 1-2 次仍给重试机会 (瞬态可恢复, E2E 实测 attempt1 fail→attempt2 success)
- 3 次确认持续全挂 → fail-fast, 节省 attempt 4+5 + backoff ≈ ~230s

## 不改的部分

- R829 `_all_cooling` 检查保留 (覆盖长 cooling 场景, R833 覆盖短 penalty 持续场景, 互补)
- KeyManager (transport 5s 短惩罚是 R728 正确设计)
- nv_breaker (R828 独立运作)
- upstream.py / chain 逻辑

## 验证

- [x] `python3 -c "import ast; ast.parse(open(...).read())"` → syntax OK
- [x] `docker compose restart nv_gw` → OK
- [x] `curl /health` nv_gw → ok, 5 keys, pexec models 含 glm5_2_nv
- [x] `curl /health` cc4101 → ok, primary=glm5_2_nv
- [x] E2E `curl cc4101 /v1/messages` → 200 OK in 69s, model 返回 "R833 ok"
- [x] 实测非回归: req=8e17c4f4 attempt1 AKE→count=1 (未达 3)→attempt2 success→flush 2696b
  → **单次瞬态 AKE 不误触发 fail-fast, 重试成功** (设计意图验证)
- [ ] 下一窗口日志确认 (待观察持续全挂场景是否 ~190s 而非 421s)

## 参数快照

新增 env: `NVU_BUFFER_AKE_FAST_N` (default 3, 连续 all_keys_exhausted 阈值)

## 备份

- `buffer_stream.py.bak.R833`

## 预期效果

| 场景 | 改前 (R829 后) | 改后 (R833) |
|---|---|---|
| NVCF 瞬态单 key fail (1-2 次 AKE) | 重试成功 (不变) | 重试成功 (不变) |
| NVCF 持续全挂 (3+ 次 AKE) | 跑满 5 attempt ~421s | 第 3 次 break ~190s |
| 全 key long cooling (429 风暴) | R829 fail-fast ~5s | R829 fail-fast ~5s (不变) |
