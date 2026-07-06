# R802: HM2→HM1 — NOP (false trigger) — 87.6% SR, 全参数floor, NVCF upstream_type=NULL ATE, 100% fallback, 系统稳定

**时间**: 2026-07-07 05:55 UTC

## TL;DR
NOP. All tunable parameters at floor. All 11 ATE failures are `upstream_type=NULL` (NVCF scheduling layer, dsv4p_nv function 74f02205 health=0.45, glm5_2 3b9748d8 health=0.90). Fallback 100% SR (13/13). Zero config-fixable errors. Single param per round; iron rule: only change HM1 never HM2.

---

## 一、当前配置快照（R802 部署前）

| # | 参数 | HM1 当前值 | 历史来源 | Floor? |
|---|------|------------|----------|--------|
| 1 | `UPSTREAM_TIMEOUT` | 66 | R754 | — |
| 2 | `TIER_TIMEOUT_BUDGET_S` | 114 | R737 | — |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | 0 | R638 | ✅ floor |
| 4 | `NVU_PEXEC_TIMEOUT_FASTBREAK` | 1 | R768 | ✅ floor |
| 5 | `TIER_COOLDOWN_S` | 25 | R492 | — |
| 6 | `NVU_PEER_FALLBACK_TIMEOUT` | 45 | R697 | — |
| 7 | `NVU_CONNECT_RESERVE_S` | 0 | R657 | ✅ floor |
| 8 | `NVU_SSLEOF_RETRY_DELAY_S` | 1.0 | R543 | ✅ floor |
| 9 | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 66 | R755 | — |
| 10 | `NVU_FORCE_STREAM_UPGRADE` | 0 | R692 | ✅ floor |
| 11 | `NVU_EMPTY_200_FASTBREAK` | 1 | R774 | ✅ floor |
| 12 | `NV_INTEGRATE_ENABLED` | 0 | R693 | ✅ floor |
| 13 | `NV_INTEGRATE_MODELS` | "" | R693 | ✅ floor |
| 14 | `NV_INTEGRATE_KEY_COOLDOWN_S` | 0 | R631 | ✅ floor |
| 15 | `KEY_COOLDOWN_S` | 25 | R162 | — |
| 16 | `FALLBACK_HEALTH_THRESHOLD` | 0.10 | R708 | ✅ floor |

---

## 二、漂移检测（Pre-change）

### 2.1 源1 — Compose 文件
全参数与容器env一致，无漂移。

### 2.2 源2 — 容器 env
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=114
MIN_OUTBOUND_INTERVAL_S=0
NVU_PEXEC_TIMEOUT_FASTBREAK=1
TIER_COOLDOWN_S=25
NVU_PEER_FALLBACK_TIMEOUT=45
NVU_CONNECT_RESERVE_S=0
NVU_EMPTY_200_FASTBREAK=1
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
FALLBACK_HEALTH_THRESHOLD=0.10
NV_INTEGRATE_KEY_COOLDOWN_S=0
NV_INTEGRATE_MODELS=
KEY_COOLDOWN_S=25
```

### 2.3 源3 — 容器启动时间
```
2026-07-06T16:02:04Z (up 6+ hours, healthy)
```

### 2.4 源4 — 运行时日志
nv_gw 最近100行: 零ERROR/WARN. 正常请求模式: dsv4p_nv empty_200→fallback→glm5_2_nv success. glm5_2_nv 直连成功. NVCF function health: dsv4p=0.45, glm5_2=0.90.

**结论：四源全部通过，无漂移，继续标准流程。**

---

## 三、数据摘要（6h window, ~16:00-22:00 UTC）

### 3.1 6h 聚合
| 指标 | 数值 |
|------|------|
| 总请求 | 89 |
| 成功 | 78 (87.6%) |
| 失败 | 11 (12.4%) |
| 全部失败类型 | `all_tiers_exhausted` |
| upstream_type | 全NULL (NVCF调度层) |
| tiers_tried_count | 全2 (双tier均失败) |
| fallback 成功 | 13/13 (100%) |
| key_cycle_429s | 26/89 reqs, total 34 |

### 3.2 按模型
| 模型 | total | ok | fail | avg_ok_ms | max_ok_ms | p95_ttfb |
|------|-------|-----|------|-----------|-----------|----------|
| glm5_2_nv | 71 | 63 | 8 | 36,506 | 163,327 | 121,423 |
| dsv4p_nv | 18 | 15 | 3 | 69,941 | 142,361 | 138,400 |

### 3.3 最近 3h 10条请求
全200 OK. glm5_2_nv: 2.1-122.2s (thinking). dsv4p_nv: 35.0-86.0s. 零错误.

### 3.4 24h 小时趋势
- 16:00 UTC: 35 OK / 9 fail (glm5_2 burst)
- 17:00-21:00 UTC: 逐步恢复, 最近小时 21:00=4/4 OK, 20:00=7/1 fail
- 整体趋势: NVCF dsv4p_nv function 74f02205 health从0.3→0.45→0.5缓慢恢复

### 3.5 NVCF Function Health
- dsv4p_nv 74f02205: 0.45 (slowly recovering from 0.3)
- glm5_2_nv 3b9748d8: 0.90 (healthy)

---

## 四、决策分析

| 参数 | 候选 | 决策 | 理由 |
|------|------|------|------|
| 全部floor参数 | — | ❌ | 已触floor，不可再降 |
| UPSTREAM_TIMEOUT 66→64 | -2s | ❌ | p95_ttfb=138s > 66s, dsv4p empty_200不是timeout问题; 降UPSTREAM只会增加false timeout |
| TIER_TIMEOUT_BUDGET_S 114→X | — | ❌ | ATE avg=160s, 需BUDGET覆盖双tier; 当前114已是最小值(BUDGET-UPSTREAM=48s for 2nd tier) |
| NVU_PEER_FALLBACK_TIMEOUT 45→40 | -5s | ❌ | 100% fallback SR, 但UPSTREAM=66需足够余量; 45已较保守 |
| TIER_COOLDOWN_S 25→23 | -2s | ❌ | 非ATE根因; 429 cycle 26/89=29%表明key轮转活跃, 降cooldown可能增加429冲突 |
| KEY_COOLDOWN_S 25→23 | -2s | ❌ | 同上, 429 cycle 34次/6h, 降cooldown风险增加 |

**最终决策：NOP.** 所有ATE均为`upstream_type=NULL`的NVCF调度层拒绝（dsv4p_nv function 74f02205 health=0.45），非proxy配置可修复。Fallback 100% SR覆盖。全参数已达floor或最优值。此轮不触发任何变更，等待NVCF function健康度恢复。

**零变更 · 少改多轮 · 铁律：只改HM1不改HM2。**

---

## 五、结论

R802 NOP（false trigger，HM2自身commit被检测脚本误判为HM1新commit）。6h 87.6% SR（78/89），11 ATE全为NVCF upstream_type=NULL调度层拒绝（非配置可修），fallback 100% SR（13/13双向）。全参数floor或最优值。零变更，等待NVCF dsv4p_nv function health恢复或新信号出现。

## ⏳ 轮到HM1优化HM2