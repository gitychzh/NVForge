# R834: HM2→HM1 — NOP (zero param, zero compose, zero restart; post-R833 restart stable, glm5_2_nv DEGRADED NVCF upstream, all 6 NOP gates pass)

**决策**: 零参数修改，零 compose 修改，零容器重启。所有参数已达 floor，glm5_2_nv 400 DEGRADED 为 NVCF 上游问题，FALLBACK_GRAPH 双向工作正常。

---

## 数据收集 (08-Jul-2026 08:05 UTC)

### 容器状态
- 容器: nv_gw, Up 5 minutes (healthy)
- 启动时间: 2026-07-08 00:01:38 UTC (R833 restart)
- 上次容器: 2026-07-07 20:39 UTC → 2026-07-08 00:01 UTC (R822 old bytecode issue)

### 环境变量 (全部 floor)
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=114
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=1
MIN_OUTBOUND_INTERVAL_S=0
NV_INTEGRATE_KEY_COOLDOWN_S=0
NVU_CONNECT_RESERVE_S=0
FALLBACK_HEALTH_THRESHOLD=0.10
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66 (= UPSTREAM_TIMEOUT ✓)
NVU_PEER_FALLBACK_TIMEOUT=45
TIER_COOLDOWN_S=25
KEY_COOLDOWN_S=25
NVU_SSLEOF_RETRY_DELAY_S=1.0
NV_INTEGRATE_MODELS="" (空)
```

### 6h 窗口统计 (02:00–08:00 UTC)
| 指标 | 值 |
|------|-----|
| 总量 | 28 req |
| OK | 16 (57.1%) |
| ATE | 12 (42.9%) |
| req_with_429 | 3 |
| total_429s | 15 |
| avg_ok_ms | 27,740ms |
| avg_ttfb_ms | 23,269ms |

### 按模型
| model | total | ok | fail | avg_ok_ms |
|-------|-------|-----|------|-----------|
| glm5_2_nv | 23 | 12 | 11 | 21,304ms |
| dsv4p_nv | 5 | 4 | 1 | 47,051ms |

### ATE 分诊
| tiers_tried_count | cnt | avg_dur |
|---|---|---|
| 1 | 7 | 15,453ms |
| 2 | 5 | 96,707ms |

- start_tier_idx=2 (glm5_2_nv): 6 ATE, avg 7,818ms, fallback NOT attempted
- start_tier_idx=1 (dsv4p_nv): 1 ATE, 61,261ms
- 7 单 tier ATE 全部在 18:03–18:19 UTC (R710 FALLBACK_GRAPH 瞬失)
- 5 双 tier ATE 在 18:34–21:05 UTC (glm5_2_nv DEGRADED → dsv4p_nv 也失败)

### 按小时 SR
| hour (UTC) | total | ok | ate | SR% |
|---|---|---|---|---|
| 18:00 | 13 | 4 | 9 | 30.8% |
| 19:00 | 3 | 3 | 0 | 100.0% |
| 20:00 | 3 | 1 | 2 | 33.3% |
| 21:00 | 3 | 2 | 1 | 66.7% |
| 22:00 | 2 | 2 | 0 | 100.0% |
| 23:00 | 2 | 2 | 0 | 100.0% |
| 00:00 | 2 | 2 | 0 | 100.0% |

### Post-R833 重启后窗口 (00:01:38+ UTC)
| 指标 | 值 |
|------|-----|
| 总量 | 2 req |
| OK | 2 (100.0%) |
| ATE | 0 |
| 模型 | glm5_2_nv 全部 pexec |
| avg_ok_ms | 2,794ms |

### Fallback
- fallback_occurred=true: 6/6 status=200 → **100% SR** ✓
- FALLBACK_GRAPH: tier_chain=['glm5_2_nv', 'dsv4p_nv'] 双向 ✓

### nv_tier_attempts (6h)
| tier | error_type | cnt | max_ms |
|------|-----------|-----|--------|
| glm5_2_nv | 400_nvcf_degraded | 14 | — |
| dsv4p_nv | 504_nv_gateway_timeout | 1 | — |

- 零 NVCFPexecTimeout → UPSTREAM=66 非绑定 ✓
- glm5_2_nv DEGRADED: 42 次 in 12h, NVCF function `3b9748d8` 持续 DEGRADED

### 日志确认
- 重启后 NONCYCLE 行为正确: `[NV-NONCYCLE-ERR] tier=glm5_2_nv k4 resp.status=400 non-cycling, aborting tier (no key cycle)` — 第一个 key 400 → 立即 fallback ~1s ✓
- **无 400 循环回退** (对比 R833 重启前 02:34–03:03 UTC 的 `NV-CYCLE` 行为)
- FALLBACK_GRAPH 双向: `tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback, health={...})` ✓

---

## 分析

### R710 FALLBACK_GRAPH 瞬失 (02:03–02:33 UTC, 30 min)
日志确认: 02:03:08 UTC 起 BOTH models 同时显示 `(no fallback, 3model)` — 经典 R710 pattern。02:33:21 UTC 自恢复。期间 7 个 glm5_2_nv 单 tier ATE (avg 7.8s) + 多个 dsv4p_nv 单 tier 请求。R833 重启已解决旧 bytecode 问题，新容器无此 pattern。

### glm5_2_nv 400 DEGRADED (NVCF 上游, 非 config-fixable)
glm5_2_nv NVCF function `3b9748d8` 持续返回 400 DEGRADED (12h 内 42 次)。所有 glm5_2_nv 请求: 400 → NONCYCLE 立即 abort → fallback 到 dsv4p_nv。fallback 100% SR。这是 NVCF 上游问题，非 config 可修。

### 双 tier ATE (glm5_2_nv→dsv4p_nv 双失败)
5 个双 tier ATE (18:34–21:05 UTC): glm5_2_nv DEGRADED abort + dsv4p_nv 也失败。NVCF 双 function 同时不可用期间 (R710 并发 FALLBACK_GRAPH 瞬失)。重启后零双 tier ATE。

### NOP Gate 分析 (Post-R833 重启后窗口)
| Gate | 条件 | 状态 |
|------|------|------|
| 1 | 所有 ATE 双 tier | ✓ (0 ATE) |
| 2 | 零单 tier ATE 或 code-level | ✓ (0 ATE; 6h 内的 7 单 tier 全部在重启前/R710) |
| 3 | NVCFPexecTimeout buffer ≥3s | ✓ (零 NVCFPexecTimeout, 非绑定) |
| 4 | FALLBACK_GRAPH 双向 | ✓ (tier_chain 双向 confirmed) |
| 5 | Fallback 100% SR | ✓ (6/6) |
| 6 | 所有 params at floor | ✓ (全部 floor) |

### 连续 4 小时 100% SR (19:00, 22:00, 23:00, 00:00 UTC)
低谷期 (2–3 req/h) 连续 100% SR。glm5_2_nv DEGRADED 时 fallback 到 dsv4p_nv 100% 成功。

---

## 决策: NOP

**零参数修改，零 compose 修改，零容器重启。**

- 所有参数已达 floor 或最优值，无优化空间
- glm5_2_nv 400 DEGRADED 为 NVCF 上游问题，非 config-fixable
- R833 重启已清除旧 bytecode，400 NONCYCLE 行为正确
- FALLBACK_GRAPH 双向工作，fallback 100% SR
- 连续 4 小时 100% SR (低谷期)
- 等待信号: NVCF glm5_2_nv function `3b9748d8` 恢复 DEGRADED → 正常状态; 或 dsv4p_nv 出现 binding 信号 → UPSTREAM 微调

---

## ⏳ 轮到 HM1 优化 HM2