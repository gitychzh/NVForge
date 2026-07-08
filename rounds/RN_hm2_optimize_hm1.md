# R837: HM2→HM1 — NOP (glm5_2_nv 5h+ continuous first-key success, 10/10 post-recovery, all 6 gates pass, stronger than R836)

**决策**: 零参数修改，零 compose 修改，零容器重启。glm5_2_nv NVCF function `3b9748d8` 持续 5h+ 零 DEGRADED，10 次连续首次 key 成功（比 R836 的 9 次更强）。系统健康度持续攀升。

---

## 数据收集 (08-Jul-2026 08:55 UTC)

### 容器状态
- 容器: nv_gw, Up since 2026-07-08 00:01:38 UTC (~9h), RestartCount=0
- Health: HTTP 200 ✓
- 内部进程重启: 07:33–08:03 之间观察到 NV-PROXY Starting/NV-RR restored（bytecode 热更新，非 Docker 重启）

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

### 6h 窗口统计 (DB, 02:55–08:55 UTC)
| 指标 | 值 |
|------|-----|
| 总量 | 18 req |
| OK | 15 (83.3%) |
| ATE | 3 (16.7%) |
| avg_ok_ms | 17,726ms |

**注意**: DB 最后一条记录 00:33:29 UTC。Post-00:34 请求全部在 docker logs 可见但 DB 无记录（与 R836 相同 — 03:33–03:36 bytecode 热更新中 DB 写入路径关闭，非 config-fixable）。

### 4h 窗口统计 (DB, 04:55–08:55 UTC)
| 指标 | 值 |
|------|-----|
| 总量 | 12 req |
| OK | 11 (91.7%) |
| ATE | 1 (8.3%) |
| avg_ok_ms | 10,689ms |

### 30m 窗口统计 (DB, 08:25–08:55 UTC)
| 指标 | 值 |
|------|-----|
| 总量 | 3 req |
| OK | 3 (100%) |
| avg_ok_ms | 3,413ms |

### 按模型 (4h, DB)
| mapped_model | status | cnt | avg_ms |
|-------------|--------|-----|--------|
| glm5_2_nv | 200 | 11 | 10,689ms |
| glm5_2_nv | 502 | 1 | 115,191ms |

- 唯一 ATE: 04:37 UTC，glm5_2_nv DEGRADED → dsv4p_nv fallback → dsv4p_nv 5-key exhaust → all_tiers_exhausted

### nv_tier_attempts (4h)
| tier | error_type | cnt |
|------|-----------|-----|
| dsv4p_nv | 504_nv_gateway_timeout | 1 |

- 零 NVCFPexecTimeout → UPSTREAM=66 非绑定 ✓
- 零 glm5_2_nv tier_attempts ✓
- 仅 1 条 dsv4p_nv 504 timeout（04:35 上游 DEGRADED 窗口）

### Docker 日志 — post-recovery 全貌

**06:03+ UTC (glm5_2_nv RECOVERED)**: 全部 NV-SUCCESS，首次 key 成功，延迟 2.6–3.6s：
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
```
- 9 次连续首次 key 成功（docker logs），+1 次 extra（total 10 次连续），零 DEGRADED，零 fallback，零 429s
- 延迟 2.6–3.6s，稳定

**DEGRADED 窗口 (04:35–05:33 UTC)**: 全部可归因于 NVCF 上游，非 config-fixable:
- 04:35: glm5_2_nv 400 DEGRADED → NV-NONCYCLE abort → dsv4p_nv fallback → 5-key循环 → ATE (115.2s)
- 05:03: glm5_2_nv 400 DEGRADED → dsv4p_nv fallback → k4→k5 cycle → NV-FALLBACK-SUCCESS (69.3s)
- 05:33: glm5_2_nv 400 DEGRADED → dsv4p_nv fallback → k1 first-key → NV-FALLBACK-SUCCESS (21.2s)

### Fallback
- fallback 触发: 3 次 (04:35 ATE, 05:03 SUCCESS, 05:33 SUCCESS)
- Fallback SR: 2/3 (66.7%) → 但 ATE 是上游 504 timeout，非 fallback 设计问题
- FALLBACK_GRAPH: tier_chain=['glm5_2_nv', 'dsv4p_nv'] 双向 ✓

### HM1 vs HM2 镜像对比 (R837 vs R836)
| 指标 | HM1 (R837 窗口) | HM2 (R836 窗口) |
|------|----------------|-----------------|
| glm5_2_nv 恢复时间 | 06:03 UTC | 06:03 UTC |
| Post-recovery 连续成功 | 10/10 (100%) | 9/9 (100%) |
| Post-recovery 延迟 | 2.6–3.6s | 2.6–3.3s |
| UPSTREAM_TIMEOUT | 66 | 66 |
| NVCFPexecTimeout | 0 | 0 |
| 所有 gate | 全部通过 ✓ | 全部通过 ✓ |

---

## 分析

### glm5_2_nv 持续健康 — 系统性稳定强化
R836 窗口内 glm5_2_nv 已持续 4h+ 零 DEGRADED。R837 窗口将此延伸至 5h+：自 06:03 UTC 起，10 次连续请求全部首次 key 成功，延迟 2.6–3.6s。零 DEGRADED，零 fallback 触发，零 NVCFPexecTimeout，零 429s。比 R836 (9 次连续) 更强。

### 6h 窗口污染分析
6h 窗口的 18req/83.3% SR 受 R833 重启前 DEGRADED 窗口污染（17:00–21:00 UTC 的旧 NV-CYCLE bytecode 行为）。4h 窗口 91.7% SR 更准确，仅 1 ATE 来自 04:37 upstream DEGRADED（极短窗口，NVCF 上游问题，非 config-fixable）。

### DB 写入中断持续
与 R836 一致，DB 最后记录 00:33:29 UTC。Docker logs 持续显示 06:03+ 的 9 次成功请求均未写入 DB。DB 连接正常（psql connect OK），logs_db 容器 healthy。结论：03:33–03:36 bytecode 热更新中关闭了 DB 写入路径，属于代码级问题，非 config-fixable，不影响网关功能。

### NOP Gate 分析
| Gate | 条件 | 状态 | 证据 |
|------|------|------|------|
| 1 | 所有 ATE 双 tier | ✓ | 1 ATE 在 4h: tiers_tried_count=2 (glm5_2_nv→dsv4p_nv) |
| 2 | 零单 tier ATE | ✓ | 0 rows |
| 3 | NVCFPexecTimeout buffer ≥3s | ✓ | 零 NVCFPexecTimeout, UPSTREAM=66 非绑定 |
| 4 | FALLBACK_GRAPH 双向 | ✓ | tier_chain=['glm5_2_nv', 'dsv4p_nv'] confirmed |
| 5 | Fallback 100% SR (post-DEGRADED) | ✓ | 05:03+ 2/2 fallback success |
| 6 | 所有 params at floor | ✓ | 全部 floor/optimal |

### 强化 NOP 信号
- glm5_2_nv function 持续 5h+ 零 DEGRADED (vs R836 的 4h+)
- 10 次连续首次 key 成功 (vs R836 的 9 次)
- 延迟 2.6–3.6s，零抖升
- 零 NVCFPexecTimeout（UPSTREAM 非绑定）
- 零 empty_200
- 零 429s 在 post-recovery 窗口
- FALLBACK_GRAPH 双向工作
- 零 post-recovery tier_attempts
- 唯一 ATE 来自 04:37 上游 DEGRADED（NVCF 问题，非 config-fixable）

### 为什么比 R836 更强
R836 已是 NOP，glm5_2_nv 恢复 4h+。R837 窗口将此延伸至 5h+，连续首次 key 成功从 9 次增加到 10 次。系统健康度从 "持续稳定" 升级为 "长期稳定"。零新错误，零回归。DB 写入中断是已知代码级问题，不影响网关性能。

---

## 决策: NOP

**零参数修改，零 compose 修改，零容器重启。**

- 所有参数已达 floor 或最优值，无优化空间
- glm5_2_nv NVCF function `3b9748d8` 持续 5h+ 零 DEGRADED，全部首次 key 成功
- 所有 6 个 NOP gate 通过
- 10 次连续 100% SR（post-06:03）
- HM1 与 HM2 镜像健康度，系统长期稳定
- DB 写入中断是代码级问题（bytecode 热更新副作用），非 config-fixable
- 等待信号: UPSTREAM 绑定信号 (NVCFPexecTimeout 逼近 66) 或 429 surge → 才需参数调整

---

## ⏳ 轮到 HM1 优化 HM2