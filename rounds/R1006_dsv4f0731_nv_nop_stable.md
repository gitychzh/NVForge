# R1006: dsv4f0731_nv NOP — 链路稳定，无参数调整

**日期**: 2026-08-07 17:16 UTC
**模型**: dsv4f0731_nv (deepseek-v4-pro, NVCF pexec)
**容器**: dsvf0731_nv40666 (port 40666)

---

## 状态总结

dsv4f0731_nv 在当前 30min 窗口表现稳定，无需参数调整。

### 核心指标（30min 窗口，n=170）

| 指标 | 值 |
|------|-----|
| SR% | **98.8%** (168/170) |
| 429 计数 | **0** |
| Fallback (hm4104) | **0** (5min 无 fallback 日志) |
| all_tiers_exhausted | 1 |
| zombie_empty_completion | 1 |

### 延迟（per-key 200 平均）

| Key | Count | Avg (ms) | P95 (ms) |
|-----|-------|---------|---------|
| k0 | 35 | 13,406 | 38,600 |
| k1 | 34 | 9,523 | 18,169 |
| k2 | 35 | 9,785 | 19,659 |
| k3 | 33 | 9,701 | 18,230 |
| k4 | 31 | 8,646 | 13,379 |

### 6h 趋势

| 指标 | 值 |
|------|-----|
| 总量 | 1,656 |
| 成功 | 1,615 |
| ATE | 41 (2.5%) |
| 429 | 0 |
| **SR%** | **97.5%** |

### 上游类型

100% nvcf_pexec（本窗口无 integrate 流量）

### 错误分类

| error_type | count | avg_elapsed_ms |
|-----------|-------|---------------|
| all_tiers_exhausted | 1 | 180,074 |
| zombie_empty_completion | 1 | 7,050 |

两个错误均在 **k0** 上发生。

### 容器健康

```
/health → {"status": "ok"}
容器运行 24h
```

---

## 分析

1. **SR=98.8%** 远超 95% 阈值 — 链路非常健康。
2. **0 429** — 冷却策略 (KEY_COOLDOWN=30, TIER_COOLDOWN=90, NVU_KEYMGR_429_BASE=120) 有效。
3. **Fallback 0** — hm4104 未触发任何 fallback，说明 dsv4f0731_nv 持续可用。
4. **k0 略劣化**：avg=13.4s (vs 平均 10.2s)，P95=38.6s (vs 平均 21.6s)，且两例错误都在 k0。但仅 1 ATE + 1 zombie，尚不构成关键问题。
5. **无 integrate 流量** — 当前窗口无法对比 pexec/integrate 表现。NV_KEY_INTEGRATE_KEYS 设定 dsv4f0731_nv:3 表示 k3 走 integrate，但本窗口内 k3 全部通过 pexec 成功（33/33, avg=9,701ms）。

### 当前参数

| 参数 | 当前值 |
|------|--------|
| UPSTREAM_TIMEOUT | 90s |
| TIER_TIMEOUT_BUDGET_S | 180s |
| NVU_TIER_BUDGET_DSV4F0731_NV | 180s |
| KEY_COOLDOWN_S | 30s |
| TIER_COOLDOWN_S | 90s |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 3 |
| NVU_EMPTY_200_FASTBREAK | 3 |
| NVU_KEYMGR_429_BASE_COOLDOWN | 120s |
| NVU_KEYMGR_429_MAX_COOLDOWN | 120s |
| NVU_KEYMGR_CONN_BASE_COOLDOWN | 30s |
| NVU_KEYMGR_CONN_LONG_COOLDOWN | 120s |
| NVU_PROBE_TIMEOUT | 10s |
| MIN_OUTBOUND_INTERVAL_S | 5s |

---

## 结论

**NOP** — 链路稳定，无参数调整。

dsv4f0731_nv 当前表现优秀（SR=98.8%, 0 429, 0 fallback），无需任何参数变更。

### 下一步建议

1. **关注 k0 趋势** — 如果未来窗口 k0 持续劣化（avg > 20s 或错误增多），可考虑：
   - 将 k0 降级为备选 (NVU_KEYMGR_CONN_BASE_COOLDOWN 惩罚) 
   - 或取消 integrate 分配 (当前 k3 走 integrate，但本窗口无 integrate 流量)
2. **增加 integrate 采样观察** — 在有 integrate 流量的窗口检查 k3 (integrate key) 表现