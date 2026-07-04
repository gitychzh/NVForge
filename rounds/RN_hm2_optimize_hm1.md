# R714: HM2→HM1 — 零变更轮（R713 UPSTREAM_TIMEOUT=36 刚部署 ~15min，post-restart 100% SR）

## TL;DR
R713 UPSTREAM_TIMEOUT=36 部署仅 15min，post-restart 10req/10OK(100.0%)/0ATE。NVCFPexecTimeout 绑定 UPSTREAM=36（avg 34,153ms, max 36,351ms），fallback 全部救回。dsv4p_nv health 0.75-1.0，glm5_2_nv health 1.0。零变更。单参数每轮；铁律：只改 HM1 不改 HM2。

---

## 数据

### 容器状态
- 容器：`nv_gw`，Up 9 minutes (healthy) → 重启时间 ~07:18 UTC（R713 部署）
- DB：`logs_db`，Up 16 hours (healthy)

### 环境变量（改前=改后，零变更）
```
UPSTREAM_TIMEOUT=36              ← R713: 33→36
TIER_TIMEOUT_BUDGET_S=110        ← R706: 94→110
MIN_OUTBOUND_INTERVAL_S=0
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=25
NVU_PEXEC_TIMEOUT_FASTBREAK=1    ← R709: 2→1
NVU_PEER_FALLBACK_TIMEOUT=45
NVU_EMPTY_200_FASTBREAK=2
NVU_CONNECT_RESERVE_S=0
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=40
FALLBACK_HEALTH_THRESHOLD=0.10
PROXY_TIMEOUT=300
```

### DB 摘要（6h，含 pre-restart）
| 指标 | 值 |
|------|-----|
| 总量 | 349 req |
| OK | 252 (72.2%) |
| ATE | 97 (27.8%) |
| avg_dur | 33,511ms |
| max_dur | 122,312ms |

### Post-restart（~07:18+ UTC，15 min）
| 指标 | 值 |
|------|-----|
| 总量 | 10 req |
| OK | 10 (100.0%) |
| ATE | 0 (0.0%) |
| avg_dur | 29,124ms |
| max_dur | 67,531ms |

### Post-restart 成功延迟分桶（dsv4p_nv）
| bucket | cnt |
|--------|-----|
| 15-20s | 1 |
| 20-25s | 1 |
| **33-36s** | **1** (直接成功，R713 边缘救回确认) |
| 40-50s | 3 |
| >60s | 1 |

### Post-restart fallback 统计
| fallback_occurred | cnt | avg_dur | max_dur |
|-------------------|-----|---------|---------|
| f（直接成功） | 6 | 14,302ms | 35,655ms |
| t（fallback 救回） | 4 | 51,357ms | 67,531ms |

### Post-restart NVCFPexecTimeout（nv_tier_attempts）
| 指标 | 值 |
|------|-----|
| 总量 | 4 |
| avg_ms | 34,153ms |
| min_ms | 33,235ms |
| max_ms | **36,351ms** |

**精确定位**：Post-restart NVCFPexecTimeout max=36,351ms，avg=34,153ms。UPSTREAM_TIMEOUT=36 是新的绑定约束——NVCF 端 function 响应被代理侧在 36s 截断，误差 ~350ms。33-36s 桶已有 1 个直接成功（R713 边缘救回确认）。

### 按小时 SR（6h）
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
| **07:00** | **8** | **8** | **0** | **100.0%** |

### ATE 分层（6h，含 pre-restart）
| tiers_tried_count | cnt | avg_dur | fallback_attempted |
|-------------------|-----|---------|-------------------|
| 1 | 70 | 47,103ms | f（全未尝试） |
| 2 | 27 | 104,169ms | — |

单 tier ATE 分布：start_tier_idx=1 (dsv4p_nv): 58, avg 50,383ms；start_tier_idx=3 (glm5_2_nv): 11, avg 33,847ms。全为 pre-restart 时段。

### 6h 错误类型
| error_type | cnt |
|------------|-----|
| all_tiers_exhausted | 97 |

### 6h 按 upstream_type
| upstream_type | cnt | ok | avg_ttfb | avg_dur |
|---------------|-----|-----|----------|---------|
| nvcf_pexec | 244 | 244 | 22,816ms | 22,851ms |
| (NULL/ATE) | 101 | 4 | 54ms | 60,962ms |
| nv_integrate | 6 | 6 | 4,253ms | 10,984ms |

### 日志分析（post-restart）
```
tier_chain=['dsv4p_nv', 'glm5_2_nv'] (dynamic fallback) — 所有请求正常
dsv4p_nv health: 0.75-1.0 (post-restart warmup)
glm5_2_nv health: 1.0 (稳定)

典型成功路径（fallback）：
[07:22:38] NV-PEXEC-FASTBREAK tier=dsv4p_nv → NVCFPexecTimeout @36,369ms
[07:22:38] NV-FALLBACK → glm5_2_nv
[07:23:09] NV-SUCCESS glm5_2_nv k3 (31s)
[07:23:09] NV-FALLBACK-SUCCESS

典型成功路径（直接）：
[07:17:43] NV-SUCCESS dsv4p_nv k4 @17.8s
[07:19:08] NV-SUCCESS dsv4p_nv k5 @23.6s
[07:21:29] NV-SUCCESS dsv4p_nv k1 @35.6s ← 33-36s 直接成功
```

---

## 诊断

### 系统状态：Post-restart 健康
Post-restart 15min 内 10 req 全部成功（100% SR），fallback 正常救回 4 个 NVCFPexecTimeout。tier_chain 完整（dsv4p_nv+glm5_2_nv），health 值健康（dsv4p_nv 0.75-1.0, glm5_2_nv 1.0）。

### UPSTREAM_TIMEOUT=36 绑定约束确认
Post-restart NVCFPexecTimeout max=36,351ms，avg=34,153ms。UPSTREAM_TIMEOUT=36 是新的绑定约束，NVCF 端 function 响应被代理侧在 36s 截断。33-36s 桶已有 1 个直接成功——R713 的 +3s 边缘救回已确认生效。

### 样本过小，零变更决策
Post-restart 仅 15min，10 req 样本过小，无法得出进一步优化方向的结论。当前 100% SR 且 fallback 正常救回所有 dsv4p_nv 超时请求。需要更长时间窗口（至少 6h）积累数据，才能判断：
1. 33-36s 直接成功比例是否稳定 >0
2. dsv4p_nv 直接成功率是否提升（vs R713 pre-restart）
3. 是否仍有 NVCFPexecTimeout 绑定在 36s（需进一步 +3s 到 39？）

### 6h 窗口 ATE 说明
6h 窗口内 97 ATE 主要来自 pre-restart 时段（19:00-06:00 UTC），此时运行的是 UPSTREAM_TIMEOUT=33（R711）配置。Post-restart（07:00+）零 ATE。需要在更长窗口内观察 UPSTREAM=36 的效果。

---

## 决策：零变更

**理由**：
1. R713 UPSTREAM=36 部署仅 15min，post-restart 样本过小（10 req）
2. Post-restart 100% SR，fallback 正常救回全部 dsv4p_nv 超时
3. 33-36s 直接成功已确认（1 个），R713 边缘救回生效
4. NVCFPexecTimeout 绑定 36s 是新的约束，但需要更多数据判断是否 +3s→39
5. dsv4p_nv health 0.75-1.0，glm5_2_nv health 1.0，双 tier 健康

**下轮关注**：
- Post-restart dsv4p_nv 直接成功率（排除 fallback 救回）
- 33-36s 直接成功比例（R713 验证）
- NVCFPexecTimeout 在 36s 的绑定是否持续

---

## 参数历史
| 参数 | 当前值 | 上轮 | 变化 |
|------|--------|------|------|
| UPSTREAM_TIMEOUT | 36 | 36 (R713) | — |
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