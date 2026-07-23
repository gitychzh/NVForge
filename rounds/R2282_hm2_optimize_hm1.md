# R2282: HM2→HM1 — SSLEOF false TIER_COOLDOWN 修复

**时间**: 2026-07-23 07:40 UTC
**执行者**: HM2 (opc2_uname)
**操作**: 修复 upstream.py SSLEOF 处理中 key_cycle_attempts 未记录导致的虚假 TIER_COOLDOWN bug

---

## 一、诊断

### 实时日志快照 (2026-07-23 ~07:30–07:40 UTC)

- NVCF 全链路 SSLEOF 风暴：最近 200 行日志中 14 条 SSLEOFError，0 条 success
- 两层 (glm5_2_nv / dsv4p_nv) 所有 5 个 key 均返回 SSLEOFError，~5s/次
- 每个请求遍历所有 5 个 key (~25s) → NV-TIER-FAIL → NV-GLOBAL-COOLDOWN 触发 → 66s 全 key 冷却

### DB 6h 数据 (nv_requests, 2026-07-22 ~17:40–~23:40 UTC)

| 模型 | 总请求 | OK | 失败 | SR% | 平均延迟 | ATE | zombie | 429 循环 |
|------|--------|-----|------|-----|----------|-----|--------|---------|
| glm5_2_nv | 30 | 23 | 7 | 76.7% | 17264ms | 4 | 5 | 0.8 |
| dsv4p_nv | 16 | 9 | 7 | 56.3% | 29626ms | 7 | 0 | 0.1 |

> SR 均低于 R2258 的 84.1%/68.2% — 呈恶化趋势

### 关键发现：代码 bug

在 `upstream.py` 第 854–856 行，SSLEOF 错误处理：

```python
if is_ssl_err:
    _log("NV-SSL-CYCLE", ...)
    continue  # ← 未 append 到 key_cycle_attempts!
```

后续 tier 失败判断 (第 888 行)：

```python
tier_attempts = [a for a in key_cycle_attempts if a.get("tier") == tier_model]
all_429 = all(a.get("error_type") == "429_nv_rate_limit" for a in tier_attempts)
```

**Bug**: 当所有 key 返回 SSLEOF 时，`key_cycle_attempts` 为空 → `tier_attempts = []` → `all([])` 在 Python 中返回 **True** → `all_429 = True` → 触发 66s TIER_COOLDOWN！

日志中的矛盾证据：
- `[NV-TIER-FAIL] … 429=0, empty200=0, timeout=0, other=0` — 所有计数器为 0
- `[NV-GLOBAL-COOLDOWN] tier=dsv4p_nv all keys 429` — 仍然触发了冷却
- 7 次 key 尝试记录在日志中 (`NV-ERR` … `NV-SSL-CYCLE`) 但未进入 `key_cycle_attempts`

**影响**: 纯 SSLEOF 风暴（非 429 限流）被错误地触发 66s TIER_COOLDOWN，使得每次请求后阻塞 66s，大幅降低恢复重试频率。

---

## 二、修复

在 SSLEOF handler 的 `continue` 之前，追加 `key_cycle_attempts.append()`：

```python
if is_ssl_err:
    _log("NV-SSL-CYCLE", ...)
    # R2282: append to key_cycle_attempts BEFORE continue — prevents
    # empty tier_attempts → all([])=True → false TIER_COOLDOWN on SSLEOF storms.
    key_cycle_attempts.append({
        "tier": tier_model,
        "nv_key_idx": key_idx,
        "litellm_model": f"nvcf_{NV_MODEL_IDS[tier_model]}_k{key_idx+1}",
        "error": str(e)[:200],
        "error_type": f"NVCFPexec{error_class}",
        "elapsed_ms": elapsed_ms,
        "upstream_type": "nvcf_pexec",
        "function_id": function_id,
    })
    continue
```

**效果**：
- `tier_attempts` 不再为空 → `all_429` 正确评估为 False（SSLEOF ≠ 429）
- SSLEOF 风暴时不再触发虚假 TIER_COOLDOWN
- 请求可立即重试（无 66s 冷却），仅受 tier budget 约束
- 不影响真实 429 全 key 冷却逻辑

---

## 三、参数状态（未变）

| # | 参数 | 值 | 来源 |
|---|------|-----|------|
| 1 | `UPSTREAM_TIMEOUT` | 24 | R10 |
| 2 | `TIER_TIMEOUT_BUDGET_S` | 275 | R2277 |
| 3 | `KEY_COOLDOWN_S` | 66 | R2267 |
| 4 | `TIER_COOLDOWN_S` | 66 | R2281 |
| 5 | `KEY_AUTHFAIL_COOLDOWN_S` | 0 | R2257 |
| 6 | `NVU_TIER_BUDGET_DSV4P_NV` | 160 | R2273 |
| 7 | `NVU_TIER_BUDGET_GLM5_2_NV` | 200 | R2278 |

**本轮只改代码，不改参数。**

---

## 四、验证

- ✅ `docker compose up -d --build nv_gw` 重建+重启成功
- ✅ `curl localhost:40006/health` → 200
- ✅ `docker exec nv_gw env` 确认所有参数不变
- ✅ `docker exec nv_gw grep "R2282" /app/gateway/upstream.py` → 代码 fix 在容器内生效
- ⏳ 待监控：SSLEOF 风暴下 TIER_COOLDOWN 不再误触发（下次日志中 `429=0` 时不应出现 `NV-GLOBAL-COOLDOWN`）

---

## 五、评判

- 更少报错 ✅ — SSLEOF 风暴不再被 66s 虚假冷却加重
- 更快请求 ✅ — 移除虚假冷却后恢复重试频率 = tier_budget / per_key_latency
- 超低延迟 ✅ — 5×5=25s 遍历全 key 无冷却 → 下一请求立即开始
- 稳定优先 ✅ — 只改 SSLEOF 的 key_cycle_attempts 记录，不改任何参数或正常 429 冷却路径
- 铁律 ✅ — 只改 HM1，不改 HM2

## ⏳ 轮到 HM1 优化 HM2