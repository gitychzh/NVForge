# R1006: dsv4f0731_nv NOP — 状态健康，无参数修改

**日期**: 2026-08-07 18:32 UTC
**容器**: dsvf0731_nv40666 (port 40666)
**模型**: dsv4f0731_nv (DeepSeek V4 Pro via NVCF pexec)

---

## 当前参数

| 参数 | 值 |
|------|------|
| UPSTREAM_TIMEOUT | 90 |
| TIER_TIMEOUT_BUDGET_S | 180 |
| NVU_TIER_BUDGET_DSV4F0731_NV | 180 |
| KEY_COOLDOWN_S | 30 |
| TIER_COOLDOWN_S | 90 |
| NVU_KEYMGR_429_BASE_COOLDOWN | 120 |
| NVU_KEYMGR_429_MAX_COOLDOWN | 120 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 3 |
| NVU_EMPTY_200_FASTBREAK | 3 |
| NVU_KEYMGR_CONN_BASE_COOLDOWN | 30 |
| NVU_KEYMGR_CONN_FAIL_THRESHOLD | 3 |
| NVU_KEYMGR_CONN_LONG_COOLDOWN | 120 |
| NVU_PROBE_TIMEOUT | 10 |
| PROXY_TIMEOUT | 300 |
| MIN_OUTBOUND_INTERVAL_S | 5 |
| NVU_BUFFER_TIMEOUT_STAIRS | 90,90,90,90,90 |

Upstream: `nvcf_pexec` (100%, integrate=0)

---

## 30min 窗口数据

| 指标 | 值 |
|------|------|
| 请求总数 | 182 |
| 成功数 | 180 |
| 错误数 | 2 |
| **SR%** | **98.9%** |
| Avg Latency | 10,234ms |
| P50 | 8,330ms |
| P95 | 25,951ms |
| Max | 43,648ms |
| 429 | 0 |
| key_cycle_429s | 全部 0 |
| Tier 切换 (tier_attempts) | 0 |
| Fallback (hm4104) | 0 |

### 错误分布

| error_type | 次数 | avg_ms |
|-----------|------|--------|
| zombie_empty_completion | 2 | 2,906 |

分布在 k1(1) 和 k2(1)，无集中模式。

### Per-key 延迟

| Key | Count | Avg(ms) | P95(ms) |
|-----|-------|---------|---------|
| k0 | 36 | 9,931 | 19,279 |
| k1 | 34 | 9,046 | 14,814 |
| k2 | 34 | 9,111 | 20,323 |
| k3 | 35 | 10,849 | 22,384 |
| k4 | 41 | 12,251 | 34,651 |

k4 略慢(avg+20%, P95+60%)，但无错误、无 TE。

### Finish Reason

| reason | 次数 |
|--------|------|
| tool_calls | 154 |
| stop | 26 |

---

## 趋势

| 窗口 | 总量 | 成功 | 错误 | SR% | Avg(ms) |
|------|------|------|------|------|---------|
| 30min | 182 | 180 | 2 | 98.9% | 10,234 |
| 1h (10-11 UTC) | 188 | 186 | 2 | 98.9% | 10,341 |
| 1h (09-10 UTC) | 363 | 358 | 5 | 98.6% | 9,890 |
| 1h (08-09 UTC) | 260 | 251 | 9 | 96.5% | 12,495 |
| 1h (07-08 UTC) | 127 | 124 | 3 | 97.6% | 12,668 |
| 6h | 1,730 | 1,688 | 42 | 97.6% | - |
| 24h ATE | - | - | 303 | - | - |

---

## 分析

**积极信号**:
1. SR 98.9% — 稳定优秀
2. 0 次 429 — key pool 无压力
3. 0 次 tier 切换 — 所有请求一次命中，无需 key 循环
4. 0 fallback — hm4104 不需要切 ms_gw
5. 全部 nvcf_pexec — integrate 已完全取消，无路由复杂性
6. 延迟稳定在 8-10s P50, 20-26s P95 — 与之前窗口持平

**微小异常**:
- zombie_empty_completion × 2 — 偶发，分布在两个不同 key，无集中模式
- k4 P95=34.7s (vs 其他 key 14-22s) — 偏高但不构成问题

**结论**: **NOP — 无需修改参数**。所有指标健康，无退化信号。24h ATE=303 值得观察趋势，但当前窗口无 TE 发生。

---

## 下一步建议

1. 继续每日监控，如果 SR 低于 95% 或 ATE 持续上升再调参
2. 关注 k4 延迟趋势 — 如果 k4 持续 P95>30s 且错误增加，考虑增加 k4 的冷却或排查 SOCKS5 链路
3. 关注 zombie_empty_completion 频率 — 如果频率上升（>5/30min），考虑降低 NVU_EMPTY_200_FASTBREAK 从 3→2