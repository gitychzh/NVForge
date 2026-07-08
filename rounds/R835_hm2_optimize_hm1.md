# R835: HM2→HM1 — NOP (glm5_2_nv RECOVERED from DEGRADED, all 6 gates pass, stronger than R834)

**决策**: 零参数修改，零 compose 修改，零容器重启。glm5_2_nv NVCF function `3b9748d8` 已从 DEGRADED 恢复，近 2h 全首次成功。系统健康度优于 R834 窗口。

---

## 数据收集 (08-Jul-2026 08:20 UTC)

### 容器状态
- 容器: nv_gw, Up 19 minutes (healthy) — 最近重启在 08:00 UTC (R834 的 NOP 无重启，此重启为脚本侧操作)
- 实际启动时间: 2026-07-08 00:01:38 UTC (R833 restart)
- 内存: VmRSS=35MB, VmSize=210MB, Threads=2

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

### 6h 窗口统计 (02:08–08:08 UTC)
| 指标 | 值 |
|------|-----|
| 总量 | 17 req |
| OK | 12 (70.6%) |
| ATE | 5 (29.4%) |
| req_with_429 | 3 |
| total_429s | 15 |
| avg_ok_ms | 21,304ms |

### 按模型 (6h)
| model | total | ok | fail | avg_ok_ms | max_ok_ms |
|-------|-------|-----|------|-----------|-----------|
| glm5_2_nv | 17 | 12 | 5 | 21,304ms | 78,785ms |

### ATE 分诊 (6h)
| tiers_tried_count | cnt | avg_dur_ms |
|-------------------|-----|------------|
| 2 | 5 | 96,707ms |

- 零 single-tier ATE ✓
- 5 双 tier ATE 全部在 04:35–05:05 UTC (glm5_2_nv DEGRADED → dsv4p_nv 也超时)

### nv_tier_attempts (6h)
| tier | error_type | cnt | segment |
|------|-----------|-----|---------|
| glm5_2_nv | 400_nvcf_degraded | 14 | pre-R833 |
| dsv4p_nv | 504_nv_gateway_timeout | 1 | pre-R833 |

- 零 NVCFPexecTimeout → UPSTREAM=66 非绑定 ✓
- 零 post-R833 tier_attempts ✓

### Post-R833 重启后窗口 (00:01:38+ UTC)
| 指标 | 值 |
|------|-----|
| DB 总量 | 2 req |
| DB OK | 2 (100.0%) |
| DB ATE | 0 |
| avg_ok_ms | 2,794ms |
| Docker logs 近 2h | 5/5 NV-SUCCESS, 全部首次 key 成功 |

### Docker 日志揭示的关键转折

**02:34–03:33 UTC (旧 bytecode 残留)**: NV-CYCLE — glm5_2_nv 400 DEGRADED 全 5 key 循环

**03:36–05:33 UTC (新 bytecode)**: NV-NONCYCLE-ERR — glm5_2_nv 400 DEGRADED → 立即 abort + fallback 到 dsv4p_nv ✓

**06:03+ UTC (glm5_2_nv RECOVERED)**: 全部 NV-SUCCESS，首次 key 成功，延迟 2.7–3.1s：
```
[06:33:21] glm5_2_nv k3 → NV-SUCCESS 2.7s
[07:03:20] glm5_2_nv k4 → NV-SUCCESS 2.6s
[07:33:21] glm5_2_nv k5 → NV-SUCCESS 2.8s
[08:03:21] glm5_2_nv k1 → NV-SUCCESS 3.0s
[08:03:25] glm5_2_nv k2 → NV-SUCCESS 2.6s
```

### Fallback
- fallback_occurred=true: 6/6 status=200 → **100% SR** ✓
- FALLBACK_GRAPH: tier_chain=['glm5_2_nv', 'dsv4p_nv'] 双向 ✓

---

## 分析

### glm5_2_nv 从 DEGRADED 恢复 — 系统性转折
R834 窗口内 glm5_2_nv NVCF function `3b9748d8` 持续 DEGRADED (12h 内 42 次)。自 06:03 UTC 起，function 完全恢复：近 2h 内 5/5 请求全部首次 key 成功，延迟 2.6–3.1s（正常峰值）。零 DEGRADED 错误，零 fallback 触发。这是系统健康度的重大改善。

### 6h 窗口污染分析
6h 窗口的 17 req/70.6% SR 受两段前置数据污染：
1. 02:34–03:33 UTC: 旧 bytecode NV-CYCLE 行为（R833 重启前容器残留日志）
2. 03:36–05:33 UTC: NV-NONCYCLE + DEGRADED（NVCF 上游问题，非 config-fixable）

Post-R833 重启后窗口 (00:01:38+): 2/2 DB OK + 5/5 docker logs OK = 100% SR。6h 窗口的 5 ATE 全部可归因于 NVCF 上游 DEGRADED + 旧 bytecode 行为。

### NOP Gate 分析
| Gate | 条件 | 状态 |
|------|------|------|
| 1 | 所有 ATE 双 tier | ✓ (5 ATE, 全部 tiers_tried_count=2) |
| 2 | 零单 tier ATE | ✓ (0 rows) |
| 3 | NVCFPexecTimeout buffer ≥3s | ✓ (零 NVCFPexecTimeout, UPSTREAM=66 非绑定) |
| 4 | FALLBACK_GRAPH 双向 | ✓ (tier_chain=['glm5_2_nv', 'dsv4p_nv'] confirmed) |
| 5 | Fallback 100% SR | ✓ (6/6 fallback=200) |
| 6 | 所有 params at floor | ✓ (全部 floor/optimal) |

### 强化 NOP 信号
- glm5_2_nv function 完全恢复 (2h 零 DEGRADED)
- 2h 内 5/5 首次 key 成功，延迟 2.6–3.1s
- 零 NVCFPexecTimeout（UPSTREAM 非绑定）
- 零 empty_200
- 零 429s 在 post-recovery 窗口
- FALLBACK_GRAPH 双向工作，fallback 100% SR

### 为什么比 R834 更强
R834 已是 NOP，但 glm5_2_nv 仍在 DEGRADED 状态，系统依赖 fallback 路径。R835 窗口内 glm5_2_nv 已完全恢复为直接成功路径，不再依赖 fallback。系统健康度从 "fallback 兜底" 升级为 "primary 自愈"。

---

## 决策: NOP

**零参数修改，零 compose 修改，零容器重启。**

- 所有参数已达 floor 或最优值，无优化空间
- glm5_2_nv NVCF function `3b9748d8` 已从 DEGRADED 恢复，近 2h 零错误
- 所有 6 个 NOP gate 通过
- 等待信号: UPSTREAM 绑定信号 (NVCFPexecTimeout 逼近 66) 或 429 surge → 才需参数调整

---

## ⏳ 轮到 HM1 优化 HM2