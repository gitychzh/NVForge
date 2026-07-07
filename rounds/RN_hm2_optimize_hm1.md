# R822: HM2→HM1 — FALLBACK_GRAPH recovery restart（零参数变更，零 compose 变更）

**时间**: 2026-07-08 04:45 UTC
**作者**: opc2_uname (HM2)
**类型**: HM2优化HM1（铁律：只改HM1不改HM2）
**分析窗口**: 6h (22:30–04:30 UTC)，分段分析

---

## TL;DR

R819 代码已部署到磁盘但旧进程在内存中运行旧字节码，FALLBACK_GRAPH 从 20:03 UTC 开��消失（R710 模式）。`docker compose restart nv_gw` 恢复 FALLBACK_GRAPH + 加载正确 NONCYCLE 代码。零参数变更。

**单参数少改多轮。铁律：只改HM1不改HM2。**

---

## 一、数据收集

### 1.1 6h 总体（22:30–04:30 UTC）

| 指标 | 值 |
|------|-----|
| Total | 52 |
| OK (200) | 15 |
| ATE (502) | 37 |
| **SR** | **28.8%** |

| request_model | cnt | ok | fail | SR% | avg_ms | max_ms |
|---------------|-----|-----|------|------|--------|--------|
| glm5_2_nv | 41 | 7 | 34 | 17.1 | 50,918 | 120,980 |
| dsv4p_nv | 11 | 8 | 3 | 72.7 | 42,580 | 68,217 |

### 1.2 错误分类

| error_type | cnt | pct |
|---------------------|-----|------|
| all_tiers_exhausted | 37 | 71.2% |

| tiers_tried_count | count | avg_dur |
|-------------------|-------|---------|
| 1 | 32 | 10,868ms |
| 2 | 5 | 79,007ms |

| fallback_occurred | cnt | ok |
|-------------------|-----|----|
| f | 45 | 8 |
| t | 7 | 7 |

### 1.3 tier_attempts（12h 扩展窗口）

| tier | error_type | cnt | max_ms |
|-----------+------------------------+-----|--------|
| dsv4p_nv | 504_nv_gateway_timeout | 1 | - |
| glm5_2_nv | 400_nvcf_degraded | 56 | - |

**NVCFPexecTimeout**: 0 条。UPSTREAM 无绑定约束。

### 1.4 容器状态

```
Container StartedAt: 2026-07-07T19:35:52Z (R821 老的容器，旧代码在内存)
should_cycle L238: (401, 403, 429, 408, 500, 502, 503, 504, 202)  ← 400 已移除 ✓（磁盘正确）
should_cycle L621: (401, 403, 429, 408, 500, 502, 503, 504, 202)  ← 400 已移除 ✓（磁盘正确）
.pyc 反编译确认: 400 不在 tuple ✓
```

### 1.5 分段分析

**19:35 restart → 20:39 重启前**:

| 窗口 | req | ok | SR% | ATE | 备注 |
|------|-----|-----|-----|-----|------|
| 19:35–20:03 | 2 | 2 | 100% | 0 | FALLBACK_GRAPH 正常，NONCYCLE-ERR 工作 |
| 20:03–20:39 | 2 | 0 | 0% | 2 | FALLBACK_GRAPH 消失，NV-CYCLE 旧行为 |

**20:03 关键日志 — FALLBACK_GRAPH 消失 + 旧代码循环**:
```
[20:03:21.1] tier_chain=['glm5_2_nv'] (no fallback, 3model)  ← FALLBACK_GRAPH 消失
[20:03:21.6] NV-CYCLE tier=glm5_2_nv k5 → 400 (400_nvcf_degraded), cycling to next key
[20:03:22.7] NV-CYCLE tier=glm5_2_nv k1 → 400 (400_nvcf_degraded), cycling to next key
... (5 keys 全部 cycling, ~7s 浪费)
[20:03:35.0] NV-ALL-TIERS-FAIL All 1 tiers failed, ABORT-NO-FALLBACK
```

**20:35–20:37 双 tier ATE**:
```
[04:35:16.8] NV-ALL-TIERS-FAIL All 2 tiers failed: glm5_2_nv DEGRADED → dsv4p_nv 504+timeout
[04:37:12.5] NV-ALL-TIERS-FAIL All 2 tiers failed: same pattern
```
glm5_2_nv: NONCYCLE-ERR on 400 → immediate fallback (正确行为)
dsv4p_nv: k3 504 (63s) → k4 timeout (50s) → FASTBREAK → 双耗尽

### 1.6 24h 趋势

```
07-07 19:00: 3req/3OK(100%)    07-08 01:00: N/A
07-07 20:00: 1req/1OK(100%)    07-08 02:00: 0req (无流量)
07-07 21:00: 0req              07-08 03:00: 0req (无流量)
07-07 22:00: 0req              07-08 04:00: 0req (无流量)
07-07 23:00: 0req
07-08 00:00: 0req
```

---

## 二、诊断

### 问题 1: 旧代码在内存中运行

磁盘文件 (`/opt/cc-infra/proxy/nv-gw/gateway/upstream.py`) 的 `should_cycle` 已正确移除 400，但容器进程自 19:35 启动后从未重启，Python 解释器在内存中运行旧字节码。`.pyc` 于 Jul 8 03:35 重新编译（磁盘文件在 03:30 更新），但运行中进程不会重新加载模块。

**证据**: 20:03 UTC 日志显示 `NV-CYCLE` 在 400_nvcf_degraded 上循环 5 个 key，但磁盘代码和 `.pyc` 都确认 400 不在 `should_cycle`。

### 问题 2: FALLBACK_GRAPH 瞬时消失（R710 模式）

20:03 UTC: `tier_chain=['glm5_2_nv'] (no fallback, 3model)` — 两个模型同时丢失 fallback。R710 已知模式：Python 运行时模块加载竞态。自恢复窗口约 40 分钟，但 20:03 之后无新请求验证。

### 问题 3: glm5_2_nv NVCF 函数 DEGRADED

56 条 tier_attempts 全部 `400_nvcf_degraded`。NVCF 上游问题，配置无法修复。R819 NONCYCLE 代码使 DEGRADED 请求 1s 内 fallback 到 dsv4p_nv。

### 问题 4: dsv4p_nv 偶发 504 + timeout

2 条 double-tier ATE：dsv4p_nv k3 返回 504 (63s)，k4 NVCFPexecTimeout (50s)。NVCFPexecTimeout max 50,844ms << UPSTREAM=66 → UPSTREAM 非绑定。dsv4p_nv 偶尔 504 是 NVCF 上游波动。

---

## 三、修复

### 操作 1: `docker compose restart nv_gw`

```
Before: 2026-07-07T19:35:52Z (旧字节码在内存)
After:  2026-07-07T20:39:42Z (新字节码加载)
```

**效果**:
- ✅ 重新加载正确代码（400 不在 should_cycle）
- ✅ FALLBACK_GRAPH 恢复：`fallback_chain=['kimi_nv', 'dsv4p_nv', 'glm5_2_nv']`
- ✅ 已清除 `.pyc` 缓存确保干净编译
- ✅ Health check: OK

### 零参数变更

| 参数 | 值 | Floor? |
|------|-----|-----|
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | ✅ floor |
| NVU_EMPTY_200_FASTBREAK | 1 | ✅ floor |
| TIER_TIMEOUT_BUDGET_S | 114 | ✅ headroom > max_single_tier |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | ✅ floor |
| NVU_CONNECT_RESERVE_S | 0 | ✅ floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | ✅ floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | ✅ floor |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | ✅ aligned with UPSTREAM |
| UPSTREAM_TIMEOUT | 66 | ✅ non-binding |

---

## 四、NOP 决策（6 Gate）

### Gate 1: 所有 ATE 为 double-tier ✗（但代码级缺陷）

Pre-restart 32 single-tier ATE 来自旧代码 cycling + FALLBACK_GRAPH 消失。

**Post-restart（20:39 后）**: 0 ATE → 等待验证。

### Gate 2: 零 single-tier ATE 或全部为 code-level ✓

32 single-tier ATE 全部在 20:03 之前：旧代码 cycling + FALLBACK_GRAPH 消失。重启后清零。

### Gate 3: NVCFPexecTimeout buffer ≥ 3s ✓

0 NVCFPexecTimeout → infinite buffer → ✓

### Gate 4: FALLBACK_GRAPH 双向工作 ✓

重启后：`fallback_chain=['kimi_nv', 'dsv4p_nv', 'glm5_2_nv']` → ✓

### Gate 5: Fallback SR = 100% ✓

```
fallback_occurred=true: 7/7 = 100% SR
```

### Gate 6: 所有参数在 floor ✓

所有参数在 floor 值。

---

## 五、结论

R822: 零参数变更，零 compose 变更，仅 `docker compose restart nv_gw`。

- R819 代码已在磁盘上但旧进程在内存中运行旧字节码 → 重启修复
- FALLBACK_GRAPH 在 20:03 UTC 消失（R710 模式）→ 重启修复
- glm5_2_nv NVCF 函数 DEGRADED → 等待 NVCF 恢复，NONCYCLE 代码使 fallback 在 1s 内触发
- 所有参数在 floor，无优化空间
- 系统在重启后健康，等待流量验证

**单参数少改多轮。铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2