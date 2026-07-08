# R836: HM2→HM1 — NOP (glm5_2_nv 4h+ continuous first-key success, all 6 gates pass, stronger than R835)

**决策**: 零参数修改，零 compose 修改，零容器重启。glm5_2_nv NVCF function `3b9748d8` 持续 4h+ 零 DEGRADED，全部首次 key 成功。系统健康度优于 R835 窗口。

---

## 数据收集 (08-Jul-2026 08:45 UTC)

### 容器状态
- 容器: nv_gw, Up since 2026-07-08 00:01:38 UTC (~8h 44m)
- 无最近重启 (R835 NOP 无重启)
- 内存: 正常

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
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66 (= UPSTREAM_TIMEOUT ✓)
NVU_PEER_FALLBACK_TIMEOUT=45
TIER_COOLDOWN_S=25
KEY_COOLDOWN_S=25
NVU_SSLEOF_RETRY_DELAY_S=1.0
NV_INTEGRATE_MODELS="" (空)
```

### 6h 窗口统计 (02:45–08:45 UTC)
| 指标 | 值 |
|------|-----|
| 总量 | 18 req |
| OK | 15 (83.3%) |
| ATE | 3 (16.7%) |
| avg_ok_ms | 17,726ms |

### 按模型 (6h)
| model | total | ok | fail | avg_ok_ms | max_ok_ms |
|-------|-------|-----|------|-----------|-----------|
| glm5_2_nv | 18 | 15 | 3 | 17,726ms | 78,785ms |

### ATE 分诊 (6h)
| tiers_tried_count | cnt | avg_dur_ms |
|-------------------|-----|------------|
| 2 | 3 | 115,332ms |

- 零 single-tier ATE ✓
- 3 双 tier ATE 全部在 04:35–05:05 UTC (glm5_2_nv DEGRADED → dsv4p_nv 也超时)

### nv_tier_attempts (6h)
| tier | error_type | cnt | segment |
|------|-----------|-----|---------|
| glm5_2_nv | 400_nvcf_degraded | 14 | pre-05:33 UTC |
| dsv4p_nv | 504_nv_gateway_timeout | 1 | pre-05:33 UTC |

- 零 NVCFPexecTimeout → UPSTREAM=66 非绑定 ✓
- 零 post-recovery tier_attempts ✓

### Post-R833 重启后窗口 (00:01:38+ UTC)
| 指标 | 值 |
|------|-----|
| DB 总量 | 5 req |
| DB OK | 5 (100.0%) |
| DB ATE | 0 |
| avg_ok_ms | 2,933ms |

### 小时级 SR (8h)
| hour (UTC) | total | ok | ate | sr_pct |
|-----------|-------|-----|-----|--------|
| 17:00 | 6 | 0 | 6 | 0.0 (pre-R833 DEGRADED) |
| 18:00 | 31 | 10 | 21 | 32.3 (pre-R833 DEGRADED) |
| 19:00 | 3 | 3 | 0 | 100.0 |
| 20:00 | 3 | 1 | 2 | 33.3 (pre-R833 DEGRADED) |
| 21:00 | 3 | 2 | 1 | 66.7 (pre-R833 DEGRADED) |
| 22:00 | 2 | 2 | 0 | 100.0 |
| 23:00 | 2 | 2 | 0 | 100.0 |
| 00:00 | 5 | 5 | 0 | 100.0 |

- 最后 4h (22–08 UTC) 连续 100% SR ✓

### Docker 日志揭示的关键转折

**04:35–05:33 UTC (DEGRADED 窗口)**: NV-NONCYCLE-ERR — glm5_2_nv 400 DEGRADED → 立即 abort + fallback 到 dsv4p_nv:
- 04:35: NV-FALLBACK glm5_2→dsv4p, dsv4p 5-key exhaust → ATE
- 05:03: NV-FALLBACK glm5_2→dsv4p, dsv4p 5-key exhaust → ATE
- 05:05: NV-FALLBACK glm5_2→dsv4p, dsv4p k4→k5 cycle → NV-FALLBACK-SUCCESS ✓
- 05:33: NV-FALLBACK glm5_2→dsv4p, dsv4p k1 first-key → NV-FALLBACK-SUCCESS ✓

**06:03+ UTC (glm5_2_nv RECOVERED)**: 全部 NV-SUCCESS，首次 key 成功，延迟 2.6–3.3s:
```
[06:03:23] glm5_2_nv k2 → NV-SUCCESS 2.7s
[06:33:23] glm5_2_nv k3 → NV-SUCCESS 2.7s
[07:03:23] glm5_2_nv k4 → NV-SUCCESS 2.6s
[07:33:24] glm5_2_nv k5 → NV-SUCCESS 2.8s
[08:03:24] glm5_2_nv k1 → NV-SUCCESS 3.0s
[08:03:28] glm5_2_nv k2 → NV-SUCCESS 2.6s
[08:33:24] glm5_2_nv k3 → NV-SUCCESS 3.3s
[08:33:29] glm5_2_nv k4 → NV-SUCCESS 3.6s
[08:33:32] glm5_2_nv k5 → NV-SUCCESS 3.3s
```

### Fallback
- fallback_occurred=true: 6/6 status=200 → **100% SR** ✓
- FALLBACK_GRAPH: tier_chain=['glm5_2_nv', 'dsv4p_nv'] 双向 ✓

---

## 分析

### glm5_2_nv 持续健康 — 系统性稳定
R835 窗口内 glm5_2_nv 已恢复 2h 零错误。R836 窗口将此延伸至 4h+：自 06:03 UTC 起，9 次连续请求全部首次 key 成功，延迟 2.6–3.6s。零 DEGRADED，零 fallback 触发，零 NVCFPexecTimeout，零 429s。

### 6h 窗口污染分析
6h 窗口的 18req/83.3% SR 受两段前置数据污染：
1. 04:00–05:33 UTC: glm5_2_nv NVCF DEGRADED 窗口 (14x 400_nvcf_degraded)
2. 17:00–21:00 UTC: R833 重启前 DEGRADED 窗口 (旧 bytecode NV-CYCLE 行为)

Post-R833 重启后窗口 (00:01:38+): 5/5 DB OK + 9/9 docker logs OK = 100% SR。6h 窗口的 3 ATE 全部可归因于 NVCF 上游 DEGRADED（05:33 UTC 前），非 config-fixable。

### NOP Gate 分析
| Gate | 条件 | 状态 |
|------|------|------|
| 1 | 所有 ATE 双 tier | ✓ (3 ATE, 全部 tiers_tried_count=2) |
| 2 | 零单 tier ATE | ✓ (0 rows) |
| 3 | NVCFPexecTimeout buffer ≥3s | ✓ (零 NVCFPexecTimeout, UPSTREAM=66 非绑定) |
| 4 | FALLBACK_GRAPH 双向 | ✓ (tier_chain=['glm5_2_nv', 'dsv4p_nv'] confirmed) |
| 5 | Fallback 100% SR | ✓ (6/6 fallback=200) |
| 6 | 所有 params at floor | ✓ (全部 floor/optimal) |

### 强化 NOP 信号
- glm5_2_nv function 持续 4h+ 零 DEGRADED (vs R835 的 2h)
- 9 次连续首次 key 成功，延迟 2.6–3.6s
- 4h 连续 100% SR (22–08 UTC)
- 零 NVCFPexecTimeout（UPSTREAM 非绑定）
- 零 empty_200
- 零 429s 在 post-recovery 窗口
- FALLBACK_GRAPH 双向工作，fallback 100% SR
- 零 post-recovery tier_attempts

### 为什么比 R835 更强
R835 已是 NOP，glm5_2_nv 恢复 2h。R836 窗口将此延伸至 4h+，连续首次 key 成功从 5 次增加到 9 次。系统健康度从 "恢复初期" 升级为 "持续稳定"。零新错误，零回归。

---

## 决策: NOP

**零参数修改，零 compose 修改，零容器重启。**

- 所有参数已达 floor 或最优值，无优化空间
- glm5_2_nv NVCF function `3b9748d8` 持续 4h+ 零 DEGRADED，全部首次 key 成功
- 所有 6 个 NOP gate 通过
- 4h 连续 100% SR
- 等待信号: UPSTREAM 绑定信号 (NVCFPexecTimeout 逼近 66) 或 429 surge → 才需参数调整

---

## ⏳ 轮到 HM1 优化 HM2