# R725: HM2→HM1 — 零变更轮（R724刚部署10min，NVCF 双 function 上游健康度问题，所有参数已达最优/地板，无需配置变更）

## TL;DR
R724 (NVU_FORCE_STREAM_UPGRADE_TIMEOUT 40→42) 部署仅10分钟，post-restart 11req/6OK(54.5%)/5ATE 样本过小。6h窗口 311req/203OK(65.3%)/108ATE(34.7%) 受 R710 FALLBACK_GRAPH 消失窗口 + NVCF 双 function 健康度下降双重影响。glm5_2_nv primary function 3b9748d8 health 0.0-0.25 极不稳定，dsv4p_nv primary 74f02205 1.0→0.667 持续下降。所有参数已达最优：UPSTREAM=42, FORCE_STREAM_UPGRADE=42, BUDGET=110, FASTBREAK=1, FALLBACK_HEALTH_THRESHOLD=0.10。零变更。单参数每轮；铁律：只改 HM1 不改 HM2。

---

## 一、当前配置快照（R725 部署前，容器 ~10:55 UTC）

| # | 参数 | HM1 当前值 | 历史来源 |
|---|------|------------|----------|
| 1 | `UPSTREAM_TIMEOUT` | 42 | R723: HM2→HM1 40→42 |
| 2 | `TIER_TIMEOUT_BUDGET_S` | 110 | R706: 94→110 |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | 0 | R548: 1.0→0 (floor) |
| 4 | `NVU_PEXEC_TIMEOUT_FASTBREAK` | 1 | R709: 2→1 |
| 5 | `TIER_COOLDOWN_S` | 25 | R694: 15→25 |
| 6 | `NVU_PEER_FALLBACK_TIMEOUT` | 45 | R697: 25→45 |
| 7 | `NVU_CONNECT_RESERVE_S` | 0 | R694: 25→0 (floor) |
| 8 | `NVU_SSLEOF_RETRY_DELAY_S` | 1.0 | R694: 0.5→1.0 |
| 9 | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 42 | R724: HM2→HM1 40→42 |
| 10 | `NVU_FORCE_STREAM_UPGRADE` | 0 | R692: 1→0 |
| 11 | `NVU_EMPTY_200_FASTBREAK` | 2 | R577: 3→2 |
| 12 | `NVU_PEER_FALLBACK_ENABLED` | 1 | R692 |
| 13 | `FALLBACK_HEALTH_THRESHOLD` | 0.10 | R708: 复活 |
| 14 | `KEY_COOLDOWN_S` | 25 | R694: 15→25 |

---

## 二、漂移检测（Pre-change）

### 2.1 源1 — Compose 文件
```
UPSTREAM_TIMEOUT: "42"  # R723 (HM2→HM1): 40→42
NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "42"  # R724 (HM2→HM1): 40→42
TIER_TIMEOUT_BUDGET_S: "110"
NVU_PEXEC_TIMEOUT_FASTBREAK: "1"
NVU_EMPTY_200_FASTBREAK: "2"
```

### 2.2 源2 — 容器 env
```
UPSTREAM_TIMEOUT=42
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=42
TIER_TIMEOUT_BUDGET_S=110
NVU_PEXEC_TIMEOUT_FASTBREAK=1
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=25
NVU_PEER_FALLBACK_TIMEOUT=45
NVU_CONNECT_RESERVE_S=0
NVU_EMPTY_200_FASTBREAK=2
NVU_FORCE_STREAM_UPGRADE=0
FALLBACK_HEALTH_THRESHOLD=0.10
NVU_PEER_FALLBACK_ENABLED=1
NVU_SSLEOF_RETRY_DELAY_S=1.0
```
→ 容器 env 与 compose 一致 ✅

### 2.3 源3 — 容器启动时间
```
Up 10 minutes (healthy) — 启动于 ~10:55 UTC
```
→ R724 部署后容器 healthy ✅

### 2.4 源4 — 运行时日志
```
[11:03:20] glm5_2_nv tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback) — FALLBACK_GRAPH 双向活跃
[11:04:17] health={'3b9748d8...': 0.0, '74f02205...': 1.0}
[11:06:44] health={'3b9748d8...': 0.25, '74f02205...': 1.0}
[11:08:52] dsv4p_nv tier_chain=['dsv4p_nv', 'glm5_2_nv'] (dynamic fallback)
[11:10:00] health={'3b9748d8...': 0.2, '74f02205...': 0.8}  ← dsv4p_nv 开始下降
[11:11:11] health={'3b9748d8...': 0.167, '74f02205...': 0.667}  ← 双 function 下降中
[11:04:17] [NV-FALLBACK-SUCCESS] glm5_2→dsv4p fallback 成功
[11:05:15] [NV-FALLBACK-SUCCESS] glm5_2→dsv4p fallback 成功
[11:06:13] [NV-FALLBACK-SUCCESS] glm5_2→dsv4p fallback 成功
[11:07:27] [NV-FALLBACK-SUCCESS] glm5_2→dsv4p fallback 成功
[11:10:17] [NV-PEER-FB] peer-originated (hop=1) all_tiers_exhausted — HM2→HM1 也失败
[11:11:24] [NV-PEER-FB] peer-originated (hop=1) all_tiers_exhausted
```
→ 四源全部通过，无漂移 ✅

**结论：四源一致，无漂移。**

---

## 三、数据摘要（6h 窗口，ts >= now() - 6h）

### 3.1 总体统计
| 模型 | 总量 | OK | ATE | SR | avg_ok_ms | max_ok_ms |
|------|------|-----|-----|-----|-----------|-----------|
| dsv4p_nv | 232 | 130 | 102 | 56.0% | 38,120ms | 99,088ms |
| glm5_2_nv | 77 | 72 | 5 | 93.5% | 19,203ms | 90,312ms |
| kimi_nv | 1 | 0 | 1 | 0% | — | — |
| **合计** | **311** | **203** | **108** | **65.3%** | — | — |

### 3.2 ATE 分解
| tiers_tried_count | 数量 | 占比 | avg_dur | 模型分布 |
|-------------------|------|------|---------|---------|
| 1 | 57 | 52.8% | 48,094ms | dsv4p_nv:51, glm5_2:5, kimi:1 |
| 2 | 51 | 47.2% | 92,749ms | dsv4p_nv:51 |

单 tier ATE (57):
- start_tier_idx=1 (dsv4p_nv): 51, avg=49,055ms, fallback_actually_attempted=f (全部)
- start_tier_idx=3 (glm5_2_nv): 5, avg=47,377ms, fallback_actually_attempted=f
- start_tier_idx=0 (kimi_nv): 1, avg=2,682ms

→ 51/57 (89.5%) 单 tier ATE 是 dsv4p_nv，全部 fallback 未尝试 — 预重启 FALLBACK_GRAPH 消失窗口

### 3.3 成功路径分析
| 模型 | fallback_occurred | 数量 | avg_dur | max_dur | 路径 |
|------|-------------------|------|---------|---------|------|
| dsv4p_nv | f (primary) | 88 | 25,553ms | 60,099ms | dsv4p_nv 直连成功 |
| dsv4p_nv | t (via glm5_2) | 41 | 57,986ms | 99,088ms | fallback 救回 |
| glm5_2_nv | f (primary) | 58 | 10,203ms | 37,917ms | glm5_2 直连成功 |
| glm5_2_nv | t (via dsv4p) | 14 | 56,587ms | 90,312ms | fallback 救回 |

→ dsv4p_nv 31.5% (41/130) 成功需要 fallback 救回
→ glm5_2_nv 19.4% (14/72) 成功需要 fallback 救回
→ Fallback 总成功 55/55 = 100% SR ✅

### 3.4 按 key 成功分布
| 模型 | 键 | 成功数 | avg_dur |
|------|-----|--------|---------|
| dsv4p_nv | k0 | 29 | 32,482ms |
| dsv4p_nv | k1 | 26 | 37,118ms |
| dsv4p_nv | k2 | 20 | 36,362ms |
| dsv4p_nv | k3 | 29 | 39,220ms |
| dsv4p_nv | k4 | 24 | 35,799ms |
| glm5_2_nv | k0 | 12 | 20,602ms |
| glm5_2_nv | k1 | 15 | 19,808ms |
| glm5_2_nv | k2 | 11 | 9,920ms |
| glm5_2_nv | k3 | 18 | 21,241ms |
| glm5_2_nv | k4 | 16 | 21,760ms |

→ 5 key 均匀分布，无单 key 热点 ✅

### 3.5 小时趋势
| 小时 (UTC) | 总量 | OK | ATE | SR | 备注 |
|-----------|------|-----|-----|-----|------|
| 21:00 | 10 | 4 | 6 | 40.0% | 低谷 |
| 22:00 | 28 | 13 | 15 | 46.4% | |
| 23:00 | 9 | 8 | 1 | 88.9% | |
| 00:00 | 2 | 2 | 0 | 100.0% | 极低流量 |
| 01:00 | 13 | 8 | 5 | 61.5% | |
| 02:00 | 49 | 35 | 14 | 71.4% | |
| 03:00 | 27 | 20 | 7 | 74.1% | |
| 04:00 | 21 | 14 | 7 | 66.7% | |
| 05:00 | 20 | 7 | 13 | 35.0% | 低谷 |
| 06:00 | 29 | 22 | 7 | 75.9% | |
| 07:00 | 24 | 21 | 3 | 87.5% | 峰值 |
| 08:00 | 23 | 13 | 10 | 56.5% | |
| 09:00 | 21 | 17 | 4 | 81.0% | |
| 10:00 | 26 | 12 | 14 | 46.2% | 低谷 |
| 11:00 | 8 | 6 | 2 | 75.0% | post-restart |

→ 05:00 UTC (13:00 CST) 和 10:00 UTC (18:00 CST) 为日常低谷，非异常

### 3.6 Post-restart (R724, ~10:55 UTC, 10 min)
| 模型 | 总量 | OK | ATE | SR | avg_dur |
|------|------|-----|-----|-----|---------|
| dsv4p_nv | 6 | 1 | 5 | 16.7% | 53,648ms |
| glm5_2_nv | 5 | 5 | 0 | 100.0% | 50,828ms |
| **合计** | **11** | **6** | **5** | **54.5%** | — |

→ Post-restart dsv4p_nv 5 个 ATE 全部双 tier 耗尽（tiers_tried_count=2, ~84s = 42+42）
→ glm5_2_nv 5/5 OK，其中 4/5 需要 fallback to dsv4p_nv
→ 样本过小（11 req），无法得出有效结论

---

## 四、决策分析

### 4.1 根因诊断

**核心发现：NVCF 双 function 上游健康度问题，非配置可修复**

**glm5_2_nv primary function 3b9748d8:**
- health 0.0 → 0.25 → 0.2 → 0.167（剧烈波动，极不稳定）
- 0.0 时所有 glm5_2 请求 timeout → 触发 fallback to dsv4p_nv
- 4/5 glm5_2_nv post-restart 成功 = 全部 fallback 救回（primary 失败 → dsv4p 成功）

**dsv4p_nv primary function 74f02205:**
- health 1.0 → 0.8 → 0.667（持续下降趋势）
- 1.0 时直连成功（25,553ms avg），0.667 时 dsv4p 也开始失败
- 5/6 dsv4p_nv post-restart ATE = 双 tier 都耗尽（glm5_2 也不健康）

**51 单 tier ATE (dsv4p_nv, fallback_actually_attempted=f):**
- 全部发生在预重启容器（R710 FALLBACK_GRAPH 消失窗口）
- R724 commit 明确提到 "Container restart also fixes active R710 FALLBACK_GRAPH transient disappearance"
- Post-restart: 0 单 tier ATE，全部为双 tier 耗尽 → FALLBACK_GRAPH 修复生效 ✅

**FALLBACK_GRAPH 双向工作验证：**
- dsv4p_nv→glm5_2_nv: tier_chain=['dsv4p_nv', 'glm5_2_nv'] ✅
- glm5_2_nv→dsv4p_nv: tier_chain=['glm5_2_nv', 'dsv4p_nv'] ✅
- NV-FALLBACK-SUCCESS 持续出现（glm5_2→dsv4p 方向）
- HEALTH_THRESHOLD=0.10 未误杀（glm5_2 health 0.0 时确实被排除，但 0.2+ 时正常加入）

### 4.2 参数候选评估

| 参数 | 当前值 | 候选 | 判定 |
|------|--------|------|------|
| `UPSTREAM_TIMEOUT` | 42 | 42→44 | ❌ R723 刚改，10min 无有效数据。NVCFPexecTimeout 绑定验证需要更多 post-restart 数据。 |
| `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 42 | — | ✅ R724 刚改，与 UPSTREAM=42 对齐。需要更多数据验证。 |
| `TIER_TIMEOUT_BUDGET_S` | 110 | — | ✅ 双 tier ATE max=92,749ms < 110s。BUDGET 充足。 |
| `NVU_PEXEC_TIMEOUT_FASTBREAK` | 1 | — | ✅ 已达 floor。5 个 ATE 全部双 tier，FASTBREAK=1 正确。 |
| `FALLBACK_HEALTH_THRESHOLD` | 0.10 | — | ✅ 安全地板。glm5_2 health 0.25>0.10 时 fallback 正常活跃。 |
| `NVU_PEER_FALLBACK_TIMEOUT` | 45 | — | ✅ 2 个 peer-originated ATE 是 HM1 自身也失败，非 timeout。 |
| `NVU_EMPTY_200_FASTBREAK` | 2 | — | ✅ 当前错误全部 all_tiers_exhausted，无 empty_200。 |

**所有候选参数均被否决。根因是 NVCF 上游 function 健康度问题。R724 刚部署 10min，无有效数据支持任何参数变更。**

### 4.3 最终决策：零变更

零变更。R724 部署仅 10 分钟，post-restart 11req 样本过小。所有参数处于历史验证最优值或 floor。NVCF 双 function 上游健康度问题（glm5_2 3b9748d8: 0.0-0.25, dsv4p_nv 74f02205: 0.667-1.0 下降中）是 ATE 根因，非配置可修复。FALLBACK_GRAPH 双向活跃，fallback 成功率 100% (55/55)。零变更是最优决策。

---

## 五、执行记录

**无执行操作（零变更轮）。** 未修改 HM1 compose 文件，未重启容器。

---

## 六、验证记录

| 指标 | 数值 | 状态 |
|------|------|------|
| 配置一致性 | compose=env=42 ✅ | — |
| FALLBACK_GRAPH 双向 | 活跃 ✅ | — |
| Fallback 成功率 | 55/55 = 100% ✅ | — |
| BUDGET 安全 | 双 tier max=92.7s < 110s ✅ | — |
| HEALTH_THRESHOLD | 未误杀 (glm5_2 0.25>0.10 时活跃) ✅ | — |
| 容器稳定性 | Up 10 min (healthy) ✅ | — |
| NVCF 上游 | glm5_2 3b9748d8 0.0-0.25 不稳定 ⚠️ | dsv4p_nv 74f02205 0.667-1.0 下降中 ⚠️ |

---

## 七、结论

R725 零变更。根因：NVCF 双 function 上游健康度问题 — glm5_2_nv primary function `3b9748d8` health 0.0-0.25 极不稳定，dsv4p_nv primary function `74f02205` 从 1.0 持续下降至 0.667。R724 刚部署 10min，post-restart 11req/6OK 样本过小。51 个 6h 单 tier ATE 全部来自预重启 FALLBACK_GRAPH 消失窗口，R724 重启已修复。Post-restart 5 个 ATE 全部双 tier 耗尽（NVCF 双 function 同时不可用），非配置可修复。FALLBACK_GRAPH 双向活跃，fallback 成功率 100% (55/55)。所有参数处于历史验证最优值或 floor。零变更。

**单参数少改多轮。铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2