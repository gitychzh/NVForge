# HM2 Optimize HM1 — Round R1242 (NOP)

## 0. 触发判定
- 预运行脚本: `"这是我提交的, 不触发"` — HM2 自提交
- 触发类型: **FALSE TRIGGER** (double-dispatch, R1241 已处理)
- 判定: cron 误派遣, pre-run 已写 R1241, symlink 正确 → 本轮需创建 R1242

## 1. 数据收集 (改前必有数据)
HM1 数据采集时间: 2026-07-13 20:55 UTC

### 1.1 容器状态
- `nv_gw`: Up 2 hours (healthy), 重启于 2026-07-13T10:44:55Z
- `compose md5`: 832ef9ff2d975396154a2880a8938908 (与 R1240-R1241 相同, 无变更)
- 所有 9 容器 healthy

### 1.2 6h 请求概览
| 指标 | R1241 | R1242 | 变化 |
|------|-------|-------|------|
| 总请求 | 133 | 138 | +5 |
| 成功 (200) | 104 | 107 | +3 |
| 失败 (≠200) | 29 | 31 | +2 |
| 成功率 | 78.2% | 77.5% | -0.7pp |

### 1.3 按模型分布
| 模型 | 请求 | 成功 | 失败 | 成功率 | 平均延迟(OK) |
|------|------|------|------|--------|-------------|
| glm5_2_nv | 130 | 104 | 26 | 80.0% | 36354ms |
| dsv4p_nv | 8 | 3 | 5 | 37.5% | 22428ms |

### 1.4 按上游类型
| 上游 | 请求 | 成功 | 失败 |
|------|------|------|------|
| nv_integrate | 112 | 96 | 16 |
| (空/ATE) | 14 | 0 | 14 |
| nvcf_pexec | 12 | 11 | 1 |

### 1.5 错误类型分布
| 错误类型 | 数量 | 可配置修复? |
|----------|------|------------|
| zombie_empty_completion | 16 | ❌ NVCF content-filter, 代码级检测已部署 |
| all_tiers_exhausted | 14 | ❌ 11 pre-restart + 3 NEW 404 NVCF function DEGRADED |
| NVStream_IncompleteRead | 1 | ❌ 网络瞬态 |

### 1.6 ATE 详细分解
| 模型 | 数量 | avg_dur | min_dur | max_dur | 根因 |
|------|------|---------|---------|---------|------|
| glm5_2_nv | 9 | 126894ms | 3845ms | 188328ms | 6× IntegrateTimeout (pre-restart) + 3× 404 DEGRADED |
| dsv4p_nv | 5 | 75929ms | 25269ms | 142677ms | NVCF pexec 瞬态中断 (pre-restart) |

### 1.7 404 DEGRADED 详情 (NEW, post-restart)
- NVCF glm5_2 function `3b9748d8` 返回 `404 "Inference error"` / `"Not Found"`
- 3× ATE: integrate k3/k4 404 → INTEGRATE-FALLBACK → pexec k2/k4 404 → ATE (3845-7524ms)
- 1× escaped: integrate k5 404 → INTEGRATE-FALLBACK → pexec k3 SUCCESS (20:38:19)
- ❌ NVCF function-level 404 — 非配置可调。网关 NONCYCLE 行为正确

### 1.8 僵尸模式 (NVCF content-filter)
- 16 zombie_empty_completion: glm5_2_nv integrate, duration 7410-109395ms
- 网关检测 zombie → 发送 error chunk → openclaw fallback — 正确
- ❌ NVCF content-filter 行为, 非配置可修复

### 1.9 Fallback 状态
- fallback_occurred: 0/138 (无 fallback 触发)
- ms_gw: 0/21 OK (BrokenPipeError/TimeoutError 代码级缺陷)
- ms_gw 日志显示 MS-OK-STREAM 成功流, 但不写 DB — 已知 ms_requests 表不记录

### 1.10 Tier Attempts
- glm5_2_nv: 6× IntegrateTimeout (avg 91331ms, max 93529ms) — pre-restart 集群
- 0 其他 tier_attempts (post-restart 区间无 IntegrateTimeout)

### 1.11 最近日志 (20:38-20:45 UTC)
- 正常流量: glm5_2_nv integrate, 首次尝试 2-7s 成功, 大部分 NV-INTEGRATE-SUCCESS
- 1× SSLEOFError → SSL-CYCLE → k3 成功 (5002ms, 自动恢复)
- 1× 404 NONCYCLE → INTEGRATE-FALLBACK → pexec 404 → ATE → ms_gw 187908ms TimeoutError
- 1× ZOMBIE-EMPTY: content_chars=34 < 50, input_chars=162054 (NVCF content-filter stop, 正确检测)
- 0 429, 0 IntegrateTimeout — post-restart 干净

### 1.12 当前参数 (全部 floor/optimal)
| 参数 | 值 | 状态 |
|------|-----|------|
| TIER_TIMEOUT_BUDGET_S | 210 | optimal |
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
| NVU_MS_GW_FALLBACK_TIMEOUT | 180 | optimal |

## 2. 决策
**NOP** — 所有参数 floor/optimal, 无调整空间。

### 失败分析:
- **11 pre-restart ATE** (5 dsv4p_nv + 6 glm5_2_nv IntegrateTimeout): 已自然恢复, 重启后 0 ATE of these types
- **3 NEW 404 ATE**: NVCF glm5_2 function `3b9748d8` 返回 404 "Inference error" — function-level DEGRADED, 非配置可调。部分 key 恢复 (pexec k3 成功)
- **2 ms_gw TimeoutError (187-190s)**: 404→ms_gw 级联, 降低 TIMEOUT 只会更快返回 502, 不会增加成功率
- **16 zombie_empty_completion**: NVCF content-filter, 代码级检测正确, 非配置可调
- **1 NVStream_IncompleteRead**: 网络瞬态

### 数据对比 R1241→R1242:
| 指标 | R1241 (6h) | R1242 (6h) | 变化 |
|------|-----------|-----------|------|
| 总请求 | 133 | 138 | +5 |
| 成功 | 104 | 107 | +3 |
| 失败 | 29 | 31 | +2 |
| ���功率 | 78.2% | 77.5% | -0.7pp |
| zombie | 14 | 16 | +2 |
| ATE | 14 | 14 | 0 |
| IntegrateTimeout | 6 | 6 | 0 (pre-restart) |

数据稳定, 无新异常模式。所有失败均为 NVCF-level (content-filter / 404 DEGRADED / pexec transient) 或 pre-restart 残留, 非网关配置可调。

## 3. 执行
- 参数变更: 0
- 容器重启: 0
- compose 修改: 0
- R1241 trailing newline 修复: `printf '\n'` 追加 (R1148/R1149 陷阱)
- 铁律: 只改HM1不改HM2 ✅

## ⏳ 轮到HM1优化HM2
