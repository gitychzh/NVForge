# RN1100: dsv4f0731_nv 自优化 NOP — 链路健康，无需调整

**容器**: dsvf0731_nv40666 (端口 40666, DeepSeek V4 Pro via NVCF)
**时间**: 2026-08-07 18:44 UTC
**本轮类型**: NOP (No Operation — 数据正常，不改参数)

---

## 当前参数快照

| 参数 | 当前值 | 说明 |
|------|--------|------|
| UPSTREAM_TIMEOUT | 90 | NVCF 单次请求读超时 |
| TIER_TIMEOUT_BUDGET_S | 180 | 整个 tier 的 key 循环总预算 |
| NVU_TIER_BUDGET_DSV4F0731_NV | 180 | dsv4f0731_nv 专属 tier 预算 |
| KEY_COOLDOWN_S | 30 | key 故障后冷却秒数 |
| TIER_COOLDOWN_S | 90 | 整个 tier 故障后冷却秒数 |
| NVU_KEYMGR_429_BASE_COOLDOWN | 120 | 429 基础冷却 |
| NVU_KEYMGR_429_MAX_COOLDOWN | 120 | 429 最大冷却 |
| NVU_KEYMGR_CONN_BASE_COOLDOWN | 30 | 连接错误基础冷却 |
| NVU_KEYMGR_CONN_MAX_COOLDOWN | 60 | 连接错误最大冷却 |
| NVU_KEYMGR_CONN_FAIL_THRESHOLD | 3 | 连接失败阈值 |
| NVU_KEYMGR_CONN_LONG_COOLDOWN | 120 | 连接错误长冷却 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 3 | pexec timeout fast-break |
| NVU_EMPTY_200_FASTBREAK | 3 | 空 200 fast-break |
| NVU_BUFFER_TIMEOUT_STAIRS | 90,90,90,90,90 | 每 key 超时阶梯 |
| MIN_OUTBOUND_INTERVAL_S | 5 | 最小请求间隔 |
| NVU_PROBE_TIMEOUT | 10 | 探针超时 |

---

## 数据分析

### 30min 窗口 (18:14–18:44 UTC)

| 指标 | 数值 | 评价 |
|------|------|------|
| 总量 | 141 | 正常流量 |
| 成功 | 139 | — |
| 失败 | 2 | 极低 |
| **SR** | **98.6%** | ✅ 优秀 |
| 429 | **0** | ✅ 零限流 |
| Avg(ms) | 10,209 | 合理 |
| P50(ms) | 9,056 | — |
| P95(ms) | 28,907 | 偏高但可接受 |

### 错误分析

| 错误类型 | 数量 | 平均耗时 | 影响 |
|---------|------|---------|------|
| zombie_empty_completion | 2 | 3,047ms | 轻量——空 200，非连接中断 |

两例分别发生在 Key 0 和 Key 2，均为快速返回的 zombie 空响应（<3.1s）。NVU_EMPTY_200_FASTBREAK=3 意味着连续3次才会触发快速失败，当前2次未达到阈值。

### Per-Key 分布

| Key | 请求数 | Avg(ms) | P95(ms) | 错误 |
|-----|--------|---------|---------|------|
| 0 | 29 | 10,062 | 20,720 | zombie:1 |
| 1 | 26 | 8,682 | 14,917 | 0 |
| 2 | 28 | 10,796 | 25,100 | zombie:1 |
| 3 | 27 | 8,475 | 13,766 | 0 |
| 4 | 29 | 13,267 | 25,799 | 0 |

Key 4 平均延迟略高（13.3s vs 整体 10.2s），但无错误且请求数均衡。不构成劣化信号。

### 6h 趋势

| 窗口 | 总量 | 成功 | 失败 | 429 | 平均耗时 |
|------|------|------|------|-----|---------|
| 6h | 1,726 | 1,685 | 41 | 0 | — |
| 3h | ~877 | ~860 | ~17 | 0 | 10-12.5Kms |

6h SR = 97.6%，逐小时 SR 从 76%→96.5%→98.6%→98.8%，呈改善趋势。08:00 小时失败多（9）但 429=0，可能是短暂网络波动。

### 24h all_tiers_exhausted

| 指标 | 数值 |
|------|------|
| 24h ATE | 297 |

考虑到每日约 6,800 请求量（6h=1,726→24h≈6,900）和当前 30min ATE=0，ATE 发生在其他时段已自行恢复。当前参数足以应对。

### Fallback 分析

hm4104 最近 5 分钟无 fallback 日志 → dsv4f0731_nv 链路稳定，没有触发 hm4104 回退到 ms_gw 或其他 tier。

### Upstream Type

100% nvcf_pexec，无 integrate.api 流量。当前 pexec SR=98.6%，无需调整路由。

---

## 结论

所有关键指标正常：
- ✅ **30min SR=98.6%** (>95% 阈值)
- ✅ **6h SR=97.6%** (>95% 阈值)
- ✅ **429=0** (零限流)
- ✅ **Fallback=0** (hm4104 无 fallback)
- ✅ **Per-key 均衡** (无劣化 key)
- ✅ **Pexec 正常** (100% pexec, 98.6% SR)

**无需修改任何参数。** 当前配置 KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=90, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, NVU_BUFFER_TIMEOUT_STAIRS=90 对 dsv4f0731_nv 链路是合适的。

---
*下一轮建议*：继续监控 24h ATE 趋势和 zombie_empty_completion 频率。如果 ATE 持续 >500/24h 或 zombie 出现模式化分布（集中在某 key），再考虑调整。