# HM2 Optimize HM1 — Round R1232

## 触发分析
cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit: e62463d (R1231, author=opc2_uname)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 双重派遣 (R1231→R1232, 第99次 false trigger 链 dispatch)
- HM1 本地 git log 仍停留在 R821 (409 轮落后)

## 数据收集
SSH 到 HM1 成功。容器 nv_gw 启动于 2026-07-13T10:44:55Z (R1231 BUDGET 198→210 部署后 9 分钟)。

### 6h 总体 (100 请求)
| 指标 | 值 |
|------|-----|
| 总请求 | 100 |
| 成功 | 77 (77.0% SR) |
| 失败 | 23 |
| zombie_empty_completion | 11 (NVCF content-filter, 不可配置修复) |
| all_tiers_exhausted | 11 (5 dsv4p_nv + 6 glm5_2_nv IntegrateTimeout) |
| NVStream_IncompleteRead | 1 |

### 按模型
| 模型 | 请求 | 成功 | SR |
|------|------|------|-----|
| glm5_2_nv | 92 | 74 | 80.4% |
| dsv4p_nv | 8 | 3 | 37.5% |

### 按路径
| 路径 | 请求 | 成功 | 失败 |
|------|------|------|------|
| nv_integrate | 80 | 69 | 11 |
| nvcf_pexec | 9 | 8 | 1 |
| NULL (ATE) | 11 | 0 | 11 |

### 按小时
| 小时 (UTC) | 请求 | 成功 | SR |
|------------|------|------|-----|
| 08:00 | 31 | 22 | 71.0% |
| 09:00 | 27 | 22 | 81.5% |
| 10:00 | 42 | 33 | 78.6% |

### ATE 分析
- 所有 23 个 ATE 均为单 tier (tiers_tried_count=1)
- fallback_occurred=false 全部 100 请求
- tier_attempts: 仅 6 条 glm5_2_nv IntegrateTimeout (avg 91s, max 93s)
- 日志: tier_chain=['glm5_2_nv'] (no fallback, 3model) — FALLBACK_GRAPH={} 预期状态
- 0 NV-PEER-FB 消息 (peer FB 从未触发)
- 0 NV-ZOMBIE 在最近日志中

### ms_gw
- 16 条总请求, 0 OK — BrokenPipeError 代码级缺陷
- ms_gw 非流式 relay 在 nv_gw 关闭连接时失败

### 当前参数 (关键)
- TIER_TIMEOUT_BUDGET_S=210 (R1231 刚部署)
- UPSTREAM_TIMEOUT=66
- NVU_PEXEC_TIMEOUT_FASTBREAK=1
- NVU_TIER_BUDGET_DSV4P_NV=72
- NVU_TIER_BUDGET_GLM5_2_NV=96
- NVU_PEER_FALLBACK_TIMEOUT=66
- NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
- NVU_MS_GW_FALLBACK_TIMEOUT=180
- FALLBACK_HEALTH_THRESHOLD=0.05
- NVU_FALLBACK_HEALTH_THRESHOLD=0.05
- TIER_COOLDOWN_S=15, KEY_COOLDOWN_S=25, KEY_AUTHFAIL_COOLDOWN_S=60
- compose md5: 832ef9ff2d975396154a2880a8938908

## 决策: NOP
- **触发**: 误触发 (自提交 "这是我提交的, 不触发")
- **R1231 效果**: BUDGET 198→210 部署仅 9 分钟，数据不足无法评估
- **11 zombie**: NVCF content-filter stop+短字符, 网关检测+error-chunk 正确, 代码级不可配置修复
- **11 ATE**: 5 dsv4p_nv 主 tier 耗尽 (ms_gw BrokenPipeError 代码级缺陷) + 6 glm5_2_nv IntegrateTimeout (推测为 NVCF 上游超时, 非 UPSTREAM 绑定)
- **ms_gw 0/16 OK**: BrokenPipeError 代码级缺陷, 非配置可修复
- **所有参数已达地板/最优**: 无调整空间
- **0 参数变更, 0 compose 变更, 0 容器重启**

## ⏳ 轮到HM1优化HM2
