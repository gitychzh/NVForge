# HM2 Optimize HM1 — Round R1237 (NOP)

## 1. 触发判定
- cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author: `opc2_uname` (HM2，自提交)
- 触发类型: **FALSE TRIGGER** (double-dispatch，R1236 已处理)
- 判定: 预运行脚本已正确检测到自提交并标记 "不触发"，cron 仍被派遣 — 误触发

## 2. 数据收集 (改前必有数据)
HM1 数据采集时间: 2026-07-13 ~19:50 UTC

### 2.1 容器状态
- `nv_gw`: Up About an hour (healthy)，重启于 2026-07-13T10:44:55Z
- `compose md5`: 832ef9ff2d975396154a2880a8938908

### 2.2 6h 请求概览
| 指标 | 值 |
|------|-----|
| 总请求 | 108 |
| 成功 (200) | 83 |
| 失败 (≠200) | 25 |
| 成功率 | 76.9% |

### 2.3 按模型分布
| 模型 | 请求 | 成功 | 失败 | 成功率 | 平均延迟 |
|------|------|------|------|--------|----------|
| glm5_2_nv | 100 | 80 | 20 | 80.0% | 48833ms |
| dsv4p_nv | 8 | 3 | 5 | 37.5% | 55866ms |

### 2.4 错误类型分布
| 错误类型 | 数量 | 可配置修复? |
|----------|------|------------|
| zombie_empty_completion | 13 | ❌ NVCF content-filter，代码级检测已部署 |
| all_tiers_exhausted | 11 | ❌ 5 dsv4p_nv (08:00-09:10 UTC NVCF pexec 瞬态中断) + 6 glm5_2_nv IntegrateTimeout (08:33-09:00 集群) |
| NVStream_IncompleteRead | 1 | ❌ 网络瞬态 |

### 2.5 按上游类型
| 上游 | 请求 | 成功 | 失败 | 平均TTFB | 平均延迟 |
|------|------|------|------|----------|----------|
| nv_integrate | 88 | 75 | 13 | 31938ms | 33331ms |
| (空/ATE) | 11 | 0 | 11 | 811ms | 136850ms |
| nvcf_pexec | 9 | 8 | 1 | 99081ms | 99082ms |

### 2.6 Fallback 状态
- fallback_occurred: 0/108 (无 fallback 触发)
- ms_gw: 0/16 OK (BrokenPipeError 代码级缺陷)

### 2.7 Tier Attempts
- glm5_2_nv: 6× IntegrateTimeout (avg 91331ms, max 93529ms) — 08:33-09:00 集群瞬态

### 2.8 最近日志
- 最近 2h 只有 glm5_2_nv integrate 请求
- 2× zombie_empty_completion (11:03, 11:34 UTC), 其余正常
- 无 MS-FB, 无 tierfail, 无 empty fastbreak

### 2.9 当前参数 (全部 floor/optimal)
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

## 3. 决策
**NOP** — 所有参数 floor/optimal，无调整空间。

失败分析:
- **13 zombie_empty_completion**: NVCF content-filter 返回 stop+12chars，代码级 zombie 检测已部署，返回 502 在 3-15s vs 旧 96s 超时 — 代码级修复，非配置可调
- **11 all_tiers_exhausted**: 5 dsv4p_nv (NVCF pexec 08:00-09:10 UTC 瞬态中断) + 6 glm5_2_nv IntegrateTimeout (08:33-09:00 集群) — 时间窗口集中的瞬态故障，已自然恢复。最近 2h 无 ATE
- **1 NVStream_IncompleteRead**: 网络瞬态
- **ms_gw 0/16 OK**: BrokenPipeError 代码级缺陷，非配置可调

数据与 R1236 实质相同（108/83/25），无新信号。

## 4. 执行
- 参数变更: 0
- 容器重启: 0
- compose 修改: 0
- 铁律: 只改HM1不改HM2 ✅

## ⏳ 轮到HM1优化HM2
