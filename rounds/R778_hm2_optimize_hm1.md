# R778: HM2→HM1 — NOP — 100% SR完美健康regime，零参数变更

**时间**: 2026-07-06 01:07 UTC
**作者**: opc2_uname (HM2)
**类型**: HM2优化HM1（铁律：只改HM1不改HM2）

---

## TL;DR
6h窗口68req/68OK(100.0% SR), 零ATE零fail。所有请求nvcf_pexec路径。NVCFPexecTimeout max=53,194ms << UPSTREAM=66(buffer=12.8s)。NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66与UPSTREAM对齐(R755)。EMPTY_200_FASTBREAK=1 at floor, PEXEC_TIMEOUT_FASTBREAK=1 at floor。所有参数处于最优值，零变更。
单参数少改多轮。铁律：只改HM1不改HM2。

---

## 一、当前配置快照（R778 部署前，无变更）

| # | 参数 | HM1 当前值 | 历史来源 |
|---|------|------------|----------|
| 1 | `UPSTREAM_TIMEOUT` | 66 | R754: 64→66 |
| 2 | `TIER_TIMEOUT_BUDGET_S` | 114 | R737: 110→114 |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | 0 | R638: floor |
| 4 | `NVU_PEXEC_TIMEOUT_FASTBREAK` | 1 | R768: 2→1 (floor) |
| 5 | `TIER_COOLDOWN_S` | 25 | R492: 稳定值 |
| 6 | `NVU_PEER_FALLBACK_TIMEOUT` | 45 | R697: 25→45 |
| 7 | `NVU_CONNECT_RESERVE_S` | 0 | R657: floor |
| 8 | `NVU_SSLEOF_RETRY_DELAY_S` | 1.0 | R543: HM1-HM2对称 |
| 9 | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 66 | R755: 62→66 (对齐UPSTREAM=66) |
| 10 | `NVU_FORCE_STREAM_UPGRADE` | 0 | R692: 禁用 |
| 11 | `NVU_EMPTY_200_FASTBREAK` | 1 | R774: 3→1 (floor) |
| 12 | `NV_INTEGRATE_MODELS` | "" (空) | R693: 清空 |
| 13 | `NV_INTEGRATE_KEY_COOLDOWN_S` | 0 | R631: floor |
| 14 | `KEY_COOLDOWN_S` | 25 | R162: 稳定值 |
| 15 | `FALLBACK_HEALTH_THRESHOLD` | 0.10 | R708: 安全地板 |

---

## 二、漂移检测

### 2.1 Source 1 — Compose
```
UPSTREAM_TIMEOUT: "66"              # R754 (HM2→HM1)
TIER_TIMEOUT_BUDGET_S: "114"         # R737 (HM2→HM1)
NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "66"  # R755 (HM2→HM1) aligned
NVU_EMPTY_200_FASTBREAK: "1"        # R774 (HM2→HM1)
NVU_PEXEC_TIMEOUT_FASTBREAK: "1"    # R768 (HM2→HM1)
NVU_PEER_FALLBACK_TIMEOUT: "45"     # R697
```

### 2.2 Source 2 — Container env
```
UPSTREAM_TIMEOUT=66 ✓
TIER_TIMEOUT_BUDGET_S=114 ✓
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66 ✓
NVU_EMPTY_200_FASTBREAK=1 ✓
NVU_PEXEC_TIMEOUT_FASTBREAK=1 ✓
NVU_PEER_FALLBACK_TIMEOUT=45 ✓
```

### 2.3 Source 3 — 容器启动时间
```
nv_gw Up About an hour (healthy)
```

### 2.4 Source 4 — 运行时日志
```
docker logs nv_gw --tail 100 | grep -iE 'error|warn|exception'
→ NO_ERRORS/WARNS_FOUND (仅NV-THINKING-TIMEOUT extended=66s正常行为)
→ 1 empty_200 cluster → NV-EMPTY-FASTBREAK tier=dsv4p_nv → NV-FALLBACK to glm5_2_nv → NV-FALLBACK-SUCCESS ✓
```

**结论：四源全部一致，零漂移。**

---

## 三、数据摘要（6h窗口，截至2026-07-06 01:07 UTC）

### 3.1 6h总体
| Metric | Value |
|--------|-------|
| Total | 68 |
| OK (200) | 68 |
| ATE (502) | 0 |
| SR | 100.0% |
| Avg duration | 25,675ms |
| P50 duration | 7,776ms |
| P95 duration | 106,661ms |
| Max duration | 118,476ms |

### 3.2 按模型(6h)
| request_model | cnt | ok | avg_ms | p95_ms | max_ms |
|---------------|-----|-----|--------|--------|--------|
| dsv4p_nv | 39 | 39 | 38,648 | 111,894 | 118,476 |
| glm5_2_nv | 29 | 29 | 8,228 | 29,863 | 55,920 |

### 3.3 按tiers_tried(6h)
| tiers_tried | cnt | avg_ms | max_ms |
|-------------|-----|--------|--------|
| 1 (单tier) | 62 | 18,182 | 108,348 |
| 2 (fallback) | 6 | 103,105 | 118,476 |

dsv4p_nv单tier: 33 OK, avg=26,929ms, max=108,348ms (BUDGET=114 buffer 5.7s)
dsv4p_nv双tier(fallback): 6 OK, avg=103,105ms, max=118,476ms (所有6次100% SR)
glm5_2_nv单tier: 29 OK, avg=8,228ms, max=55,920ms

### 3.4 按路径(6h)
| upstream_type | cnt | ok | avg_ttfb | avg_dur | max_dur |
|---------------|-----|-----|----------|---------|---------|
| nvcf_pexec | 68 | 68 | 25,647 | 25,675 | 118,476 |

Integrate路径零流量(NV_INTEGRATE_MODELS="")。

### 3.5 Fallback统计(6h)
| fallback_occurred | cnt | avg_ms | max_ms |
|-------------------|-----|--------|--------|
| false | 62 | 18,182 | 108,348 |
| true | 6 | 103,105 | 118,476 |

6次fallback全部成功(dsv4p_nv→glm5_2_nv, 100% SR)。

### 3.6 nv_tier_attempts(6h) — 失败尝试
| tier | error_type | cnt | max_ms |
|------|------------|-----|--------|
| dsv4p_nv | empty_200 | 11 | — |
| dsv4p_nv | 429_nv_rate_limit | 6 | — |
| dsv4p_nv | NVCFPexecTimeout | 2 | 53,194 |

NVCFPexecTimeout max=53,194ms << UPSTREAM=66 (buffer=12.8s) ✓ 非绑定
empty_200 leading failure type but EMPTY_200_FASTBREAK=1 triggers immediate fallback

### 3.7 key_cycle_429s(6h)
| request_model | 429=0 | 429=1 | 429=2 | 429=3 | total_429s |
|---------------|-------|-------|-------|-------|------------|
| dsv4p_nv | 26 | 9 | 2 | 2 | 19 |
| glm5_2_nv | 29 | 0 | 0 | 0 | 0 |

dsv4p_nv 33.3%有429 cycle (13/39)，glm5_2完全零429。429分布均匀非key集中。

### 3.8 每小时SR(6h)
| hour (UTC) | total | ok | sr_pct | avg_ms |
|------------|-------|-----|--------|--------|
| 19:00-20:00 | 5 | 5 | 100.0 | 36,991 |
| 20:00-21:00 | 18 | 18 | 100.0 | 15,149 |
| 21:00-22:00 | 8 | 8 | 100.0 | 28,397 |
| 22:00-23:00 | 5 | 5 | 100.0 | 40,565 |
| 23:00-00:00 | 11 | 11 | 100.0 | 32,022 |
| 00:00-01:00 | 17 | 17 | 100.0 | 24,797 |
| 01:00-01:07 | 4 | 4 | 100.0 | 21,115 |

所有小时100% SR。零变异。

---

## 四、决策分析

| 参数 | 当前值 | 候选新值 | 数据支撑 | 决策 |
|------|--------|---------|---------|------|
| NOP (all) | — | — | 100% SR 6h, 零ATE, 零fail, NVCFPexecTimeout buffer=12.8s >3s | ✅ NOP |
| UPSTREAM_TIMEOUT | 66 | — | max NVCFPexecTimeout=53,194ms << 66 (12.8s buffer). 非绑定。降低无收益 | ❌ |
| TIER_TIMEOUT_BUDGET_S | 114 | — | max单tier成功=108,348ms buffer仅5.7s, 降低风险误杀 | ❌ |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | — | peer fallback零触发6h, 无数据支持调整 | ❌ |
| NVU_EMPTY_200_FASTBREAK | 1 | — | 已达floor=1, 不可再降 | ❌ |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | — | 已达floor=1, 不可再降 | ❌ |

**最终决策**: NOP（零变更）。所有参数处于最优值，regime 100% SR完美健康。

**理由**:
1. 100% SR over 6h — 无任何配置相关错误需要修复
2. NVCFPexecTimeout 非 UPSTREAM 绑定 (buffer=12.8s >> 3s min) — 降低 UPSTREAM 无收益
3. BUDGET=114 单tier max=108,348ms buffer仅5.7s — 降低BUDGET可能导致边缘误杀
4. 所有可优化参数已达 floor (FASTBREAK=1, EMPTY_200_FASTBREAK=1, CONNECT_RESERVE=0, MIN_OUTBOUND=0, INTEGRATE_COOLDOWN=0)
5. FORCE_STREAM_UPGRADE_TIMEOUT=66 与 UPSTREAM=66 已对齐 (R755 drift correction)
6. 无参数漂移 — compose / env / runtime 三源一致 ✓

---

## 五、结论

R778 NOP。零参数变更，零 compose 修改，零容器重启。

6h窗口68/68 OK = **100.0% SR**，连续7小时全小时100% SR。所有请求nvcf_pexec路径。Fallback双向100% SR (6/6 dsv4p_nv→glm5_2_nv全部成功)。NVCFPexecTimeout max=53,194ms << UPSTREAM=66 非绑定。所有可优化参数已达地板值或处于安全最优值。

**等待信号**: 若NVCF function健康度变化导致ATE重现 → 考虑PEER_FALLBACK_TIMEOUT或UPSTREAM微调。当前regime下任何参数变更均为不必要的风险引入。

**单参数少改多轮。铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2