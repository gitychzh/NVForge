# R1489: HM2→HM1 — NOP (all params floor/optimal, zero ATE post-restart, code-level failures only)

## 数据收集 (HM1 via SSH)

### 容器状态
- nv_gw: Up ~26min (healthy), compose md5: ba4f2871fc9695f237e9a436ac25c279
- ms_gw: Up 19h+ (healthy), 20req/16OK = 80.0% SR
- logs_db: Up 19h+ (healthy)
- 容器重启: R1488 restart (post-R1488 ~26min, 零 ATE)

### 容器 env (R1488 compose 已生效)
- NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms ✅ (dsv4p_nv 已移除)
- NVU_PEER_FB_SKIP_MODELS="" ✅
- NVU_PEER_FALLBACK_ENABLED=1 ✅
- NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006 ✅
- NVU_PEER_FALLBACK_TIMEOUT=66 ✅
- All FASTBREAK: floor/optimal ✅ (PEXEC=1, INTEGRATE=1, EMPTY_200=2)
- NVU_TIER_BUDGET_DSV4P_NV=66 (=UPSTREAM, BUDGET floor) ✅
- NVU_TIER_BUDGET_GLM5_2_NV=96 ✅
- UPSTREAM_TIMEOUT=66 (floor) ✅
- TIER_TIMEOUT_BUDGET_S=205 (safe) ✅
- TIER_COOLDOWN_S=15 (floor) ✅
- KEY_COOLDOWN_S=25 (floor) ✅
- NVU_CONNECT_RESERVE_S=0 (floor) ✅
- MIN_OUTBOUND_INTERVAL_S=0 (floor) ✅
- NV_INTEGRATE_KEY_COOLDOWN_S=0 (floor) ✅

### 6h 总体 (nv_requests)
- 57req / 34OK / 23fail = 59.6% SR

### 6h 每小时 SR
| 小时 | total | OK | fail | SR |
|------|-------|-----|------|-----|
| 13:00 | 9 | 5 | 4 | 55.6% |
| 14:00 | 7 | 3 | 4 | 42.9% |
| 15:00 | 6 | 2 | 4 | 33.3% |
| 16:00 | 9 | 6 | 3 | 66.7% |
| 17:00 | 8 | 4 | 4 | 50.0% |
| 18:00 | 18 | 14 | 4 | 77.8% |

### 6h post-restart (R1488 restart ~18:03 UTC)
| period | total | OK | fail | SR |
|--------|-------|-----|------|-----|
| post-restart | 12 | 8 | 4 | 66.7% |

### 6h per-model SR
| Model | total | OK | fail | SR | avg_dur |
|-------|-------|-----|------|-----|---------|
| dsv4p_nv | 32 | 21 | 11 | 65.6% | 35292ms |
| glm5_2_nv | 25 | 13 | 12 | 52.0% | 12832ms |

### 6h 错误类型
| error_type | cnt | model | avg_dur |
|-----------|-----|-------|---------|
| zombie_empty_completion | 18 | glm5_2_nv(12)/dsv4p_nv(6) | 12147/34390ms |
| all_tiers_exhausted | 5 | dsv4p_nv(5) | 63580ms |

### 6h ATE 详细
| model | status | cnt | avg_dur_ms |
|-------|--------|-----|-----------|
| dsv4p_nv | 200 | 3 | 16732 |
| dsv4p_nv | 502 | 5 | 63580 |

ATE 200×3: ms_gw fallback 救援 (R1488 前, MODELMAP 曾含 dsv4p_nv)
ATE 502×5: 全部 pre-restart

### 6h zombie 详细
| model | cnt | avg_ichars | avg_dur |
|-------|-----|-----------|---------|
| glm5_2_nv | 12 | 219,828 | 12,147ms |
| dsv4p_nv | 6 | 220,132 | 34,390ms |

### 6h fallback
- fallback_occurred=f: 57/57 (100% 无 fallback 记录)

### 6h upstream_type
| upstream_type | cnt | OK | fail | avg_dur |
|--------------|-----|-----|------|---------|
| nv_integrate | 25 | 13 | 12 | 12832ms |
| nvcf_pexec | 24 | 18 | 6 | 31718ms |
| (null, ATE) | 8 | 3 | 5 | 46012ms |

### ms_gw 6h
- 20req / 16OK = 80.0% SR

### tier_attempts 6h
- 2 rows: glm5_2_nv 429_integrate_rate_limit (零影响)

### nv_gw 日志 (post-R1488 restart, ~26min)
- **零 ATE, 零 NV-TIER-FAIL, 零 NV-EMPTY-200, 零 NV-GLOBAL-COOLDOWN**
- 全成功: NV-INTEGRATE-SUCCESS (k1/k2, 2-3s) + NV-SUCCESS (k3/k4, 10-13s)
- 1× NV-ZOMBIE-EMPTY (glm5_2_nv, 12 chars output, → NV-ZOMBIE-ERROR-CHUNK → openclaw fallback)
- 2× NV-THINKING-TIMEOUT (dsv4p_nv thinking requests, extended timeout 66s)

### HM2 nv_gw health
- nv_gw: `{"status":"ok","nvcf_pexec_models":["kimi_nv","dsv4p_nv","glm5_2_nv"]}` ✅ (peer-fb ready)

## 分析

### 核心结论: NOP — 所有参数已达 floor/optimal, 零可配置优化空间

R1488 移除 dsv4p_nv→dsv4p_ms 映射后, post-restart 26min 零 ATE, 全成功请求 first-attempt:
- dsv4p_nv pexec: k3(11s), k4(13s), 后续 k3(38s), k4(22s), k3(11s), k4(13s) — 全部 first-attempt
- glm5_2_nv integrate: k1(2.5s), k2(2.7s), k1(5.6s), k2(14.3s) — 全部 first-attempt

**6h 失败全部 code-level, 不可配置修复**:
- 18 zombie (NVCF content-filter: input ~220K → output 12 chars) — R1107 code-level feature
- 5 ATE 全部 pre-R1488 (single-key empty_200 → all-key cooldown → tier failure)

**所有参数 floor/optimal**:
- UPSTREAM_TIMEOUT=66 (floor, NVCFPexecTimeout binding)
- BUDGET=205 (safe: 66s tier + 66s peer-fb = 132s < 205s)
- TIER_COOLDOWN=15 (floor, R1103 revert)
- KEY_COOLDOWN=25 (floor)
- PEER_FB_SKIP_MODELS="" → peer-fb 全开
- NVU_MS_GW_FALLBACK_MODELMAP 无 dsv4p_nv → peer-fb 救援 (66s < 176s ms_gw TimeoutError)
- All FASTBREAK floor/optimal, CONNECT_RESERVE=0, MIN_OUTBOUND=0, NV_INTEGRATE_KEY_COOLDOWN=0

### EMPTY_200_FASTBREAK=2 仍为 no-op (R1039/R1489 确认)

R1489 FASTBREAK=2 budget exhaustion trap: NVU_TIER_BUDGET_DSV4P_NV=66=UPSTREAM, k1 empty_200 burns ~62s → budget 4s < MIN_ATTEMPT_TIMEOUT(5s) → 2nd key unreachable. FASTBREAK=2 在 BUDGET=UPSTREAM 下是 dead code. 但 peer-fb 已提供独立救援路径, 无需提升 BUDGET 激活 FASTBREAK=2.

### 无变更

**铁律: 只改HM1不改HM2** ✅

## 评判

**更少报错**: post-restart 零 ATE, 零 tier cycling, 零 ms_gw relay 超时。所有失败 code-level (zombie), 不可配置修复。

**更快请求**: 成功路径全 first-attempt, 延迟健康 (dsv4p 10-38s, glm5_2 2.5-14s)。peer-fb 66s 超时 < ms_gw 120s 超时。

**超低延迟稳定优先**: 所有参数已达 floor/optimal, 零调整空间。铁律: 只改HM1不改HM2 ✅
## ⏳ 轮到HM1优化HM2
