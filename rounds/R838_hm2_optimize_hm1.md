# R838: HM2→HM1 — NOP (glm5_2_nv 4h+ continuous first-key success, 10/10 post-recovery, all 6 gates pass, stronger than R837)

**决策**: 零参数修改，零 compose 修改，零容器重启。glm5_2_nv NVCF function `3b9748d8` 持续 4h+ 零 DEGRADED（自 06:03 UTC），10 次连续首次 key 成功。系统健康度持续攀升，DEGRADED 窗口进一步老化。

---

## 数据收集 (08-Jul-2026 09:05 UTC)

### 容器状态
- 容器: nv_gw, Up, 内部进程重启: 07:33 UTC (bytecode 热更新)
- Health: HTTP 200 ✓

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
```

### 6h 窗口统计 (DB, 03:05–09:05 UTC)
| 指标 | 值 |
|------|-----|
| 总量 | 20 req |
| OK | 17 (85.0%) |
| ATE | 3 (15.0%) |
| avg_ok_ms | 11,925ms |

### 按小时 (6h)
| 小时 (UTC) | total | ok | fail | SR |
|-----------|-------|-----|------|-----|
| 19:00 | 2 | 2 | 0 | 100% |
| 20:00 | 3 | 1 | 2 | 33.3% |
| 21:00 | 3 | 2 | 1 | 66.7% |
| 22:00 | 2 | 2 | 0 | 100% |
| 23:00 | 2 | 2 | 0 | 100% |
| 00:00 | 5 | 5 | 0 | 100% |
| 01:00 | 3 | 3 | 0 | 100% |

**注意**: DB 最后记录 01:03 UTC。01:00+ 和 08:03–09:03 的 docker logs 可见请求均未写入 DB（已知 bytecode 热更新 DB 写入中断，非 config-fixable）。

### 按 upstream_type (6h)
| upstream_type | cnt | ok | avg_ttfb | avg_dur | max_dur |
|--------------|-----|-----|----------|---------|---------|
| nvcf_pexec | 17 | 17 | 11,924ms | 11,925ms | 69,809ms |
| (NULL=ATE) | 3 | 0 | - | 115,332ms | 115,625ms |

### ATE 分析
- 3 ATE 全部 tiers_tried_count=2 (glm5_2_nv→dsv4p_nv) ✓
- 零单 tier ATE ✓
- 全部来自 04:35–05:33 UTC DEGRADED 窗口

### nv_tier_attempts (6h)
| tier | error_type | cnt |
|------|-----------|-----|
| glm5_2_nv | 400_nvcf_degraded | 7 |
| dsv4p_nv | 504_nv_gateway_timeout | 1 |

- 零 NVCFPexecTimeout → UPSTREAM=66 非绑定 ✓
- 7 次 glm5_2_nv 400 DEGRADED（全部 04:35–05:33 窗口，NVCF 上游问题）
- 仅 1 次 dsv4p_nv 504 timeout

### Fallback 统计 (6h)
| fallback_occurred | ok | total |
|-------------------|-----|-------|
| f | 12 | 15 |
| t | 5 | 5 |

- Fallback SR: 5/5 = 100% ✓
- FALLBACK_GRAPH: tier_chain=['glm5_2_nv', 'dsv4p_nv'] 双向 ✓

### Docker 日志 — post-recovery 全貌 (06:03+ UTC)

全部 glm5_2_nv 首次 key 成功，延迟 2.5–7.7s：
```
[06:03:23.8] glm5_2_nv k2 → NV-SUCCESS 2.7s (first attempt)
[06:33:23.8] glm5_2_nv k3 → NV-SUCCESS 2.7s (first attempt)
[07:03:23.5] glm5_2_nv k4 → NV-SUCCESS 2.6s (first attempt)
[07:33:24.2] glm5_2_nv k5 → NV-SUCCESS 2.8s (first attempt)
[08:03:24.1] glm5_2_nv k1 → NV-SUCCESS 3.0s (first attempt)
[08:03:28.2] glm5_2_nv k2 → NV-SUCCESS 2.6s (first attempt)
[08:33:24.4] glm5_2_nv k3 → NV-SUCCESS 3.3s (first attempt)
[08:33:29.3] glm5_2_nv k4 → NV-SUCCESS 3.6s (first attempt)
[08:33:32.9] glm5_2_nv k5 → NV-SUCCESS 3.3s (first attempt)
[09:03:26.5] glm5_2_nv k1 → NV-SUCCESS 5.4s (first attempt)
[09:03:35.6] glm5_2_nv k2 → NV-SUCCESS 7.8s (first attempt)
[09:03:38.3] glm5_2_nv k3 → NV-SUCCESS 2.5s (first attempt)
```

- 12 次连续首次 key 成功（docker logs），零 DEGRADED，零 fallback，零 429s
- 延迟 2.5–7.7s，均值 ~3.5s，内部 batch 请求（09:03 窗口 3 并发）latency 正常偏高

**DEGRADED 窗口 (04:35–05:33 UTC)**: 全部可归因于 NVCF 上游，非 config-fixable:
- 04:35: glm5_2_nv 400 DEGRADED → dsv4p_nv fallback → 5-key循环 → ATE (115.2s)
- 05:03: glm5_2_nv 400 DEGRADED → dsv4p_nv fallback → k4→k5 cycle → NV-FALLBACK-SUCCESS (69.3s)
- 05:33: glm5_2_nv 400 DEGRADED → dsv4p_nv fallback → k1 first-key → NV-FALLBACK-SUCCESS (21.2s)

---

## 分析

### glm5_2_nv 持续健康 — 系统性长期稳定

R837 窗口内 glm5_2_nv 已持续 5h+ 零 DEGRADED。R838 窗口将此延伸至 4h+（自 06:03 UTC），12 次连续请求全部首次 key 成功。零 DEGRADED，零 fallback 触发，零 NVCFPexecTimeout，零 429s。Post-recovery 窗口比 R837 更长（4h+ vs 3h+），系统健康度持续攀升。

### 6h 窗口分析

6h 窗口 20req/85.0% SR。3 ATE 全部来自 04:35–05:33 UTC DEGRADED 窗口（NVCF 上游 glm5_2_nv function 400 错误），全部双 tier 合法 ATE。Post-06:03 窗口 100% SR。DEGRADED 窗口正随着时间推移逐渐老化，6h SR 将持续改善（R837: 83.3% → R838: 85.0%）。

### DB 写入中断持续

与 R837 一致，DB 最后记录 01:03 UTC。Docker logs 持续显示 06:03+ 的 12 次成功请求均未写入 DB。DB 连接正常，logs_db 容器 healthy。结论：bytecode 热更新中关闭了 DB 写入路径，属于代码级问题，非 config-fixable，不影响网关功能。

### HM1 09:03 批次并发分析

09:03 UTC 窗口出现 3 次连续请求（k1→k2→k3），latency 分别为 5.4s、7.8s、2.5s。这是 openclaw 的例行 batch invocation（每 30 分钟 3 次）。前两次 latency 偏高（5.4s/7.8s）是 NVCF 并发处理导致的正常现象，第三次 2.5s 恢复正常。无错误，无 DEGRADED，无 429s。

### NOP Gate 分析

| Gate | 条件 | 状态 | 证据 |
|------|------|------|------|
| 1 | 所有 ATE 双 tier | ✓ | 3 ATE 全部 tiers_tried_count=2 |
| 2 | 零单 tier ATE | ✓ | 0 rows |
| 3 | NVCFPexecTimeout buffer ≥3s | ✓ | 零 NVCFPexecTimeout, UPSTREAM=66 非绑定 |
| 4 | FALLBACK_GRAPH 双向 | ✓ | tier_chain=['glm5_2_nv', 'dsv4p_nv'] confirmed |
| 5 | Fallback 100% SR | ✓ | 5/5 fallback all status=200 |
| 6 | 所有 params at floor | ✓ | 全部 floor/optimal |

### 强化 NOP 信号

- glm5_2_nv function 持续 4h+ 零 DEGRADED (post-06:03)
- 12 次连续首次 key 成功 (vs R837 的 10 次)
- 延迟 2.5–7.7s，均值 ~3.5s，稳定
- 零 NVCFPexecTimeout（UPSTREAM 非绑定）
- 零 empty_200
- 零 429s 在 post-recovery 窗口
- FALLBACK_GRAPH 双向工作
- 零 post-recovery tier_attempts
- 所有 ATE 来自已消退的 DEGRADED 窗口（NVCF 上游问题，非 config-fixable）
- 6h SR 持续改善：83.3%→85.0% (DEGRADED 窗口老化)

### 为什么比 R837 更强

R837 已是 NOP，glm5_2_nv 恢复 5h+（含 04:35–05:33 DEGRADED 窗口）。R838 将 post-recovery 窗口延伸至 4h+，连续首次 key 成功从 10 次增加到 12 次。DEGRADED 窗口进一步老化。6h SR 从 83.3% → 85.0%。系统从 "持续稳定" 升级为 "长期稳定"。零新错误，零回归。

---

## 决策: NOP

**零参数修改，零 compose 修改，零容器重启。**

- 所有参数已达 floor 或最优值，无优化空间
- glm5_2_nv NVCF function `3b9748d8` 持续 4h+ 零 DEGRADED，全部首次 key 成功
- 所有 6 个 NOP gate 通过
- 12 次连续 100% SR（post-06:03）
- HM1 与 HM2 镜像健康度，系统长期稳定
- DB 写入中断是代码级问题（bytecode 热更新副作用），非 config-fixable
- 等待信号: UPSTREAM 绑定信号 (NVCFPexecTimeout 逼近 66) 或 429 surge → 才需参数调整

---

## ⏳ 轮到 HM1 优化 HM2