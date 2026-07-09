# R1012: HM2→HM1 — NOP (minimax_m3_nv NVCF degraded, ms_gw no minimax, all params floor/optimal)

## TL;DR
NOP — 1h 89.8% SR (44/49), 5 ATE (3 minimax_m3_nv function-level degrade + 2 glm5_2_nv scheduler-gate). All params at floor/optimal. minimax failures not config-fixable: NVCF integrate timeout + pexec empty_200, ms_gw has no minimax model. Single param; iron rule: only change HM1 never HM2.

---

## 一、当前配置快照（R1012 部署前）

| # | 参数 | HM1 当前值 | 历史来源 |
|---|------|------------|----------|
| 1 | `UPSTREAM_TIMEOUT` | 66 | R988 |
| 2 | `TIER_TIMEOUT_BUDGET_S` | 112 | R971 |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | 0 | R638 |
| 4 | `NVU_PEXEC_TIMEOUT_FASTBREAK` | 1 | R997 |
| 5 | `TIER_COOLDOWN_S` | 25 | R492 |
| 6 | `NVU_PEER_FALLBACK_TIMEOUT` | 45 | R697 |
| 7 | `NVU_CONNECT_RESERVE_S` | 0 | R657 |
| 8 | `NVU_SSLEOF_RETRY_DELAY_S` | 1.0 | R543 |
| 9 | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 66 | R988 |
| 10 | `NVU_FORCE_STREAM_UPGRADE` | 0 | R692 |
| 11 | `NVU_EMPTY_200_FASTBREAK` | 1 | R1005 |
| 12 | `NV_INTEGRATE_MODELS` | glm5_2_nv,minimax_m3_nv | R833 |
| 13 | `NV_INTEGRATE_KEY_COOLDOWN_S` | 0 | R631 |
| 14 | `KEY_COOLDOWN_S` | 25 | R162 |
| 15 | `NVU_INTEGRATE_TIMEOUT_FASTBREAK` | 1 | R1010 |
| 16 | `NVU_INTEGRATE_THINKING_TIMEOUT_S` | 90 | R830b |
| 17 | `NVU_TIER_BUDGET_GLM5_2_NV` | 96 | R830b |
| 18 | `NVU_FALLBACK_HEALTH_THRESHOLD` | 0.10 | R982 |
| 19 | `FALLBACK_HEALTH_THRESHOLD` | 0.05 | (dead param) |
| 20 | `KEY_AUTHFAIL_COOLDOWN_S` | 60 | R922 |
| 21 | `NVU_PEER_FB_SKIP_MODELS` | glm5_2_nv,dsv4p_nv | R923 |
| 22 | `NVU_MS_GW_FALLBACK_TIMEOUT` | 45 | R832c |

---

## 二、漂移检测（Pre-change）

### 2.1 源1 — Compose 文件
```
UPSTREAM_TIMEOUT: "66" ✓
TIER_TIMEOUT_BUDGET_S: "112" ✓
NVU_PEXEC_TIMEOUT_FASTBREAK: "1" ✓
NVU_EMPTY_200_FASTBREAK: "1" ✓
NVU_INTEGRATE_TIMEOUT_FASTBREAK: "1" ✓
KEY_COOLDOWN_S: "25" ✓
TIER_COOLDOWN_S: "25" ✓
MIN_OUTBOUND_INTERVAL_S: "0" ✓
NVU_CONNECT_RESERVE_S: "0" ✓
NV_INTEGRATE_KEY_COOLDOWN_S: "0" ✓
```

### 2.2 源2 — 容器 env
```
UPSTREAM_TIMEOUT=66 ✓
TIER_TIMEOUT_BUDGET_S=112 ✓
NVU_PEXEC_TIMEOUT_FASTBREAK=1 ✓
NVU_EMPTY_200_FASTBREAK=1 ✓
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1 ✓
KEY_COOLDOWN_S=25 ✓
TIER_COOLDOWN_S=25 ✓
MIN_OUTBOUND_INTERVAL_S=0 ✓
NVU_CONNECT_RESERVE_S=0 ✓
NV_INTEGRATE_KEY_COOLDOWN_S=0 ✓
```

### 2.3 源3 — 容器启动时间
```
nv_gw Up 20 minutes (healthy), StartedAt ~2026-07-09T16:49:14Z
```

### 2.4 源4 — 运行时日志
```
docker logs nv_gw --tail 100 → 无 ERROR/WARN/panic
→ minimax_m3_nv: integrate timeout (90s) → pexec empty_200 → ABORT-NO-FALLBACK ×3
→ glm5_2_nv: integrate success (k1-k4) normal
→ kimi_nv: pexec success normal
→ dsv4p_nv: pexec success normal
```

**结论：四源全部通过，零漂移。**

---

## 三、数据摘要（部署前窗口，~1h: 16:30-17:04 UTC）

### 3.1 总体统计
| 指标 | 值 |
|------|-----|
| 总请求 | 49 |
| 成功 (200) | 44 |
| 错误 (502) | 5 |
| 成功率 | **89.8%** |

### 3.2 Per-tier 1h
| Tier | 请求 | OK | 错误 | SR | avg_ttfb | avg_dur |
|------|------|-----|------|-----|----------|---------|
| glm5_2_nv | 35 | 33 | 2 | 94.3% | 27,938ms | 38,060ms |
| kimi_nv | 6 | 6 | 0 | 100.0% | 12,310ms | 12,310ms |
| minimax_m3_nv | 5 | 2 | 3 | 40.0% | 4,837ms | 94,613ms |
| dsv4p_nv | 3 | 3 | 0 | 100.0% | 19,766ms | 19,766ms |

### 3.3 错误详情（5 ATE, 全部 upstream_type=NULL）
| 时间 (UTC) | Tier | 状态 | 耗时 | 错误类型 | tiers_tried |
|-----------|------|------|------|----------|-------------|
| 17:02:17 | minimax_m3_nv | 502 | 154,796ms | all_tiers_exhausted | 1 |
| 16:59:33 | minimax_m3_nv | 502 | 156,903ms | all_tiers_exhausted | 1 |
| 16:57:14 | minimax_m3_nv | 502 | 151,691ms | all_tiers_exhausted | 1 |
| 16:32:35 | glm5_2_nv | 502 | 174,716ms | all_tiers_exhausted | 1 |
| 16:30:22 | glm5_2_nv | 502 | 173,092ms | all_tiers_exhausted | 1 |

### 3.4 MS GW fallback (仅 glm5_2_nv)
| 时间 (UTC) | Tier | 状态 | 耗时 | fallback_to |
|-----------|------|------|------|-------------|
| 16:32:12 | glm5_2_nv | 200 | 34,734ms | glm5_2_ms ✓ |

### 3.5 nv_tier_attempts
1h: **0 rows** — 干净，无 tier 级错误记录
6h: 0 rows for minimax_m3_nv

### 3.6 Docker Logs 关键事件
```
[00:58:45] minimax_m3_nv integrate timeout k1 (90,746ms) → FASTBREAK=1 → integrate fail
          → pexec fallback: k3 empty_200 → FASTBREAK=1 → TIER-FAIL all 5 keys
          → ABORT-NO-FALLBACK (FALLBACK_GRAPH={}, ms_gw no minimax model)

[00:59:46] minimax_m3_nv integrate timeout k5 (90,663ms) → FASTBREAK=1 → integrate fail
          → pexec fallback: k3 empty_200 → FASTBREAK=1 → TIER-FAIL all 5 keys
          → ABORT-NO-FALLBACK

[01:02:10] minimax_m3_nv integrate timeout + pexec empty_200 → ABORT-NO-FALLBACK

[01:04:51] minimax_m3_nv integrate timeout + pexec empty_200 → ABORT-NO-FALLBACK
```

---

## 四、决策分析

| 参数 | 旧值 | 候选新值 | 数据支撑 | 决策 |
|------|------|---------|---------|------|
| — | — | — | 所有参数 floor/optimal | ❌ NOP |

### 否决原因

1. **minimax_m3_nv ATE 不可配置修复**：3个 ATE 全部是 NVCF function-level 降级（integrate timeout ~90s + pexec empty_200），不是参数调优可解决。ms_gw 无 minimax 模型（仅 glm5_2_ms），`NVU_MS_GW_FALLBACK_MODELMAP` 默认 `glm5_2_nv:glm5_2_ms` 不含 minimax → ABORT-NO-FALLBACK。添加 minimax ms_gw 支持需要 nv_gw MODELMAP 修改 + ms_gw ModelScope variant 注册 → 多服务源码变更，超出单参数铁律。

2. **glm5_2_nv scheduler-gate ATE**：upstream_type=NULL → 请求从未被调度到任何 tier 键，不是配置可修复。

3. **所有参数已 floor/optimal**：UPSTREAM=66, BUDGET=112, FASTBREAKs=1, COOLDOWNs=25/0, CONNECT_RESERVE=0, MIN_OUTBOUND=0。无进一步下调空间。

4. **ms_gw fallback 正常**：glm5_2_nv 成功 fallback 到 glm5_2_ms (34,734ms, 200 OK) — 机制有效但仅覆盖 glm5_2_nv。

5. **铁律**：只改 HM1 不改 HM2。

**最终决策**：NOP — 无变更。所有参数已 floor/optimal，可观测错误均非配置可修复。

---

## 五、变更

- **变更**: 无 (NOP)
- **验证**: 数据确认，所有参数 floor/optimal，无需调整
- **铁律**: 只改 HM1 不改 HM2

---

## 六、结论

R1012 NOP。minimax_m3_nv 3 ATE 是 NVCF function-level 降级（integrate timeout + pexec empty_200），ms_gw 无 minimax 模型导致 ABORT-NO-FALLBACK；glm5_2_nv 2 ATE 是 scheduler-gate。所有参数已 floor/optimal，无单参数可调空间。kimi_nv/dsv4p_nv 100% SR，glm5_2_nv 94.3% SR（ms_gw fallback 有效）。minimax 问题需 src 级修复（ms_gw 添加 minimax ModelScope variant），属未来多服务变更范畴。

**单参数少改多轮。铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2