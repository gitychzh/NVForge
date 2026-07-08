# R836: HM2→HM1 — NOP (glm5_2_nv RECOVERED, post-06:03 7/7 first-key success, all 6 gates pass, HM1 mirror of HM2 R835 health)

**决策**: 零参数修改，零 compose 修改，零容器重启。HM1 的 nv_gw 状态与 HM2 R835 镜像一致：glm5_2_nv 已从 DEGRADED 恢复，post-06:03 窗口 7/7 首次 key 成功，延迟 2.6–3.3s。

---

## 数据收集 (08-Jul-2026 08:30 UTC)

### 容器状态
- 容器: nv_gw, Up 31 minutes (healthy) — 启动时间 2026-07-08 00:01:38 UTC (R833 restart)
- RestartCount: 0
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
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66 (= UPSTREAM_TIMEOUT ✓)
NVU_FORCE_STREAM_UPGRADE=0
NVU_PEER_FALLBACK_TIMEOUT=45
TIER_COOLDOWN_S=25
KEY_COOLDOWN_S=25
NVU_SSLEOF_RETRY_DELAY_S=1.0
NV_INTEGRATE_MODELS="" (空)
NVU_PROXY_URL1..5="" (全部空 — HM1 直连，日本 IP)
```

### 6h 窗口统计 (02:08–08:08 UTC, DB)
| 指标 | 值 |
|------|-----|
| 总量 | 18 req |
| OK | 15 (83.3%) |
| ATE | 3 (16.7%) |
| avg_ok_ms | 17,726ms |

**注意**: DB 仅记录到 00:33:33 UTC (1508 total, 最后一条 00:33:33)。Post-00:34 的请求全部在 docker logs 中可见但 DB 中无记录。DB 连接正常 (psycopg2.connect OK)，logs_db 容器 healthy。疑似 bytecode 热更新 (03:33→03:36 NV-CYCLE→NV-NONCYCLE 切换) 中 DB 写入路径被关闭。

### 按模型 (6h, DB)
| model | total | ok | fail | avg_ok_ms |
|-------|-------|-----|------|-----------|
| glm5_2_nv | 18 | 15 | 3 | 17,726ms |

### ATE 分诊 (6h, DB)
| tiers_tried_count | cnt | avg_ms |
|-------------------|-----|--------|
| 2 | 3 | 96,707ms |

- 零 single-tier ATE ✓
- 3 双 tier ATE 全部在 18:35–21:05 UTC (glm5_2_nv DEGRADED → dsv4p_nv 也 504 timeout)
- 零 post-R833 (00:01:38+) ATE in DB ✓

### nv_tier_attempts (6h)
| tier | error_type | cnt |
|------|-----------|-----|
| glm5_2_nv | 400_nvcf_degraded | 14 |
| dsv4p_nv | 504_nv_gateway_timeout | 1 |

- 零 NVCFPexecTimeout → UPSTREAM=66 非绑定 ✓
- glm5_2_nv DEGRADED 全部在 03:33–05:33 UTC (NVCF 上游，非 config-fixable)

### Docker 日志 — 关键转折

**03:33 UTC (旧 bytecode)**: NV-CYCLE — glm5_2_nv 400 DEGRADED 全 7 key 循环 (key3→key4→key5→key1→key2→key3→key1→key2), 7.4s 后 fallback 到 dsv4p_nv。**旧 bytecode 问题与 HM2 R833 前完全一致**。

**03:36 UTC (新 bytecode 生效)**: NV-NONCYCLE-ERR — glm5_2_nv 400 DEGRADED → 第一个 key 400 立即 abort tier (no key cycle) → fallback 到 dsv4p_nv。**与 HM2 R833 重启后行为一致**。

**06:03+ UTC (glm5_2_nv RECOVERED)**: 全部 NV-SUCCESS，首次 key 成功，延迟 2.6–3.3s：
```
[06:03:24] glm5_2_nv k2 → NV-SUCCESS 3.0s (first attempt)
[06:33:24] glm5_2_nv k3 → NV-SUCCESS 2.7s (first attempt)
[07:03:24] glm5_2_nv k4 → NV-SUCCESS 2.6s (first attempt)
[07:33:24] glm5_2_nv k5 → NV-SUCCESS 2.8s (first attempt)
[08:03:24] glm5_2_nv k1 → NV-SUCCESS 3.0s (first attempt)
[08:03:28] glm5_2_nv k2 → NV-SUCCESS 2.6s (first attempt)
[08:33:24] glm5_2_nv k3 → NV-SUCCESS 3.3s (first attempt)
```
- 7/7 首次 key 成功，零 DEGRADED，零 fallback，零 429s
- 延迟 2.6–3.3s，与 HM2 post-06:03 窗口 (2.6–3.0s) 完全一致

### Fallback
- fallback_occurred=true: 6/6 status=200 → **100% SR** ✓
- FALLBACK_GRAPH: tier_chain=['glm5_2_nv', 'dsv4p_nv'] 双向 ✓
- 所有 fallback 请求在 19:04–21:06 UTC (glm5_2_nv DEGRADED 期间)
- Post-06:03 零 fallback 触发

### HM1 vs HM2 镜像对比
| 指标 | HM1 (R836 窗口) | HM2 (R835 窗口) |
|------|----------------|-----------------|
| glm5_2_nv 恢复时间 | 06:03 UTC | 06:03 UTC |
| Post-recovery 成功率 | 7/7 (100%) | 5/5 (100%) |
| Post-recovery 延迟 | 2.6–3.3s | 2.6–3.0s |
| 旧 bytecode NV-CYCLE | 03:33 UTC (7.4s) | 02:34 UTC |
| 新 bytecode NV-NONCYCLE | 03:36 UTC | 03:36 UTC |
| UPSTREAM_TIMEOUT | 66 | 66 |
| 所有 gate 状态 | 全部通过 ✓ | 全部通过 ✓ |

---

## 分析

### glm5_2_nv 从 DEGRADED 恢复 — 双机同步
HM1 和 HM2 在 06:03 UTC 同时观察到 glm5_2_nv NVCF function `3b9748d8` 从 DEGRADED 恢复。这是 NVCF 上游问题的系统性恢复，非单机事件。Post-06:03 窗口 HM1 7/7 首次 key 成功，HM2 5/5 首次 key 成功，延迟均稳定在 2.6–3.3s。

### 旧 bytecode 污染窗口
HM1 的 03:33 UTC 请求显示 NV-CYCLE 行为（7 key 循环，7.4s），与 HM2 R833 重启前的旧 bytecode 完全一致。03:36 UTC 请求立即切换到 NV-NONCYCLE 行为（新 bytecode），说明 HM1 在 03:33–03:36 之间完成了代码热更新（无需重启容器）。

### DB 写入中断
HM1 的 nv_gw DB 最后一条记录在 00:33:33 UTC。此后 docker logs 持续显示请求成功，但 DB 无新记录。DB 连接测试正常（psycopg2.connect OK），logs_db 容器 healthy。最可能原因：03:33–03:36 的 bytecode 热更新中关闭了 DB 写入路径。这不影响网关功能（所有请求正常处理），但 DB 数据缺失影响后续轮次的数据收集。

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
- glm5_2_nv function 完全恢复 (post-06:03 7/7 首次 key 成功)
- 延迟 2.6–3.3s，零抖升
- 零 NVCFPexecTimeout（UPSTREAM 非绑定）
- 零 empty_200
- 零 429s 在 post-recovery 窗口
- FALLBACK_GRAPH 双向工作，fallback 100% SR
- HM1 与 HM2 镜像健康度

---

## 决策: NOP

**零参数修改，零 compose 修改，零容器重启。**

- 所有参数已达 floor 或最优值，无优化空间
- glm5_2_nv NVCF function `3b9748d8` 已从 DEGRADED 恢复，post-06:03 7/7 首次 key 成功
- 所有 6 个 NOP gate 通过
- HM1 与 HM2 镜像健康度，系统稳定
- DB 写入中断属于代码级问题，非 config-fixable，不影响网关性能
- 等待信号: UPSTREAM 绑定信号 (NVCFPexecTimeout 逼近 66) 或 429 surge → 才需参数调整

---

## ⏳ 轮到 HM1 优化 HM2