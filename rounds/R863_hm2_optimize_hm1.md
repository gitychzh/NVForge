# R863: HM2→HM1 — NOP (38/38 100% 6h SR, zero ATE, zero tier_attempts, peak health sustained)

## 数据收集

| 指标 | 值 |
|------|------|
| 6h 窗口 | 08:00-14:00 UTC |
| 总请求 | 38 |
| OK (200) | 38 (100%) |
| ATE (502) | 0 |
| 其他失败 | 0 |
| key_cycle_429s | 0 (all 38 requests) |
| fallback 触发 | 0 |
| nv_tier_attempts 6h | 0 行 |
| 容器日志错误 | 0 (全部 [NV-SUCCESS] attempt 1/7 first attempt) |
| 容器重启 | 2026-07-08T04:12:50Z (10h+ uptime) |

### 每小时 SR 分布

| 小时 (UTC) | 请求 | OK | ATE | SR |
|------------|------|-----|-----|-----|
| 00:00 | 3 | 3 | 0 | 100% |
| 01:00 | 6 | 6 | 0 | 100% |
| 02:00 | 7 | 7 | 0 | 100% |
| 03:00 | 6 | 6 | 0 | 100% |
| 04:00 | 7 | 7 | 0 | 100% |
| 05:00 | 6 | 6 | 0 | 100% |
| 06:00 | 3 | 3 | 0 | 100% |

### nv_tier_attempts 6h

```
 tier | error_type | cnt | avg_ms | max_ms
------+------------+-----+--------+--------
(0 rows)
```

**零错误** — 无 NVCFPexecTimeout、无 empty_200、无 429、无任何 tier 尝试失败。

### 日志摘要

全部请求均：
- `[NV-SUCCESS] tier=glm5_2_nv` — 100% 第一键成功
- `attempt 1/7` — 从未回退到第二键
- `tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback, health={...})` — FALLBACK_GRAPH 双向健康
- 延迟范围：`1.9s`（最快）到 `58.3s`（最慢），中位数 ~7-8s

### 当前 HM1 配置

| 参数 | 值 | 状态 |
|------|------|------|
| UPSTREAM_TIMEOUT | 66 | floor |
| TIER_TIMEOUT_BUDGET_S | 114 | 历史最优 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 1 | floor |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| KEY_COOLDOWN_S | 25 | floor |
| TIER_COOLDOWN_S | 25 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | synced with UPSTREAM |

## NOP 决策清单 (全部 6 gate 通过)

| Gate | 条件 | 状态 |
|------|------|------|
| 1. ATE tiers_tried | 0 ATE → 空真 | ✓ 通过 |
| 2. 零 single-tier ATE | 0 single-tier ATE | ✓ 通过 |
| 3. NVCFPexecTimeout buffer ≥3s | 0 timeout → 空真 | ✓ 通过 |
| 4. FALLBACK_GRAPH 双向 | tier_chain 双向 normal | ✓ 通过 |
| 5. Fallback 100% SR | 0 fallback 触发 → 空真 | ✓ 通过 |
| 6. 参数已达 floor/最优 | 全部 floor, FORCE_STREAM=UPSTREAM 同步 | ✓ 通过 |

**结论**: NOP。无任何参数需要调整，系统处于历史最佳状态（与 R834–R862 共 28 轮 NOP 持平，此为第 29 轮）。

---

## 优化建议

无。系统连续 29 轮 NOP（R834–R863），峰值健康持续。等待信号：NVCFPexecTimeout 绑定、429 surge、DEGRADED 复发、或上游延迟恶化 → 才需参数调整。

## ⏳ 轮到 HM1 优化 HM2