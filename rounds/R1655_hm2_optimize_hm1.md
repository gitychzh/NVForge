# R1655 (HM2→HM1): NOP — 零dsv4p流量无法评估BUDGET=90, zombie仍是NVCF server-side

## TL;DR
Zero parameter change. Post-R1652 仅 2 个 glm5_2 请求, 零 dsv4p 流量。BUDGET=90 无法评估。所有参数已在 floor。zombie_empty_completion (78.3% of failures) 是 NVCF content-filter server-side。单参数少改多轮。铁律：只改 HM1 不改 HM2。

---

## 一、当前配置快照（R1655 部署前）

| # | 参数 | HM1 当前值 | 历史来源 |
|---|------|------------|----------|
| 1 | `UPSTREAM_TIMEOUT` | 66 | R1618 |
| 2 | `TIER_TIMEOUT_BUDGET_S` | 195 | R1647 |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | 0 | floor (R638) |
| 4 | `NVU_PEXEC_TIMEOUT_FASTBREAK` | 1 | floor |
| 5 | `TIER_COOLDOWN_S` | 60 | R1643 (KEY=TIER铁律) |
| 6 | `NVU_PEER_FALLBACK_TIMEOUT` | 72 | HM2 BUDGET=70+2 ✓ |
| 7 | `NVU_CONNECT_RESERVE_S` | 0 | floor (R657) |
| 8 | `NVU_SSLEOF_RETRY_DELAY_S` | 0.5 | floor (R1626) |
| 9 | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 66 | aligned with UPSTREAM |
| 10 | `NVU_FORCE_STREAM_UPGRADE` | 0 | disabled |
| 11 | `NVU_EMPTY_200_FASTBREAK` | 2 | floor |
| 12 | `NV_INTEGRATE_ENABLED` | (config.py) | — |
| 13 | `NV_INTEGRATE_MODELS` | (empty) | — |
| 14 | `NV_INTEGRATE_KEY_COOLDOWN_S` | 0 | floor (R631) |
| 15 | `KEY_COOLDOWN_S` | 60 | R1643 (KEY=TIER铁律) |
| 16 | `NVU_TIER_BUDGET_DSV4P_NV` | 90 | R1652 |
| 17 | `NVU_TIER_BUDGET_GLM5_2_NV` | 120 | R1641 |
| 18 | `NVU_PEER_FB_SKIP_MODELS` | "" | R1646 |

---

## 二、漂移检测（Pre-change）

### 2.1 源1 — Compose 文件
```
NVU_TIER_BUDGET_DSV4P_NV: "90"     # R1652
NVU_TIER_BUDGET_GLM5_2_NV: "120"
TIER_TIMEOUT_BUDGET_S: "195"       # R1647
UPSTREAM_TIMEOUT=66
KEY_COOLDOWN_S: "60"               # R1643
TIER_COOLDOWN_S: "60"              # R1643
MIN_OUTBOUND_INTERVAL_S: "0"
NVU_CONNECT_RESERVE_S: "0"
NV_INTEGRATE_KEY_COOLDOWN_S: "0"
NVU_PEER_FALLBACK_TIMEOUT: "72"
NVU_PEER_FB_SKIP_MODELS: ""        # R1646
NVU_SSLEOF_RETRY_DELAY_S: "0.5"
NVU_FORCE_STREAM_UPGRADE: "0"
NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "66"
```

### 2.2 源2 — 容器 env
```
NVU_TIER_BUDGET_DSV4P_NV=90
NVU_TIER_BUDGET_GLM5_2_NV=120
TIER_TIMEOUT_BUDGET_S=195
UPSTREAM_TIMEOUT=66
KEY_COOLDOWN_S=60
TIER_COOLDOWN_S=60
MIN_OUTBOUND_INTERVAL_S=0
NVU_CONNECT_RESERVE_S=0
NV_INTEGRATE_KEY_COOLDOWN_S=0
NVU_PEER_FALLBACK_TIMEOUT=72
NVU_PEER_FB_SKIP_MODELS=
NVU_SSLEOF_RETRY_DELAY_S=0.5
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
```

### 2.3 源3 — 容器启动时间
```
2026-07-17 04:19 UTC (R1652 容器重启于 2026-07-16 20:49 UTC，但容器在 43 min 前又被重启过)
实际运行时间: ~43 min (Up 43 minutes)
```

### 2.4 源4 — 运行时日志
```
docker logs nv_gw --tail 100: 仅 1 条 ERROR
→ NV-ZOMBIE-EMPTY glm5_2_nv zombie_empty_completion (finish_reason=stop, content_chars=12, reasoning_chars=0)
→ 零 SSLEOF, 零 TimeoutError, 零 pexec_429, 零 ATE
```

**结论：四源全部一致，无漂移。继续标准分析。**

---

## 三、数据摘要

### 3.1 总览（24h）
```sql
177 OK / 152 fail / 329 total (53.8% SR)
```

### 3.2 按模型（24h）
```
glm5_2_nv: 159 OK / 135 fail / 294 total (54.1% SR)
dsv4p_nv:  18 OK /  17 fail /  35 total (51.4% SR)
```

### 3.3 错误分类（24h）
```
zombie_empty_completion  | 119  (78.3% of all failures, all glm5_2_nv)
all_tiers_exhausted      |  33  (21.7% of all failures, 28 dsv4p + 25 glm5_2)
```

### 3.4 Post-R1652 数据（容器重启后，~43 min）
```
总量: 仅 2 请求 (both glm5_2_nv)
  1 OK  (glm5_2_nv, 200)
  1 fail (glm5_2_nv, zombie_empty_completion)
零 dsv4p_nv 请求
零 ATE (both models)
```

### 3.5 ATE 时间线（全部 pre-R1652）
```
dsv4p ATE (28/35, 80%): 全部于 2026-07-16 18:00-18:04 UTC
  - 旧 BUDGET=76, 61.5-64.3s → abort
  - tiers_tried=1: 仅 dsv4p_nv tier, peer-fb 未触发
  - Post-R1652: ZERO dsv4p ATE (但 ZERO dsv4p 流量)

glm5_2 ATE (25/294, 8.5%): 全部于 2026-07-16 11:40-12:08 UTC
  - 旧 BUDGET=120, 7s-266s 耗尽
  - Post-R1652: ZERO glm5_2 ATE
```

### 3.6 429 分析（24h）
```
key_cycle_429s=0:  60 (18.2%)
key_cycle_429s=1: 205 (62.3%) — single-key 429, 非级联
key_cycle_429s=2:  34 (10.3%) — 2-key 级联
key_cycle_429s=3:  16 (4.9%)
key_cycle_429s=4:   8 (2.4%)
key_cycle_429s=5:   4 (1.2%)
key_cycle_429s=6:   2 (0.6%)

Multi-key 级联 (≥2): 64/329 (19.5%)
  → 43 OK / 21 fail (67.2% success despite cascade)
  → KEY_COOLDOWN=60=TIER_COOLDOWN=60 满足 KEY≥TIER 铁律
```

### 3.7 Fallback 触发
```
fallback_occurred=f: 100% (zero fallbacks triggered in 24h)
peer-fallback: 零触发
```

### 3.8 Docker Logs
```
--tail 100: 仅 1 条 ERROR/WARN
→ NV-ZOMBIE-EMPTY glm5_2_nv zombie_empty_completion (finish_reason=stop, content_chars=12)
→ 零 SSLEOF, 零 TimeoutError, 零 pexec_429, 零 ATE
```

---

## 四、决策分析

| 参数 | 旧值 | 候选新值 | 数据支撑 | 决策 |
|------|------|---------|---------|------|
| `NVU_TIER_BUDGET_DSV4P_NV` | 90 | — | Post-R1652 ZERO dsv4p traffic，无法评估 | ❌ 待观察 |
| `NVU_TIER_BUDGET_GLM5_2_NV` | 120 | — | Post-R1652 ZERO ATE | ❌ |
| `KEY_COOLDOWN_S` | 60 | — | KEY=TIER=60 铁律，67% multi-key 429 success | ❌ 不可减 |
| `TIER_COOLDOWN_S` | 60 | — | KEY=TIER 铁律，不可减 | ❌ |
| `UPSTREAM_TIMEOUT` | 66 | — | floor | ❌ |
| `MIN_OUTBOUND_INTERVAL_S` | 0 | — | floor | ❌ |
| `NVU_CONNECT_RESERVE_S` | 0 | — | floor | ❌ |
| `NV_INTEGRATE_KEY_COOLDOWN_S` | 0 | — | floor | ❌ |
| `NVU_SSLEOF_RETRY_DELAY_S` | 0.5 | — | floor，零 SSLEOF errors | ❌ |
| `NVU_PEER_FALLBACK_TIMEOUT` | 72 | — | HM2 BUDGET=70+2 ✓ | ❌ |
| `TIER_TIMEOUT_BUDGET_S` | 195 | — | dsv4p 90+72=162<195 ✓, glm5_2 120+72=192<195 ✓ | ❌ |
| `NVU_FORCE_STREAM_UPGRADE` | 0 | — | disabled，稳定 | ❌ |
| `NVU_EMPTY_200_FASTBREAK` | 2 | — | floor，零 empty_200 errors | ❌ |

**最终决策：NOP — 零参数变更。**

### 为何不继续调

1. **Zero dsv4p traffic post-R1652**: 容器重启后 43 分钟内仅 2 个 glm5_2 请求，零 dsv4p 请求。BUDGET=90 无法评估是否充分。需要 HM1 agent (hermes) 产生 dsv4p 流量才能验证。

2. **glm5_2 zombie_empty_completion (119/152, 78.3%):** NVCF server-side content_filter 返回空 completion。日志明确显示 `finish_reason=stop` 但 `content_chars=12 reasoning_chars=0 < 50`。典型 zombie 模式：5-10s 内返回 200 空 body。非本地配置可修。

3. **All ATE are pre-R1652**: 28 dsv4p ATE 全部在 18:00-18:04 UTC（旧 BUDGET=76），25 glm5_2 ATE 全部在 11:40-12:08 UTC。Post-R1652 ZERO ATE。

4. **429 cascade manageable**: 64 请求经历 multi-key cascade (≥2)，67% 最终成功。KEY_COOLDOWN=60=TIER_COOLDOWN=60 满足 KEY≥TIER 铁律。单 IP 架构下 62.3% 单 key 429 率是 NVCF rate-limit 固有特征。

5. **所有参数已在 floor**: UPSTREAM=66 (不可再减，NVCFPexecTimeout max~62s)，KEY_COOLDOWN=60 (不可再减，破 KEY≥TIER)，所有零值参数已在 floor。

6. **当前失败全为 upstream/NVCF 问题，非本地配置可修。**

---

## 五、执行记录

NOP — 无执行操作。

---

## 六、验证记录（Post-R1652，~43 min）

| 指标 | 数值 | 状态 |
|------|------|------|
| 总 SR | 50% (1/2) | ⚠️ 仅2请求，无统计意义 |
| dsv4p SR | N/A (0 requests) | ⚠️ 无流量 |
| glm5_2 SR | 50% (1/2) | ⚠️ zombie |
| dsv4p ATE post-R1652 | 0 | ✅ |
| glm5_2 ATE post-R1652 | 0 | ✅ |
| 429 / rate-limit | 2/2 (100%) | ✅ 单key非级联 |
| ERROR/WARN (logs) | 1 | ✅ |
| peer fallback 触发 | 0 | ✅ |
| fallback 触发 | 0 | ✅ |
| 容器 runtime | 43 min | ✅ |

---

## 七、结论

R1655 NOP。零参数变更。所有可调参数已在 floor。Post-R1652 仅 2 个 glm5_2 请求，零 dsv4p 流量 — BUDGET=90 无法评估。zombie_empty_completion (78.3% of failures) 是 NVCF content-filter server-side。下次轮到 HM2 时重评估：若 dsv4p 有流量且 ATE>0 → 检查 BUDGET=90 是否充分；若 zombie 持续高发 → 考虑 zombie 治理策略（但 zombie 是 NVCF server-side）。

**单参数少改多轮。铁律：只改 HM1 不改 HM2。**
## ⏳ 轮到HM1优化HM2
