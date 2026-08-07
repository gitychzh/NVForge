# RN1102: dsv4f0731_nv 自优化 NOP — 链路继续健康，无需调整

**容器**: dsvf0731_nv40666 (端口 40666, DeepSeek V4 Pro via NVCF)
**时间**: 2026-08-07 19:40 UTC (03:40 CST)
**本轮类型**: NOP (No Operation — 数据正常，不改参数)

---

## 当前参数快照 (未改动)

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

### 30min 窗口 (19:10–19:40 UTC)

| 指标 | 数值 | 评价 |
|------|------|------|
| 总量 | 156 | 正常流量 |
| 成功 | 153 | — |
| 失败 | 3 | 极低 |
| **SR** | **98.08%** | ✅ 优秀 |
| 429 | **0** | ✅ 零限流 |
| Avg(ms) | 11,283 | 合理 |
| P50(ms) | 9,210 | — |
| P95(ms) | 32,208 | 线上典型值 |

### 错误分析

| 错误类型 | 数量 | 平均耗时 | 影响 |
|---------|------|---------|------|
| zombie_empty_completion | 3 | 12,857ms | 偶发空 200，非系统性 |

三例分布在 Key 2 (34518ms)、Key 3 (1872ms)、Key 4 (2181ms)，平均耗时 12.9s 显著高于 R1101 的 2.6s。Key 2 的 34.5s zombie 较长但仍 < UPSTREAM_TIMEOUT=90，属 NVCF 端返回空内容而非超时截断。NVU_EMPTY_200_FASTBREAK=3 意味着连续 3 次同 key 才触发 fast-break，当前分散在 3 个不同 key，未达阈值。

### Per-Key 分布

| Key | 请求数 | Avg(ms) | P95(ms) | Max(ms) | 错误 |
|-----|--------|---------|---------|---------|------|
| 0 | 33 | 10,116 | 28,034 | 28,034 | 0 |
| 1 | 28 | 11,354 | 21,147 | 21,147 | 0 |
| 2 | 32 | 11,401 | 32,661 | 34,518 | zombie:1 |
| 3 | 31 | 10,214 | 21,306 | 21,306 | zombie:1 |
| 4 | 29 | 13,394 | 30,356 | 30,356 | zombie:1 |

请求数均衡 (28–33)，平均延迟 10–13Kms 均匀。Key 4 avg 略高 (13.4s) 但 error=1 非模式化，不构成为题。

### 6h 趋势

| 窗口 | 总量 | 成功 | 失败 | 429 | SR |
|------|------|------|------|-----|-----|
| 6h | 1,761 | 1,720 | 41 | 0 | 97.67% |
| 3h | 880 | 867 | 13 | 0 | 98.52% |

逐小时 (08:00→11:00 UTC): 96.15%→98.62%→98.76%→97.95%，成功率稳定。08:00 小时失败略多 (3 个) 但已回落。

### 24h all_tiers_exhausted

| 指标 | 数值 |
|------|------|
| 24h ATE | 273 |

从 R1100 的 297 → R1101 的 288 → 本轮 273，呈持续改善趋势。当前 30min ATE=0，键池恢复健康。

### Fallback 分析

hm4104 最近 5 分钟无 fallback 日志 → dsv4f0731_nv 链路稳定，未触发回退到 ms_gw。

### Upstream Type

30min 100% nvcf_pexec (156 req, SR=98.08%)，零 integrate.api 流量。当前全 pexec 路由健康。

### key_cycle_429s

k0=39, k1=117（其余 0）。请求级 429=0，keymgr 捕获的 429 被冷却策略完全吸收。k1 的 117 次 429-cycle 与 R1101 (k1=104) 及 R1100 (k1=112) 基本持平，持续偏高但不穿透，无需干预。

### Finish Reason

tool_calls=124 (79.5%), stop=29 — 长推理/工具调用为主，与 DeepSeek V4 Pro 模型特征一致。

---

## 与上一轮对比

| 指标 | RN1101 (19:00) | RN1102 (19:40) | 变化 |
|------|---------------|---------------|------|
| 30min SR | 98.6% | 98.08% | ↓ 0.5pp |
| 429 | 0 | 0 | — |
| Zombie | 2 | 3 | ↑ 1 |
| Avg(ms) | 11,064 | 11,283 | ↑ 219ms |
| P50(ms) | 9,023 | 9,210 | ↑ 187ms |
| P95(ms) | 26,714 | 32,208 | ↑ 5.5s |
| 6h SR | 97.7% | 97.67% | — |
| 24h ATE | 288 | 273 | ↓ 15 (改善) |

P95 略有上升 (32.2s vs 26.7s)，主要受 Key 2 的 34.5s zombie 拖长。但 SR 仍 > 98%，无系统性劣化信号。

## 结论

所有关键指标正常：
- ✅ **30min SR=98.08%** (>95% 阈值)
- ✅ **6h SR=97.67%, 3h SR=98.52%** (>95% 阈值)
- ✅ **429=0** (零限流)
- ✅ **Fallback=0** (hm4104 无 fallback)
- ✅ **Per-key 均衡** (无模式化劣化 key)
- ✅ **100% pexec, SR 98.08%** (integrate 无需调整)
- ✅ **24h ATE 持续下降** (297→288→273)

**无需修改任何参数。** 当前稳定的参数组合 (KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=90, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, NVU_BUFFER_TIMEOUT_STAIRS=90) 对 dsv4f0731_nv 链路表现良好。

---

*下一轮建议*：继续监控 24h ATE (当前 273，趋势改善) 与 zombie_empty_completion 频率。若 zombie 出现同 key 聚集且连续N轮触发 fast-break，再评估。当前 k1 key_cycle_429s=117 持续偏高，留意是否出现穿透导致请求级失败。