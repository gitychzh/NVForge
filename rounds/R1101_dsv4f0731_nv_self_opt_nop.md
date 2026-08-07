# RN1101: dsv4f0731_nv 自优化 NOP — 链路健康，无需调整

**容器**: dsvf0731_nv40666 (端口 40666, DeepSeek V4 Pro via NVCF)
**时间**: 2026-08-07 19:00 UTC
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

### 30min 窗口 (18:30–19:00 UTC)

| 指标 | 数值 | 评价 |
|------|------|------|
| 总量 | 139 | 正常流量 |
| 成功 | 137 | — |
| 失败 | 2 | 极低 |
| **SR** | **98.6%** | ✅ 优秀 |
| 429 | **0** | ✅ 零限流 |
| Avg(ms) | 11,064 | 合理 |
| P50(ms) | 9,023 | — |
| P95(ms) | 26,714 | 线上典型值 |

### 错误分析

| 错误类型 | 数量 | 平均耗时 | 影响 |
|---------|------|---------|------|
| zombie_empty_completion | 2 | 2,649ms | 轻量——空 200，非连接中断 |

两例分别在 Key 0 和 Key 3，均为 <3s 快速返回的 zombie 空响应。NVU_EMPTY_200_FASTBREAK=3 意味着需连续3次才触发快速失败，当前单轮分布未达阈值，属偶发。

### Per-Key 分布

| Key | 请求数 | Avg(ms) | P95(ms) | 错误 |
|-----|--------|---------|---------|------|
| 0 | 27 | 10,563 | 24,245 | zombie:1 |
| 1 | 26 | 11,640 | 33,870 | 0 |
| 2 | 28 | 11,477 | 24,438 | 0 |
| 3 | 26 | 10,228 | 30,702 | zombie:1 |
| 4 | 30 | 11,916 | 25,599 | 0 |

请求数均衡 (26–30)，平均延迟 10–12Kms 均匀，无一 key 劣化。Key 1 P95 略高 (33.9s) 但 error=0，不构成为题。

### 6h 趋势

| 窗口 | 总量 | 成功 | 失败 | 429 | SR |
|------|------|------|------|-----|-----|
| 6h | 1,726 | 1,686 | 40 | 0 | 97.7% |
| 3h | 986 | 977 | 9 | 0 | 99.1% |

逐小时 (08:00→11:00 UTC): 98.8%→98.6%→99.1%→100%，成功率稳定。08:00 小时失败 9 为高峰值但已回落。

**6h tier-attempt 错误分布**: pexec_success 1351, NVCFPexecRemoteDisconnected 115 (avg 40.2s), NVCFPexecTimeout 17 (avg 39.2s), empty_200 16。tier 内部重试吸收了这些错误，请求级 SR 仍达 97.7%。NVCFPexecRemoteDisconnected 平均 40.2s < UPSTREAM_TIMEOUT=90，属 NVCF 端主动断开而非客户端超时截断，重试机制已覆盖。

### 24h all_tiers_exhausted

| 指标 | 数值 |
|------|------|
| 24h ATE | 288 |

与 R1100 (297) 基本持平，且 24h 逐小时分布无聚集（当前 30min ATE=0）。键池在限流窗口内自行恢复，参数充足。

### Fallback 分析

hm4104 最近 5 分钟无 fallback 日志 → dsv4f0731_nv 链路稳定，未触发回退到 ms_gw。

### Upstream Type

30min 100% nvcf_pexec (139 req, SR=98.6%)，零 integrate.api 流量。当前全 pexec 路由健康，无需调整 integrate 分配。

### key_cycle_429s

k0=35, k1=104（其余 0）。请求级 429=0，说明 keymgr 在轮转期间捕获的 429 已被冷却策略吸收，未穿透到请求层。k1 轮转 429 偏高但未导致最终失败，暂不处理。

---

## 结论

所有关键指标正常：
- ✅ **30min SR=98.6%** (>95% 阈值)
- ✅ **6h SR=97.7%**, **3h SR=99.1%** (>95% 阈值)
- ✅ **429=0** (零限流)
- ✅ **Fallback=0** (hm4104 无 fallback)
- ✅ **Per-key 均衡** (无劣化 key)
- ✅ **100% pexec, SR 98.6%** (integrate 无需调整)

**无需修改任何参数。** 当前关键配置 KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=90, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, NVU_BUFFER_TIMEOUT_STAIRS=90, NVU_EMPTY_200_FASTBREAK=3 对 dsv4f0731_nv 链路是合适的。

---

*下一轮建议*：继续监控 24h ATE (当前 288) 与 6h NVCFPexecRemoteDisconnected (115) 趋势。若 ATE >500/24h 或 RemoteDisconnected 占比持续升高，考虑调整连接冷却 (NVU_KEYMGR_CONN_*) 或超时预算。同时留意 key_cycle_429s 中 k1 (104) 是否持续偏高导致未来穿透。