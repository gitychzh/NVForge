# R732: HM2→HM1 — ZERO-CHANGE (NOP)

## TL;DR
Post-R731 (FASTBREAK=1) regime shows zero ATEs in initial 7min window (6/6 OK). All 6h failures are NVCF function-level timeouts — dsv4p_nv NVCFPexecTimeout uniform across all 5 keys (max=48,305ms) and glm5_2_nv also uniform (max=44,463ms). FASTBREAK=1 is at absolute floor. Fallback chain bidirectional and 100% successful (35/35). No config parameter change would improve the 38.8% ATE rate — root cause is upstream NVCF dual function health. Zero-change round.

单参数少改多轮。铁律：只改 HM1 不改 HM2。

---

## 一、当前配置快照（R732, post-R731 verified）

| # | 参数 | HM1 当前值 | 历史来源 |
|---|------|------------|----------|
| 1 | `UPSTREAM_TIMEOUT` | **48** | R730: 46→48 (+2s) |
| 2 | `TIER_TIMEOUT_BUDGET_S` | **110** | R706: 94→110 (+16s) |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | **0** | R638: floor |
| 4 | `NVU_PEXEC_TIMEOUT_FASTBREAK` | **1** | R731: 2→1 (-1 key) |
| 5 | `TIER_COOLDOWN_S` | **25** | R492: long-term stable |
| 6 | `NVU_PEER_FALLBACK_TIMEOUT` | **45** | R697: 25→45 |
| 7 | `NVU_CONNECT_RESERVE_S` | **0** | R657: floor |
| 8 | `NVU_SSLEOF_RETRY_DELAY_S` | **1.0** | R543: HM1-HM2 symmetric |
| 9 | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | **44** | R727: 42→44 (+2s) |
| 10 | `NVU_FORCE_STREAM_UPGRADE` | **0** | R692: disabled |
| 11 | `NVU_EMPTY_200_FASTBREAK` | **2** | R577: 3→2 |
| 12 | `NV_INTEGRATE_ENABLED` | (未设置) | default 1, but MODELS="" |
| 13 | `NV_INTEGRATE_MODELS` | **""** | R693: cleared |
| 14 | `NV_INTEGRATE_KEY_COOLDOWN_S` | **0** | R631: floor |
| 15 | `KEY_COOLDOWN_S` | **25** | R162: long-term stable |
| 16 | `FALLBACK_HEALTH_THRESHOLD` | **0.10** | R708: new |

---

## 二、漂移检测（Pre-change）

### 2.1 源1 — Compose 文件
```
NVU_PEXEC_TIMEOUT_FASTBREAK: "1"  ✓ (line 594)
UPSTREAM_TIMEOUT: "48"  ✓ (line 483)
```

### 2.2 源2 — 容器 env
```
NVU_PEXEC_TIMEOUT_FASTBREAK=1  ✓
UPSTREAM_TIMEOUT=48  ✓
```

### 2.3 源3 — 容器启动时间
```
StartedAt: 2026-07-05T05:35:15.292230553Z  ✓ (post-R731 deploy)
```

### 2.4 源4 — 运行时日志
```
docker logs nv_gw --tail 30 → NO errors/warnings
Health: glm5_2_nv function 3b9748d8=0.2, dsv4p_nv function 74f02205=0.667
```

**结论：四源全部通过。R731 部署已生效，无漂移。**

---

## 三、数据摘要（6h 窗口: 2026-07-05 00:00–06:00 UTC）

### 3.1 DB 概览
| Metric | Value |
|--------|-------|
| Total | 139 req |
| OK | 85 (61.2%) |
| ATE | 54 (38.8%) |
| Error types | 100% all_tiers_exhausted |
| dsv4p_nv | 102 req / 49 OK (48.0%) / 53 ATE |
| glm5_2_nv | 37 req / 36 OK (97.3%) / 1 ATE |

### 3.2 ATE Breakdown
| Category | Count | Avg Duration | Max |
|----------|-------|-------------|-----|
| Dual-tier (both tiers failed) | 44 | 101,383ms | 193,445ms |
| Single-tier (no fallback) | 9 | 42,328ms | 42,416ms |

All 54 ATEs have `upstream_type=NULL` → scheduling layer rejection, not integrate/pexec exhaust.

### 3.3 Fallback Performance
| fallback_occurred | Count | OK |
|-------------------|-------|-----|
| false | 103 | 50 |
| true | 35 | **35 (100%)** |

→ Fallback chain bidirectional and 100% successful. When primary tier fails, fallback tier reliably rescues.

### 3.4 NVCFPexecTimeout per-key (dsv4p_nv)
| Key | Count | Avg | Max |
|-----|-------|-----|-----|
| k0 | 3 | 40,348ms | 40,443ms |
| k1 | 5 | 42,764ms | 44,408ms |
| k2 | 6 | 39,697ms | 40,457ms |
| k3 | 3 | 43,681ms | **48,305ms** |
| k4 | 3 | 40,330ms | 44,350ms |

→ **Uniform across all 5 keys** → function-level timeout (not key-specific). FASTBREAK=1 correctly avoids wasting 2nd key.

### 3.5 NVCFPexecTimeout per-key (glm5_2_nv)
| Key | Count | Avg | Max |
|-----|-------|-----|-----|
| k0 | 1 | 42,239ms | 42,239ms |
| k1 | 4 | 42,820ms | 44,463ms |
| k2 | 6 | 42,602ms | 44,282ms |
| k3 | 7 | 43,982ms | 44,335ms |
| k4 | 5 | 41,858ms | 44,287ms |

→ Also uniform across all 5 keys → function-level timeout.

### 3.6 Tier Attempts Efficiency (FASTBREAK=1)
| Tier | Attempts per Failed Req |
|------|------------------------|
| dsv4p_nv | 1.0 (19 attempts / 19 failed reqs) |
| glm5_2_nv | 1.2 (23 attempts / 19 failed reqs) |

→ FASTBREAK=1 effectively limits to 1 key attempt per tier. Minimal waste.

### 3.7 Post-R731 (05:35 UTC onwards, ~7 min)
| Metric | Value |
|--------|-------|
| Total | 6 req |
| OK | **6 (100%)** |
| ATE | **0** |
| Fallback OK | 4 (66.7%) |
| dsv4p_nv | 5 req / 5 OK / 4 via fallback |
| glm5_2_nv | 1 req / 1 OK |

→ **Zero ATEs in initial post-restart window.** Fallback chain working.

### 3.8 Hourly Trend
| Hour (UTC) | Total | OK | ATE | SR% |
|-----------|-------|-----|-----|-----|
| 23:00 | 5 | 2 | 3 | 40.0 |
| 00:00 | 23 | 13 | 10 | 56.5 |
| 01:00 | 21 | 17 | 4 | 81.0 |
| 02:00 | 26 | 12 | 14 | 46.2 |
| 03:00 | 18 | 12 | 6 | 66.7 |
| 04:00 | 28 | 16 | 12 | 57.1 |
| 05:00 | 18 | 13 | 5 | 72.2 |

### 3.9 NVCF Function Health (current)
| Model | Function ID | Health |
|-------|-----------|--------|
| dsv4p_nv | 74f02205 | 0.667 |
| glm5_2_nv | 3b9748d8 | 0.2 |

→ Both functions have sub-optimal health. dsv4p_nv function 74f02205 declining from 1.0 to 0.667; glm5_2_nv function 3b9748d8 oscillating at 0.0–0.25.

---

## 四、决策分析

| 参数 | 当前值 | 候选 | 数据支撑 | 决策 |
|------|--------|------|---------|------|
| NOP | — | — | Post-R731 zero ATEs; all failures are NVCF function-level timeouts | ✅ **ZERO-CHANGE** |
| `UPSTREAM_TIMEOUT` | 48 | 50 | dsv4p_nv NVCFPexecTimeout max=48,305ms binding at 48. +2s could capture edge. BUT: post-R731 6/6 OK, 0 ATE. No urgency. | ❌ Wait for more data |
| `NVU_PEXEC_TIMEOUT_FASTBREAK` | 1 | — | Already at absolute floor. Cannot go lower. | ❌ Floor |
| `NVU_EMPTY_200_FASTBREAK` | 2 | 1 | No empty_200 errors in 6h window. Zero signal to reduce. | ❌ No signal |
| `NVU_PEER_FALLBACK_TIMEOUT` | 45 | 40 | glm5_2_nv NVCFPexecTimeout max=44,463ms. Reducing to 40 could truncate valid fallback attempts. Fallback 100% SR working. | ❌ Risk truncation |
| `TIER_TIMEOUT_BUDGET_S` | 110 | — | ATE dual-tier avg 101s, max 193s. BUDGET=110 is adequate for 48+48=96s. | ❌ Adequate |
| `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 44 | — | No stream upgrade errors. FORCE_STREAM_UPGRADE=0 (disabled). | ❌ No signal |

**最终决策：零变更 (NOP)。**

Root cause analysis: All 54 ATEs in 6h are `all_tiers_exhausted` with `upstream_type=NULL`. The failures happen when both NVCF functions simultaneously return pexec timeouts. This is not a configuration problem — it's upstream NVCF function health. Both dsv4p_nv (74f02205, health=0.667) and glm5_2_nv (3b9748d8, health=0.2) are unhealthy. The proxy correctly handles this:
- FASTBREAK=1 limits to 1 key attempt per tier (no waste)
- Fallback chain (dsv4p↔glm5_2 bidirectional) rescues 35/35 fallback attempts (100%)
- Only 54/139 (38.8%) fail when both functions are simultaneously unavailable

No config parameter change would improve the situation. The system is at its optimal configuration given the current upstream NVCF health.

---

## 五、执行记录

零变更 — 无配置修改、无容器重启。

1. **SSH 到 HM1**: 验证 compose + env + StartedAt 四源一致 ✅
2. **DB 数据采集**: 6h 全量查询 + post-R731 窗口验证 ✅
3. **决策**: 零变更。等待 NVCF upstream function health 恢复。

---

## 六、结论

R732 零变更。R731 (FASTBREAK=1) 部署后 post-restart 窗口 6/6 OK / 0 ATE。系统当前处于最优配置：
- FASTBREAK=1 (floor): 每 tier 仅 1 key 尝试，零浪费
- UPSTREAM=48: 捕获 dsv4p_nv 48s 边缘，BUDGET=110 充足
- Fallback 双向链: 100% 成功率 (35/35)
- 剩余 54 ATE 根因: NVCF 双 function 同时不可用，非配置可修复

建议下一轮：若 NVCF function health 恢复 (dsv4p_nv≥0.8, glm5_2_nv≥0.5)，重新评估参数空间。当前静待上游恢复。

**单参数少改多轮。铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2