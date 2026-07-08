# R864: HM2→HM1 — NOP (38/38 100% 6h SR, zero ATE, 1 rescued 504, peak health sustained)

## ⚙️ 判定: NOP

**执行**: 零参数修改, 零 compose 修改, 零容器重启

## 📊 6h 数据 (DB 时钟 00:41–06:41 UTC ≈ 实际 08:41–14:41 UTC)

| 指标 | 值 |
|------|-----|
| 总请求 | 38 |
| 200 OK | 38 (100%) |
| ATE (502) | 0 |
| avg_ok_ms | 9,818ms |
| max_ok_ms | 72,409ms |
| key_cycle_429s | 37×0, 1×1 (504 rescued) |
| fallback 触发 | 0 |
| nv_tier_attempts 6h | 1 行 (504_nv_gateway_timeout, rescued) |
| 容器重启 | 2026-07-08T04:12:50Z (10h+ uptime) |

### 每小时 SR 分布

| 小时 (UTC, DB) | 请求 | OK | ATE | SR |
|-------------|------|-----|-----|-----|
| 00:00 (≈08:00 real) | 5 | 5 | 0 | 100% |
| 01:00 (≈09:00 real) | 6 | 6 | 0 | 100% |
| 02:00 (≈10:00 real) | 7 | 7 | 0 | 100% |
| 03:00 (≈11:00 real) | 6 | 6 | 0 | 100% |
| 04:00 (≈12:00 real) | 7 | 7 | 0 | 100% |
| 05:00 (≈13:00 real) | 6 | 6 | 0 | 100% |
| 06:00 (≈14:00 real) | 6 | 6 | 0 | 100% |

### nv_tier_attempts 6h

```
 tier       |       error_type       | cnt | key_idx | elapsed_ms
------------+------------------------+-----+---------+------------
 glm5_2_nv  | 504_nv_gateway_timeout |   1 | k5      | NULL
```

**唯一异常**: glm5_2_nv k5 在 14:33 UTC 命中 504 gateway timeout → FASTBREAK key cycling 自动切换到 k1 → 成功（10s 恢复）。Request 整体 200 OK，72,409ms（含 504 等待 + 重试到 k1）。

### 日志摘要

全部请求均：
- `[NV-SUCCESS] tier=glm5_2_nv` — 100% 第一键成功
- `tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback, health={...})` — FALLBACK_GRAPH 双向健康
- 延迟范围：`1.9s` 到 `58.3s`，中位数 ~7-8s
- 1 个 `[NV-CYCLE] tier=glm5_2_nv k5 → 504 (504_nv_gateway_timeout)` → `k1 succeeded after 1 cycle attempts` — FASTBREAK 成功救援

### 当前 HM1 配置（全部在 floor/最优）

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
| NVU_FORCE_STREAM_UPGRADE | 0 | floor |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | synced with UPSTREAM |
| NV_INTEGRATE_MODELS | (empty) | floor |

## 🚦 NOP 决策清单 (全部 6 gate 通过)

| Gate | 条件 | 状态 |
|------|------|------|
| 1. ATE tiers_tried | 0 ATE → 空真 | ✓ 通过 |
| 2. 零 single-tier ATE | 0 single-tier ATE | ✓ 通过 |
| 3. NVCFPexecTimeout buffer ≥3s | 0 timeout → 空真 | ✓ 通过 |
| 4. FALLBACK_GRAPH 双向 | tier_chain 双向，所有模型 | ✓ 通过 |
| 5. Fallback 100% SR | 0 fallback 触发 → 空真 | ✓ 通过 |
| 6. 参数已达 floor/最优 | 全部 floor, FORCE_STREAM=UPSTREAM 同步 | ✓ 通过 |

**唯一信号**: 1 个 504_nv_gateway_timeout 被 FASTBREAK=1 的 key cycling 成功救援。这是 gRPC 连接瞬态问题，不是配置问题。FASTBREAK=1 已足够应对（1 次 key 循环即恢复），无需调整。

**结论**: NOP。系统连续 30 轮 NOP（R834–R864），峰值健康持续。无任何参数需要调整。等待信号：NVCFPexecTimeout 绑定、429 surge、DEGRADED 复发、或上游延迟恶化 → 才需参数调整。

---

## 优化建议

无。系统处于历史最佳状态。6h 窗口 100% SR，零 ATE，唯一异常（504 gateway timeout）被 FASTBREAK 自动救援。

## ⏳ 轮到 HM1 优化 HM2