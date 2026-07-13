# HM2 Optimize HM1 — Round R1239

## 1. 触发判定
- cron 脚本输出: `[2026-07-13 20:15:06] 这是我提交的, 不触发`
- 最新 commit = `503835f R1238: HM2→HM1 — NOP (false trigger, double-dispatch)`
- 判定: **FALSE TRIGGER — 双派遣 (double-dispatch)**
- R1238 已处理过此 commit，数据与 R1238 完全一致

## 2. 数据收集 (改前必有数据)

### 2.1 6h 总体
| 指标 | 值 |
|------|-----|
| 总请求 | 112 |
| 成功 (200) | 86 |
| 失败 | 26 |
| SR | 76.8% |
| 容器重启时间 | 2026-07-13T10:44:55 UTC |

### 2.2 按模型
| 模型 | 请求 | 成功 | 失败 | SR |
|------|------|------|------|-----|
| glm5_2_nv | 104 | 83 | 21 | 79.8% |
| dsv4p_nv | 8 | 3 | 5 | 37.5% |

### 2.3 错误分类
| 错误类型 | 数量 | 可修复? |
|----------|------|---------|
| zombie_empty_completion | 14 | ❌ 代码级 (NVCF content-filter stop+12chars, R1107 快速终止) |
| all_tiers_exhausted | 11 | ❌ NVCF 上游 (5 dsv4p_nv pexec transient + 6 glm5_2_nv IntegrateTimeout) |
| NVStream_IncompleteRead | 1 | ❌ 网络瞬态 |

### 2.4 按 upstream 路径
| 路径 | 请求 | 成功 | 失败 | avg_ttfb | avg_dur |
|------|------|------|------|----------|---------|
| nv_integrate | 92 | 78 | 14 | 31880ms | 33212ms |
| nvcf_pexec | 9 | 8 | 1 | 99081ms | 99082ms |
| NULL (ATE) | 11 | 0 | 11 | 811ms | 136850ms |

### 2.5 nv_tier_attempts (6h)
| 模型 | 错误类型 | 数量 | avg | max |
|------|----------|------|-----|-----|
| glm5_2_nv | IntegrateTimeout | 6 | 91331ms | 93529ms |

### 2.6 ms_gw
| 总请求 | 成功 |
|--------|------|
| 16 | 0 |

ms_gw 0/16 OK — BrokenPipeError 代码级缺陷 (MS-OK-STREAM 后 MS-STREAM-CLIENT-EOF)，非配置可修复。

### 2.7 容器日志 (最近 100 行)
- `NV-INTEGRATE-SUCCESS` — glm5_2_nv 全部 k1-k5 一轮成功
- `NV-ZOMBIE-EMPTY` — 3 次 zombie 检测 (content_chars=12, input_chars=115K-124K)
- 零 error/warn/timeout/cooldown 异常

### 2.8 当前参数状态 (全部 floor/optimal)
```
UPSTREAM_TIMEOUT=66          TIER_TIMEOUT_BUDGET_S=210
MIN_OUTBOUND_INTERVAL_S=0    KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=15           NVU_CONNECT_RESERVE_S=0
NVU_PEXEC_TIMEOUT_FASTBREAK=1   NVU_EMPTY_200_FASTBREAK=2
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_PEER_FALLBACK_TIMEOUT=66    NVU_MS_GW_FALLBACK_TIMEOUT=180
NVU_TIER_BUDGET_DSV4P_NV=72    NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_FALLBACK_HEALTH_THRESHOLD=0.05  KEY_AUTHFAIL_COOLDOWN_S=60
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
NV_INTEGRATE_MODELS=glm5_2_nv
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
```
compose md5: `832ef9ff2d975396154a2880a8938908`
nv_gw: Up 2 hours (healthy)

## 3. 决策: ⏸️ NOP

### 3.1 zombie_empty_completion (14 次)
- 全部 glm5_2_nv integrate 路径
- NVCF content-filter `stop` + 12 chars, input_chars 115K-124K
- 网关 zombie 检测 + FASTBREAK 快速终止 (3-27s)，非旧版 96s hang
- **代码级特性，非配置可修复** (R1107)

### 3.2 all_tiers_exhausted (11 次)
- 5 dsv4p_nv: NVCF pexec 瞬态，已自愈
- 6 glm5_2_nv: IntegrateTimeout cluster (91-93s)，NVCF integrate 内部排队超时
- **NVCF 上游问题，非配置可修复** (R717/R1010 模式)

### 3.3 ms_gw 0/16 OK
- BrokenPipeError 代码级缺陷 — ms_gw streaming relay 发送 200+headers 后中断
- **代码级缺陷，非配置可修复** (R1031)

### 3.4 全部参数在 floor/optimal
- 所有 FASTBREAK 在 floor (1/2/1)
- 所有 cooldown 在 optimal (KEY_COOLDOWN=25, TIER_COOLDOWN=15)
- 所有 budget 有充足余量 (BUDGET=210, 各 tier_budget=72/96/100)
- compose md5 未变，无漂移

## 4. 与 R1238 对比
| 指标 | R1238 | R1239 | 变化 |
|------|-------|-------|------|
| 总请求 | 112 | 112 | 0 |
| 成功 | 86 | 86 | 0 |
| 失败 | 26 | 26 | 0 |
| SR | 76.8% | 76.8% | 0 |
| zombie_empty | 14 | 14 | 0 |
| all_tiers_exhausted | 11 | 11 | 0 |
| NVStream_Incomplete | 1 | 1 | 0 |
| ms_gw OK | 0/16 | 0/16 | 0 |

**数据完全一致** — 确认双派遣。无新请求、无新错误、无配置漂移。

## 5. 总结
- **0 参数变更** — 全部在 floor/optimal
- **0 compose 变更** — md5 未变
- **0 容器重启** — 无配置变化
- 铁律: 只改 HM1 不改 HM2
- 所有错误 = 代码级缺陷 (zombie 检测 + ms_gw streaming) + NVCF 上游 (IntegrateTimeout + pexec transient)，非配置可修复
## ⏳ 轮到HM1优化HM2
