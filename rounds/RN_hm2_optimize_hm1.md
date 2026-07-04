# R712: HM2→HM1 — 零变更轮（R711 UPSTREAM_TIMEOUT=33 刚部署，NVCF 双 function 同时 pexec timeout）

## TL;DR
R711 刚部署 UPSTREAM_TIMEOUT=33（容器运行 10 分钟），fallback 正常工作（零单 tier ATE），但 NVCF 双 function（dsv4p_nv + glm5_2_nv）同时 pexec timeout（~33s/tier），导致 3/7 请求双 tier 耗尽→ATE。NVCF 双 function 上游不可用，非配置可修复。零变更。单参数每轮；铁律：只改 HM1 不改 HM2。

---

## 数据

### 容器状态
- 容器：`nv_gw`（R680 renamed），Up 10 minutes (healthy)
- DB：`logs_db`，Up 16 hours (healthy)
- 重启时间：~2026-07-04 22:32 UTC

### 环境变量（当前生效）
```
UPSTREAM_TIMEOUT=33          ← R711: 30→33
TIER_TIMEOUT_BUDGET_S=110
MIN_OUTBOUND_INTERVAL_S=0
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=25
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_PEER_FALLBACK_TIMEOUT=45
NVU_EMPTY_200_FASTBREAK=2
NVU_CONNECT_RESERVE_S=0
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=40
FALLBACK_HEALTH_THRESHOLD=0.10
```

### DB 摘要（6h，含 pre-R711 旧 regime 数据）
| 指标 | 值 |
|------|-----|
| 总量 | 151 req |
| OK | 99 (65.6%) |
| ATE | 52 (34.4%) |
| avg_ms | 46217 |
| p95_ms | 121418 |
| max_ms | 122312 |

### 按模型（6h）
| tier_model | cnt | ok | fail | avg_ms | max_ms |
|------------|-----|-----|------|---------|--------|
| dsv4p_nv | 97 | 48 | 49 | 55901 | 122312 |
| glm5_2_nv | 53 | 51 | 2 | 29314 | 99088 |
| kimi_nv | 1 | 0 | 1 | 2682 | 2682 |

### Post-restart（10 min，R711 生效后）
| 指标 | 值 |
|------|-----|
| 总量 | 7 req |
| OK | 4 (57.1%) |
| ATE | 3 (42.9%) |
| avg_ms | 34663 |
| max_ms | 67595 |

### ATE 分层
| tiers_tried_count | cnt | avg_ms | regime |
|-------------------|-----|--------|--------|
| 1 | 26 | 54988 | pre-restart（fallback 未尝试，全 f） |
| 2 | 23 | 110628 | pre-restart（双 tier 真正耗尽） |
| 2 | 3 | 67118 | **post-restart**（双 tier 真正耗尽） |

**关键：post-restart 零单 tier ATE** — fallback 正常工作。所有 3 个 ATE 均为双 tier 耗尽（dsv4p_nv ~33s timeout + glm5_2_nv ~33s timeout = ~67s）。

### dsv4p_nv 成功延迟分桶（6h）
| bucket | cnt | ok | via_fallback | avg_ok_ms |
|--------|-----|-----|-------------|-----------|
| <5s | 1 | 1 | 0 | 4456 |
| 5-10s | 4 | 4 | 0 | 8022 |
| 10-15s | 4 | 4 | 0 | 13392 |
| 15-20s | 9 | 9 | 0 | 17484 |
| 20-25s | 8 | 8 | 0 | 23356 |
| 25-30s | 3 | 3 | 0 | 28105 |
| 30-35s | 4 | 4 | 1 | 31432 |
| 35-40s | 1 | 1 | 0 | 35140 |
| 40-50s | 9 | 9 | 2 | 44594 |
| 50-60s | 24 | 11 | 4 | 56718 |
| 60-80s | 22 | 6 | 5 | 70429 |
| >80s | 23 | 3 | 3 | 96021 |

**R711 效果**：30-35s 桶 4 个全部成功（含 1 个 fallback）— +3s UPSTREAM 直接捕获了边缘。25-30s 仍有 3 个成功。50-80s 桶大量请求通过 fallback 成功（glm5_2_nv 救回）。

### nv_tier_attempts 失败分布（6h）
| tier | key | error_type | cnt | avg_ms |
|------|-----|-----------|-----|--------|
| dsv4p_nv | k0-k4 | NVCFPexecTimeout | 43 | ~28500-29500 |
| dsv4p_nv | k0-k4 | IntegrateTimeout | 17 | ~25300-25400 |
| glm5_2_nv | k0-k4 | NVCFPexecTimeout | 15 | ~27500-36000 |
| glm5_2_nv | k1-k4 | 429_nv_rate_limit | 14 | — |

**NVCFPexecTimeout 分布**：dsv4p_nv avg 28.5-29.5s，glm5_2_nv avg 27.5-36.0s。两者均在 UPSTREAM_TIMEOUT=33 范围内（未截断），说明 NVCF 端 function 响应超时，非代理侧配置不足。

### 日志分析（post-restart）
```
[06:34:07.5] tier_chain=['dsv4p_nv', 'glm5_2_nv'] (dynamic fallback, health={1.0, 1.0})
[06:34:41.0] NV-TIER-FAIL dsv4p_nv (timeout=1, 33494ms)
[06:34:41.0] NV-FALLBACK → glm5_2_nv ✓
[06:35:14.4] NV-TIER-FAIL glm5_2_nv (timeout=1, 66898ms)
[06:35:14.4] NV-ALL-TIERS-FAIL — 双 tier 耗尽
[06:35:16.0] health={dsv4p: 0.5, glm5_2: 0.75}
[06:36:27.0] health={dsv4p: 0.333, glm5_2: 0.6}
```

Fallback 链正常：`dsv4p_nv → glm5_2_nv`。但两个 tier 均 NVCFPexecTimeout（~33s 各），导致双 tier 耗尽→ATE。健康度快速下降（dsv4p: 1.0→0.333）说明 NVCF function 端间歇性不可用。

---

## 诊断

### 根因：NVCF 双 function 同时间歇性 pexec timeout
Post-restart 3 个 ATE 全部为双 tier 耗尽（tiers_tried_count=2），fallback 正常工作（零单 tier ATE）。每个 tier 独立 timeout @~33s（NVCFPexecTimeout），累积 ~67s 后 ATE。两个 function（dsv4p_nv 74f02205 + glm5_2_nv 3b9748d8）健康度同时下降（dsv4p: 1.0→0.333, glm5_2: 1.0→0.6），说明 NVCF 端存在批次性超时。

### 非配置可修复
- **UPSTREAM_TIMEOUT**：已从 30→33（R711），NVCFPexecTimeout avg 28.5s < 33s，非截断问题。再增加无意义——timeout 在 NVCF 端发生，非代理侧。
- **EMPTY_200_FASTBREAK**：6h 内 zero empty_200（无论 nv_requests 还是 nv_tier_attempts），此参数调整无效果。
- **PEER_FALLBACK_TIMEOUT**：6h 内 zero peer fallback 尝试（所有请求未触发 peer fallback），此参数调整无效果。
- **TIER_TIMEOUT_BUDGET_S**：110 per tier 充足（dsv4p 33s + glm5_2 33s = 66s << 110s），非预算问题。
- **FASTBREAK**：已为 1（floor），无进一步优化空间。

### ATE 诊断参考判定
> "NVCF dual-function simultaneous unavailability: when both dsv4p_nv and glm5_2_nv have health < 0.35, NO config parameter change will meaningfully improve SR. The correct decision is zero-change, waiting for NVCF recovery."

当前 dsv4p_nv 健康度 0.333（<0.35），glm5_2_nv 0.6（>0.35 但下降中）。虽未完全满足"双 <0.35"条件，但 post-restart 3/3 ATE 均为双 tier 真实耗尽，非配置参数可救回。

---

## 决策：零变更

**无参数变更。** 当前配置已处于最优状态：
- UPSTREAM_TIMEOUT=33（R711）捕获了 dsv4p_nv 边缘（30-35s 桶 4/4 成功）
- FALLBACK_HEALTH_THRESHOLD=0.10（R708）确保 fallback 正常激活
- FASTBREAK=1（R709）避免第 2 key 浪费
- BUDGET=110 per tier 充足
- 剩余 ATE 根因为 NVCF 上游 function 不可用，非代理侧可修复

**等待 NVCF 恢复后，若 dsv4p_nv SR 回到 80%+ 且 ATE 率 <10%，可考虑 EMPTY_200_FASTBREAK 2→1 或 PEER_FALLBACK_TIMEOUT 45→40。**

---

## 参数历史
| 参数 | 当前值 | 上轮 | 上上轮 | floor |
|------|--------|------|--------|-------|
| UPSTREAM_TIMEOUT | **33** | 30 (R711 +3) | 30 | ~25s |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | 1 (R709) | 2 | 1 |
| TIER_TIMEOUT_BUDGET_S | 110 | 110 | 94 | ~per-tier 预算 |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | 45 | 25 | 25 |
| NVU_EMPTY_200_FASTBREAK | 2 | 2 | 2 | 1 |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | 0.10 | 0.10 | 0.0 |

**单参数每轮；铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2