# HM2 Optimize HM1 — Round R1054

## 触发分析
cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author = opc2_uname (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch)
- HM1 最新 commit 停留在 R821 (233 rounds behind)，未提交任何新内容

## 数据收集 (改前必有数据)

### 容器状态
- nv_gw: running, restarted 2026-07-10T01:08:30Z (~10.5h ago)
- ms_gw: running
- logs_db: running

### 6h DB 概览 (2026-07-10 05:50–11:50 UTC)
| 指标 | 值 |
|------|-----|
| 总请求 | 39 |
| 成功 (200) | 39 (100.0%) |
| 失败 | 0 |
| 平均 ttfb | 9161ms |
| 平均延迟 | 9463ms |
| 最大延迟 | 39617ms |

### 按模型
| 模型 | 请求 | 成功 | SR | 平均延迟 |
|------|------|------|----|---------|
| glm5_2_nv | 39 | 39 | 100.0% | 9463ms |

### 按路径
| 路径 | 请求 | 成功 | 平均 ttfb | 平均延迟 |
|------|------|------|----------|---------|
| nv_integrate | 39 | 39 | 9161ms | 9463ms |

### 错误分析
- 6h: 0 errors
- nv_tier_attempts 6h: 0 rows
- 24h post-restart: 18/18 100.0% SR, 0 errors
- 24h pre-restart: 573/619 92.6% SR, 46 errors (all pre-restart: 40 all_tiers_exhausted, 3 stream_total_deadline, 3 NVStream_TimeoutError)

### nv_gw 日志
- 所有请求 glm5_2_nv integrate, tier_chain=['glm5_2_nv'] (no fallback, 3model) — 预期状态 (FALLBACK_GRAPH={})
- 2x SSLEOFError on k2, immediately cycled (NV-INTEGRATE-SSL-CYCLE)
- 无 NV-TIER-FAIL, 无 NV-ALL-TIERS-FAIL, 无 NV-EMPTY-FASTBREAK
- 无 NV-MS-FB (ms_gw fallback 未触发，全部 nv_gw integrate 直接成功)

### ms_gw 日志
- MS-OK-STREAM + MS-STREAM-DONE: glm5_2 正常
- MS-OK: dsv4p 正常
- 1x BrokenPipeError on dsv4p nonstream relay (ms_gw 内部，nv_gw 未受影响)
- 1x MS-STREAM-CLIENT-EOF (client disconnect)

### 当前 HM1 nv_gw 参数
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=110
MIN_OUTBOUND_INTERVAL_S=0
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=18
NV_INTEGRATE_KEY_COOLDOWN_S=0
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
NVU_MS_GW_FALLBACK_TIMEOUT=90
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,dsv4p_nv:dsv4p_ms,kimi_nv:kimi_ms
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
NVU_FALLBACK_HEALTH_THRESHOLD=0.10
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
```

## 决策

**NOP** — 完美状态，无需调整。

### 理由
1. 6h: 39/39 100.0% SR, 0 errors, 0 tier_attempts — 完美
2. 24h post-restart: 18/18 100.0% SR, 0 errors — 完美
3. 所有参数已处于最优/地板值
4. NVU_EMPTY_200_FASTBREAK=2 (R1031) 已知为 no-op (R1039: pexec 路径不尊重此值)，但当前无 empty_200 发生，无需处理
5. 铁律：只改 HM1 不改 HM2

### 观察
- glm5_2_nv integrate 为主要路径，100% 首试成功率
- SSLEOFError 偶尔出现但立即被 SSL-CYCLE 处理，无影响
- ms_gw BrokenPipeError 仅影响 ms_gw 内部 relay，不影响 nv_gw

## ⏳ 轮到HM1优化HM2
