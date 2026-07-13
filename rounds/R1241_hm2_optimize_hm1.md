# HM2 Optimize HM1 — Round R1241 (NOP)

## 0. 触发判定
- 预运行脚本: `"这是我提交的, 不触发"` — HM1 commit `e80c0e4` (R1240) author=`opc2_uname` (HM2, 自提交)
- 触发类型: **FALSE TRIGGER** (double-dispatch, R1240 已处理)
- 判定: cron 误派遣辅以 HM1 commit 声明不触发

## 1. 数据收集 (改前必有数据)
HM1 数据采集时间: 2026-07-13 20:41 UTC

### 1.1 容器状态
- `nv_gw`: Up 2 hours (healthy), 重启于 2026-07-13T10:44:55Z
- `compose md5`: 832ef9ff2d975396154a2880a8938908 (与 R1240 相同, 无变更)

### 1.2 6h 请求概览
| 指标 | 值 |
|------|-----|
| 总请求 | 133 |
| 成功 (200) | 104 |
| 失败 (≠200) | 29 |
| 成功率 | 78.2% |

vs R1240: 112/86/26 (76.8%) → 133/104/29 (78.2%) — 轻微改善 (post-restart 效应)

### 1.3 按模型分布
| 模型 | 请求 | 成功 | 失败 | 成功率 | 平均TTFB | 平均延迟 |
|------|------|------|------|--------|----------|----------|
| glm5_2_nv | 125 | 101 | 24 | 80.8% | 31629ms | 42225ms |
| dsv4p_nv | 8 | 3 | 5 | 37.5% | 10108ms | 55866ms |

### 1.4 按上游类型
| 上游 | 请求 | 成功 | 失败 | 平均TTFB | 平均延迟 |
|------|------|------|------|----------|----------|
| nv_integrate | 107 | 93 | 14 | 28677ms | 30446ms |
| (空/ATE) | 14 | 0 | 14 | 801ms | 108693ms |
| nvcf_pexec | 12 | 11 | 1 | 78794ms | 78796ms |

### 1.5 错误类型分布
| 错误类型 | 数量 | 可配置修复? |
|----------|------|------------|
| all_tiers_exhausted | 14 | ❌ 11 pre-restart + 3 NEW 404-DEGRADED |
| zombie_empty_completion | 14 | ❌ NVCF content-filter, 代码级检测已部署 |
| NVStream_IncompleteRead | 1 | ❌ 网络瞬态 |

### 1.6 ATE 详细分解
| 时间段 | 模型 | 数量 | 特征 | 根因 |
|--------|------|------|------|------|
| 08:17-09:10 UTC | dsv4p_nv | 5 | duration 25269-142677ms, tiers_tried=1 | NVCF pexec 瞬态中断 (pre-restart) |
| 08:33-09:00 UTC | glm5_2_nv | 6 | duration 186862-188328ms, tiers_tried=1 | IntegrateTimeout 集群 (pre-restart) |
| 12:33-12:39 UTC | glm5_2_nv | 3 | **duration 3845-7524ms, tiers_tried=1** | **NEW: NVCF 404 "Inference error"** |
| 20:37-20:39 UTC | glm5_2_nv | 0→1 escaped | integrate 404 → pexec k3 success | 部分恢复, 部分 key 仍 404 |

### 1.7 NEW FAILURE: 404 "Inference error" (post-restart)
```
12:33:21 integrate k4 → 404 body={"error":""} → INTEGRATE-FALLBACK → pexec k4 → 404 "Inference error" → ATE 7524ms
12:37:55 integrate k4 → 404 → INTEGRATE-FALLBACK → pexec k2 → 404 → ATE 3845ms
12:39:23 integrate k3 → 404 → INTEGRATE-FALLBACK → pexec k4 → 404 → ATE 4977ms
20:37:18 integrate k1 → 404 → INTEGRATE-FALLBACK → pexec k5 → 404 → ATE → ms_gw 193899ms TimeoutError
20:38:19 integrate k5 → 404 → INTEGRATE-FALLBACK → pexec k3 → SUCCESS (escaped!)
20:39:26 integrate k3 → 404 → INTEGRATE-FALLBACK → pexec k4 → 404 → ATE → ms_gw 190186ms TimeoutError
```

**特征**: NVCF glm5_2 function `3b9748d8` 返回 `404 "Inference error"` / `"Not Found"` — function-level DEGRADED。网关正确检测 NONCYCLE (404 不循环 key), 但 integrate→pexec fallback 也命中 404, 最终 ms_gw fallback 超时 190s。

**可配置修复?**: ❌ NVCF function-level 404 — 非配置可调。网关行为正确 (NONCYCLE=不循环 key, 节省 ~21s per key)。ms_gw TimeoutError 是因为 glm5_2_ms 处理大请求超时 (NVU_MS_GW_FALLBACK_TIMEOUT=180)，降低超时只会更快返回 502, 不会增加成功率。

### 1.8 僵尸模式 (NVCF content-filter)
- 14 zombie_empty_completion: glm5_2_nv integrate, total_input_chars 109K-130K, duration 3972-109395ms
- 网关检测 zombie → 发送 error chunk → openclaw fallback — 正确
- ❌ NVCF content-filter 行为, 非配置可修复

### 1.9 Fallback 状态
- fallback_occurred: 0/133 (无 fallback 触发)
- ms_gw: 0/21 OK in DB (BrokenPipeError/TimeoutError 代码级缺陷)
- ms_gw 日志显示 MS-OK-STREAM 成功流 (glm5_2_ms, 3-4s), 但不写 DB — 已知 ms_requests 表不记录

### 1.10 Tier Attempts
- glm5_2_nv: 6× IntegrateTimeout (avg 91331ms, max 93529ms) — pre-restart 集群
- 0 其他 tier_attempts (post-restart 区间无 IntegrateTimeout)

### 1.11 最近日志 (20:37-20:44 UTC)
- 正常流量: glm5_2_nv integrate, k1-k5 轮转, 首次尝试 2-5s 成功
- 1× SSLEOFError → SSL-CYCLE → k3 成功 (5002ms, 自动恢复)
- 2× 404 NONCYCLE → INTEGRATE-FALLBACK → pexec 404 → ATE → ms_gw 190s TimeoutError
- 1× 404 NONCYCLE → INTEGRATE-FALLBACK → pexec k3 → SUCCESS (escaped, 部分 key 恢复)
- 0 zombie, 0 429 — post-restart 干净

### 1.12 当前参数 (全部 floor/optimal)
| 参数 | 值 | 状态 |
|------|-----|------|
| TIER_TIMEOUT_BUDGET_S | 210 | optimal (R1231) |
| UPSTREAM_TIMEOUT | 66 | optimal |
| TIER_COOLDOWN_S | 15 | optimal |
| KEY_COOLDOWN_S | 25 | optimal |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | optimal |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | optimal |
| NVU_TIER_BUDGET_DSV4P_NV | 72 | optimal |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | optimal |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | optimal |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | optimal |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | optimal |
| NVU_EMPTY_200_FASTBREAK | 2 | optimal |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | optimal |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| NVU_MS_GW_FALLBACK_TIMEOUT | 180 | optimal (降低只会更快返回502) |

## 2. 决策
**NOP** — 所有参数 floor/optimal, 无调整空间。

### 失败分析:
- **11 pre-restart ATE**: 5 dsv4p_nv (NVCF pexec 瞬态中断) + 6 glm5_2_nv IntegrateTimeout (集群) — 已自然恢复, 重启后 0 ATE of these types
- **3 NEW 404 ATE (12:33-12:39)**: NVCF glm5_2 function `3b9748d8` 返回 404 "Inference error" — function-level DEGRADED, 非配置可调。网关 NONCYCLE 行为正确 (不循环 key 节省预算)。function 部分恢复 (20:38 pexec k3 成功)
- **2 ms_gw TimeoutError (20:37-20:41)**: 404→ms_gw 级联, glm5_2_ms 大请求超时 190s。NVU_MS_GW_FALLBACK_TIMEOUT=180 合理, 降低只会更快返回 502
- **14 zombie_empty_completion**: NVCF content-filter, 代码级检测正确, 非配置可调
- **1 NVStream_IncompleteRead**: 网络瞬态

### 数据对比 R1240→R1241:
| 指标 | R1240 (6h) | R1241 (6h) | 变化 |
|------|-----------|-----------|------|
| 总请求 | 112 | 133 | +21 |
| 成功 | 86 | 104 | +18 |
| 失败 | 26 | 29 | +3 (404 DEGRADED) |
| 成功率 | 76.8% | 78.2% | +1.4pp |
| zombie | 14 | 14 | 0 |
| ATE | 11 | 14 | +3 (NEW 404) |
| IntegrateTimeout ATE | 11 | 6 | -5 (pre-restart cleared) |
| 404 ATE | 0 | 3 | NEW (NVCF function DEGRADED) |

Post-restart (10:44→now): 14 zombie + 3 404 ATE + 0 IntegrateTimeout + 0 dsv4p_nv ATE。重启清除了 IntegrateTimeout/dsv4p_nv ATE, 404 是新的 NVCF function-level 问题。

## 3. 执行
- 参数变更: 0
- 容器重启: 0
- compose 修改: 0
- 铁律: 只改HM1不改HM2 ✅

## ⏳ 轮到HM1优化HM2
