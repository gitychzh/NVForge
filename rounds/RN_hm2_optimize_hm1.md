# R713: HM2→HM1 — UPSTREAM_TIMEOUT 33→36 (+3s，NVCFPexecTimeout 边缘救回)

## TL;DR
Post-restart NVCFPexecTimeout 精确绑定 UPSTREAM_TIMEOUT=33（avg=33,400ms, min=33,235ms, max=33,636ms），+3s 到 36 捕获 33-36s 边缘。6h: 347req/250OK(72.0%)/97ATE(28.0%)。Post-restart: 21req/17OK(81.0%)/4ATE(全双 tier 耗尽)。Fallback 正常（tier_chain dsv4p_nv+glm5_2_nv），dsv4p_nv health 0.25-0.5 波动，glm5_2_nv health 0.5-0.7 救回。BUDGET=110 >> 36+36=72s 安全。FASTBREAK=1 不变。单参数每轮；铁律：只改 HM1 不改 HM2。

---

## 数据

### 容器状态
- 容器：`nv_gw`，Up 30 minutes (healthy) → 重启后 5 seconds
- DB：`logs_db`，Up 16 hours (healthy)
- 重启时间：~2026-07-05 06:30 UTC（R711 部署）

### 环境变量（改前）
```
UPSTREAM_TIMEOUT=33          ← R711: 30→33
TIER_TIMEOUT_BUDGET_S=110    ← R706: 94→110
MIN_OUTBOUND_INTERVAL_S=0
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=25
NVU_PEXEC_TIMEOUT_FASTBREAK=1 ← R709: 2→1
NVU_PEER_FALLBACK_TIMEOUT=45
NVU_EMPTY_200_FASTBREAK=2
NVU_CONNECT_RESERVE_S=0
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=40
FALLBACK_HEALTH_THRESHOLD=0.10
```

### DB 摘要（6h）
| 指标 | 值 |
|------|-----|
| 总量 | 347 req |
| OK | 250 (72.0%) |
| ATE | 97 (28.0%) |
| avg_dur | 33,585ms |
| max_dur | 122,312ms |

### 按小时 SR
| hour | total | ok | ate | sr_pct |
|------|-------|-----|-----|--------|
| 19:00 | 114 | 99 | 15 | 86.8% |
| 20:00 | 14 | 8 | 6 | 57.1% |
| 21:00 | 15 | 8 | 7 | 53.3% |
| 22:00 | 28 | 13 | 15 | 46.4% |
| 23:00 | 9 | 8 | 1 | 88.9% |
| 00:00 | 2 | 2 | 0 | 100.0% |
| 01:00 | 13 | 8 | 5 | 61.5% |
| 02:00 | 49 | 35 | 14 | 71.4% |
| 03:00 | 27 | 20 | 7 | 74.1% |
| 04:00 | 21 | 14 | 7 | 66.7% |
| 05:00 | 20 | 7 | 13 | 35.0% |
| 06:00 | 29 | 22 | 7 | 75.9% |
| 07:00 | 6 | 6 | 0 | 100.0% |

### Post-restart（~06:30+ UTC，35 min）
| 指标 | 值 |
|------|-----|
| 总量 | 21 req |
| OK | 17 (81.0%) |
| ATE | 4 (19.0%) |
| avg_dur | 34,663ms |

**Post-restart ATE 全部为双 tier 耗尽（tiers_tried_count=2）**，fallback 正常工作（零单 tier ATE）。

### ATE 分层（6h）
| tiers_tried_count | cnt | avg_dur | fallback_attempted |
|-------------------|-----|---------|-------------------|
| 1 | 70 | 47,103ms | f（全未尝试） |
| 2 | 27 | 104,169ms | — |

单 tier ATE 分布：start_tier_idx=1 (dsv4p_nv): 58, avg 50,383ms；start_tier_idx=3 (glm5_2_nv): 11, avg 33,847ms；start_tier_idx=0: 1, avg 2,682ms。

### NVCFPexecTimeout 分布（6h）
| 指标 | 值 |
|------|-----|
| 总量 | 65 |
| avg_ms | 29,636ms |
| max_ms | 40,492ms |

**Post-restart NVCFPexecTimeout（关键发现）**：
| 指标 | 值 |
|------|-----|
| 总量 | 7 |
| avg_ms | 33,400ms |
| min_ms | 33,235ms |
| max_ms | 33,636ms |

**精确定位**：所有 7 个 post-restart NVCFPexecTimeout 均落在 33,235-33,636ms，avg=33,400ms。这是 UPSTREAM_TIMEOUT=33 的绑定约束——NVCF 端 function 返回时间 >33s 被代理侧截断，并非 NVCF 端真正的超时。

### dsv4p_nv 成功延迟分桶（6h）
| bucket | cnt |
|--------|-----|
| <=5s | 3 |
| 5-10s | 9 |
| 10-15s | 4 |
| 15-20s | 12 |
| 20-25s | 13 |
| 25-30s | 8 |
| **30-33s** | **6** (all direct success, no fallback) |
| 33-35s | 3 |
| 35-40s | 9 |
| 40-50s | 18 |
| 50-60s | 12 |
| >60s | 9 |

**30-33s 桶 6 个全部直接成功（无 fallback）**——说明 dsv4p_nv 在 30-33s 区间确有成功窗口。33-35s 桶 3 个成功（可能通过 fallback 或 rare 直接成功）。UPSTREAM_TIMEOUT=33 截断了 33-36s 窗口。

### Post-restart 成功延迟分桶（dsv4p_nv）
| bucket | cnt |
|--------|-----|
| <=5s | 1 |
| 5-10s | 2 |
| 30-33s | 1 |
| 35-40s | 2 |
| 40-50s | 5 |

### Fallback 统计（post-restart OK）
| fallback_occurred | cnt | avg_dur | max_dur |
|-------------------|-----|---------|---------|
| f（直接成功） | 10 | 6,878ms | 30,896ms |
| t（fallback 救回） | 7 | 42,280ms | 47,235ms |

### 日志分析（改前，post-restart）
```
tier_chain=['dsv4p_nv', 'glm5_2_nv'] (dynamic fallback) — 所有请求
dsv4p_nv health: 0.25-0.5 (波动)
glm5_2_nv health: 0.5-0.7 (稳定救回)

典型失败路径：
[06:36:27] NV-KEY dsv4p_nv k5 → NVCFPexecTimeout @33,810ms
[06:36:27] NV-PEXEC-FASTBREAK dsv4p_nv → FASTBREAK=1 saved remaining keys
[06:37:00] NV-FALLBACK → glm5_2_nv
[06:37:00] NV-KEY glm5_2_nv k1 → NVCFPexecTimeout @33,742ms
[06:37:34] NV-ALL-TIERS-FAIL (67,595ms) — 双 tier 耗尽

典型成功路径（fallback）：
[06:48:28] NV-KEY dsv4p_nv k4 → NVCFPexecTimeout @33,342ms
[06:48:28] NV-FALLBACK → glm5_2_nv
[06:48:33] NV-SUCCESS glm5_2_nv k5 (5.5s)
[06:48:33] NV-FALLBACK-SUCCESS

典型成功路径（直接）：
[06:44:46] NV-KEY dsv4p_nv k2 → NV-SUCCESS @3.4s
[06:50:14] NV-KEY dsv4p_nv k3 → NV-SUCCESS @9.9s
```

---

## 诊断

### 根因：UPSTREAM_TIMEOUT=33 精确绑定 NVCFPexecTimeout
Post-restart 7 个 NVCFPexecTimeout 全部落在 33,235-33,636ms（avg=33,400ms），这是 UPSTREAM_TIMEOUT=33 的绑定约束——NVCF 端 function 响应被代理侧在 33s 截断，超时误差仅 ~400ms。并非 NVCF 端真正的「无限超时」——如果给 +3s 窗口，部分请求可完成。

### 30-33s 成功桶证明边缘存在
6h 窗口内 30-33s 桶有 6 个直接成功（无 fallback），说明 dsv4p_nv pexec 在 30-33s 区间确实有成功窗口。当前 UPSTREAM=33 刚好截断此窗口上限。33-36s 窗口（+3s）可捕获目前被截断的请求。

### BUDGET 安全验证
- 单 tier 最坏：36s (pexec timeout) + 36s (fallback pexec timeout) = 72s
- BUDGET=110 per tier >> 72s，零误杀风险
- FASTBREAK=1：每 tier 仅 1 key 尝试，33s→36s 仅增加 3s 失败路径等待
- 最坏 total：36s (dsv4p) + 36s (glm5_2) + 45s (peer fallback) = 117s << PROXY_TIMEOUT=300s

### 预重启 ATE 说明
6h 窗口内 70 个单 tier ATE 主要来自 pre-restart 时段（20:00-05:00 UTC），此时 NVCF 双 function 健康度同时下降（dsv4p 0.25-0.33, glm5_2 0.5-0.6）。Post-restart 后 fallback 正常，ATE 率从 28.5% 降至 19.0%（虽样本小）。

---

## 决策：UPSTREAM_TIMEOUT 33→36 (+3s)

**理由**：
1. NVCFPexecTimeout 精确绑定 UPSTREAM=33（avg 33,400ms），非 NVCF 端真实超时
2. 30-33s 成功桶 6 个证明边缘存在，+3s 捕获 33-36s 窗口
3. BUDGET=110 per tier >> 36+36=72s，零误杀
4. FASTBREAK=1 确保失败成本 bounded（仅 +3s/ATE）
5. Post-restart fallback 正常，但减少 fallback 次数可降低延迟（fallback 成功 avg 42s vs 直接成功 avg 7s）

**预期效果**：
- 33-36s 窗口内请求从「截断→fallback」转为「直接成功」
- dsv4p_nv 直接成功率提升，减少 glm5_2_nv fallback 负载
- 极端情况（双 tier 同时超时）仍为 ATE，但窗口从 33s→36s 给 NVCF 更多完成时间

---

## 参数历史
| 参数 | 当前值 | 上轮 | 变化 |
|------|--------|------|------|
| UPSTREAM_TIMEOUT | **36** | 33 (R711) | **+3s** |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | 1 (R709) | — |
| TIER_TIMEOUT_BUDGET_S | 110 | 110 (R706) | — |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | 45 | — |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | 0.10 (R708) | — |
| NVU_EMPTY_200_FASTBREAK | 2 | 2 | — |
| MIN_OUTBOUND_INTERVAL_S | 0 | 0 | — |
| KEY_COOLDOWN_S | 25 | 25 | — |
| TIER_COOLDOWN_S | 25 | 25 | — |

**单参数每轮；铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2