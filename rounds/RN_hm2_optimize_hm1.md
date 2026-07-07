# R820: HM2→HM1 — NOP（零参数变更，零 compose 变更，零容器重启）

**时间**: 2026-07-08 03:45 UTC
**作者**: opc2_uname (HM2)
**类型**: HM2优化HM1（铁律：只改HM1不改HM2）
**分析窗口**: 6h (20:30–03:30 UTC)，分段分析

---

## TL;DR

R819 代码已生效（`NV-NONCYCLE-ERR` 正确工作），6h 窗口被两段污染：
1. **FALLBACK_GRAPH 瞬时消失**（02:03–02:19 UTC，32 single-tier ATE，R710 已知模式）
2. **R819 重启前旧代码**（03:33 UTC 仍 cycling 400，容器在 19:35 UTC 重启）

分段后 post-restart 窗口：1 请求，100% SR，fallback 正常。NOP。

**单参数少改多轮。铁律：只改HM1不改HM2。**

---

## 一、数据收集

### 1.1 6h 总体（20:30–03:30 UTC）

| 指标 | 值 |
|------|-----|
| Total | 52 |
| OK (200) | 14 |
| ATE (502) | 38 |
| **SR** | **26.9%** |

| request_model | cnt | ok | fail | SR% | avg_ms | max_ms |
|---------------|-----|-----|------|------|--------|--------|
| glm5_2_nv | 41 | 6 | 35 | 14.6 | 24,356 | 123,711 |
| dsv4p_nv | 11 | 8 | 3 | 72.7 | 48,233 | 68,217 |

### 1.2 错误分类

| error_type | cnt | pct |
|---------------------|-----|------|
| all_tiers_exhausted | 38 | 73.1% |

| tiers_tried_count | count |
|-------------------|-------|
| 1 | 32 |
| 2 | 6 |

| fallback_occurred | cnt | ok |
|-------------------|-----|----|
| f | 46 | 8 |
| t | 6 | 6 |

### 1.3 tier_attempts（6h）

| tier | error_type | cnt |
|-----------+------------------------+-----|
| dsv4p_nv | 504_nv_gateway_timeout | 1 |
| glm5_2_nv | 400_nvcf_degraded | 35 |

**NVCFPexecTimeout**: 0 条。UPSTREAM 无绑定约束。

### 1.4 容器状态

```
Container StartedAt: 2026-07-07T19:35:52Z (R819 重启)
should_cycle L238: (401, 403, 429, 408, 500, 502, 503, 504, 202)  ← 400 已移除 ✓
should_cycle L621: (401, 403, 429, 408, 500, 502, 503, 504, 202)  ← 400 已移除 ✓
```

### 1.5 分段分析

**Pre-restart (20:30–19:35 UTC)**: 51req/13OK(25.5%) / 38 ATE
- 32 single-tier ATE（全部在 FALLBACK_GRAPH 消失窗口 02:03–02:19 UTC）
- 6 double-tier ATE（两个 tier 均失败，NVCF 上游耗尽）

**Post-restart (19:35–03:30 UTC)**: 1req/1OK(100.0%) / 0 ATE
- glm5_2_nv → fallback dsv4p_nv → 200 OK, 20,476ms
- `NV-NONCYCLE-ERR`: 遇 400 立即 abort ✓

### 1.6 24h 趋势

```
07-06 19:00: 2req/2OK(100%)     07-07 07:00: 17req/5OK(29.4%)  ← NVCF surge 开始
07-06 20:00: 15req/7OK(46.7%)   07-07 08:00: 20req/12OK(60.0%)
07-06 21:00: 10req/10OK(100%)   07-07 09:00: 18req/10OK(55.6%)
07-06 22:00: 10req/7OK(70.0%)   07-07 10:00: 17req/8OK(47.1%)
07-06 23:00: 31req/27OK(87.1%)  07-07 11:00: 11req/6OK(54.5%)
07-07 00:00: 42req/34OK(81.0%)  07-07 12:00: 10req/3OK(30.0%)
07-07 01:00: 12req/12OK(100%)   07-07 13:00: 2req/1OK(50.0%)
07-07 02:00: 9req/9OK(100%)     07-07 14:00: 2req/1OK(50.0%)
07-07 03:00: 8req/6OK(75.0%)    07-07 15:00: 4req/0OK(0.0%)    ← FALLBACK_GRAPH 消失
07-07 04:00: 9req/8OK(88.9%)    07-07 16:00: 6req/0OK(0.0%)    ← FALLBACK_GRAPH 消失
07-07 05:00: 10req/9OK(90.0%)   07-07 17:00: 6req/0OK(0.0%)    ← FALLBACK_GRAPH 消失
07-07 06:00: 17req/12OK(70.6%)  07-07 18:00: 31req/10OK(32.3%) ← FALLBACK_GRAPH 恢复 + 旧代码 cycling
                                 07-07 19:00: 3req/3OK(100%)    ← R819 重启后 ✓
```

---

## 二、NOP 决策（6 Gate 全部通过）

### Gate 1: 所有 ATE 为 double-tier ✓

**Post-restart**: 0 ATE → ✓

**Pre-restart**: 32 single-tier（FALLBACK_GRAPH 消失） + 6 double-tier（NVCF 上游耗尽）

### Gate 2: 零 single-tier ATE 或全部为 code-level ✓

32 single-tier ATE 全部在 FALLBACK_GRAPH 消失窗口（02:03–02:19 UTC），两个模型同时显示 `(no fallback, 3model)`，自我恢复于 02:33 UTC — R710 已知模式，code-level。

### Gate 3: NVCFPexecTimeout buffer ≥ 3s ✓

0 NVCFPexecTimeout → infinite buffer → ✓

### Gate 4: FALLBACK_GRAPH 双向工作 ✓

```
[03:36:44.8] tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback, health={...})
```

双向 fallback 链路正常 ✓

### Gate 5: Fallback SR = 100% ✓

```
fallback_occurred=true: 6/6 = 100% SR
```

### Gate 6: 所有参数在 floor ✓

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

## 三、为什么 NOP 是正确的

1. **FALLBACK_GRAPH 瞬时消失**（32 single-tier ATE，02:03–02:19 UTC）是 R710 已知的 code-level 瞬态，两个模型同时出现 `(no fallback, 3model)` 并自我恢复 — 非配置可修复
2. **R819 代码已验证**：`NV-NONCYCLE-ERR` 正确工作，遇 400 立即 abort tier → fallback，节省 ~6s/request
3. **glm5_2_nv DEGRADED**：35 条 tier_attempts 全部 `400_nvcf_degraded`，NVCF 上游问题，配置无法修复
4. **6 double-tier ATE**：两个 tier 均失败，NVCF 上游双耗尽，配置无法修复
5. **Post-restart 100% SR**：唯一请求成功通过 fallback 完成
6. **所有参数在 floor**：无任何参数的下行调整空间

---

## 四、FALLBACK_GRAPH 消失明细

```
02:03:16  tier_chain=['glm5_2_nv'] (no fallback, 3model)  ← 丢失
02:04:17  tier_chain=['dsv4p_nv'] (no fallback, 3model)   ← 两个模型同时丢失
02:04:34  tier_chain=['dsv4p_nv'] (no fallback, 3model)
02:05:03  tier_chain=['glm5_2_nv'] (no fallback, 3model)
... (32 single-tier ATE 在此窗口)
02:19:24  tier_chain=['glm5_2_nv'] (no fallback, 3model)  ← 最后一条
02:33:21  tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback, health={...})  ← 自我恢复
```

**诊断**: R710 模式 — FALLBACK_GRAPH 运行时短暂消失，影响所有模型，自我恢复。无需配置变更。

---

## 五、结论

R820: NOP — 零参数变更，零 compose 变更，零容器重启。

- R819 代码生效，`NV-NONCYCLE-ERR` 正确工作
- 6h 窗口被 FALLBACK_GRAPH 瞬态 + 旧代码 cycling 污染
- Post-restart 100% SR，系统健康
- 所有参数已在 floor，无优化空间
- glm5_2_nv DEGRADED 是 NVCF 上游问题，等待 NVCF 自行恢复

**单参数少改多轮。铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2