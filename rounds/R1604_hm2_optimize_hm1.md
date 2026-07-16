# HM2 Optimize HM1 — Round R1604

## 决策: NOP (所有失败 zombie + 504 streaming sync defect, 参数全 floor/optimal, ms_gw 100% SR)

## 1. 改前数据 (2026-07-16 10:05 CST)

### 容器状态
- nv_gw: Up 2 hours (healthy)
- compose md5: 64e8fc1a (与 R1534 一致, 无变化)

### 关键参数 (全 floor/optimal)
| 参数 | 值 | 评价 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | floor |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | floor (UPSTREAM) |
| NVU_TIER_BUDGET_GLM5_2_NV | 120 | optimal |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | optimal |
| TIER_TIMEOUT_BUDGET_S | 205 | optimal |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | optimal |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| TIER_COOLDOWN_S | 15 | floor |
| KEY_COOLDOWN_S | 25 | optimal |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | optimal |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | optimal |
| NVU_PEER_FB_SKIP_MODELS | (空) | optimal (peer-fb 全开) |

### 6h 总体统计
| total | ok | fail | SR |
|-------|-----|------|-----|
| 67 | 47 | 20 | 70.1% |

### 按模型
| 模型 | total | ok | fail | SR | avg_dur |
|------|-------|-----|------|-----|---------|
| glm5_2_nv | 36 | 26 | 10 | 72.2% | 13256ms |
| dsv4p_nv | 31 | 21 | 10 | 67.7% | 11734ms |

### 错误分类 (20 失败)
| 错误类型 | 数量 | 占比 |
|---------|------|------|
| zombie_empty_completion | 17 | 85% |
| all_tiers_exhausted | 3 | 15% |

### Zombie 详情 (17 条)
| 模型 | 数量 | avg_ichars | avg_dur |
|------|------|-----------|---------|
| dsv4p_nv | 8 | 223,748 | 9,126ms |
| glm5_2_nv | 9 | 223,099 | 5,365ms |

全部 ~223K input chars, output 2-48 chars. NVCF content-filter → 代码级 zombie 检测 (R1107), 不可配置修复.

### ATE 详情 (3 条)
| 模型 | 数量 | avg_dur |
|------|------|---------|
| dsv4p_nv | 2 | 35,119ms |
| glm5_2_nv | 1 | 8,411ms |

Log 证据: dsv4p_nv ATE = 504 gateway timeout → k5 504 → all 5 keys failed → ms_gw relay TimeoutError 132,529ms (relay_started=True). ms_gw streaming sync defect (R832/R1103), 代码级, 不可配置修复.

### ms_gw 信号
13/13 **100% SR** (ms_gw 健康, 可靠回退)

### tier_attempts (6h)
| tier | error_type | cnt | avg_ms | max_ms |
|------|-----------|-----|--------|--------|
| glm5_2_nv | pexec_success | 19 | 14,873 | 51,657 |
| glm5_2_nv | pexec_NameError | 1 | 3,310 | 3,310 |
| glm5_2_nv | pexec_empty_200 | 1 | — | — |

### 按 upstream 路径
| 路径 | total | ok | fail | avg_ttfb | avg_dur |
|------|-------|-----|------|---------|---------|
| nvcf_pexec | 47 | 36 | 11 | 13,518 | 13,546 |
| nv_integrate | 16 | 10 | 6 | 7,124 | 7,647 |
| (NULL/ATE) | 4 | 1 | 3 | 1,181 | 20,491 |

### 每小时 SR
| 小时 | total | ok | fail | SR |
|------|-------|-----|------|-----|
| 20:00 | 4 | 2 | 2 | 50.0% |
| 21:00 | 21 | 17 | 4 | 81.0% |
| 22:00 | 4 | 2 | 2 | 50.0% |
| 23:00 | 8 | 4 | 4 | 50.0% |
| 00:00 | 19 | 17 | 2 | 89.5% |
| 01:00 | 8 | 4 | 4 | 50.0% |
| 02:00 | 3 | 1 | 2 | 33.3% |

### 最近 2h (post-restart 窗口)
| total | ok | fail | SR |
|-------|-----|------|-----|
| 25 | 19 | 6 | 76.0% |

## 2. 分析

### 失败根因
1. **zombie_empty_completion (85%)**: NVCF content-filter — 输入 ~223K chars, 输出 2-48 chars, finish_reason=stop. 代码级 zombie 检测功能 (R1107), 快速 abort (3-15s) 替代旧 96s hang. 不可配置修复. 正效应: 更快的失败回退循环.
2. **all_tiers_exhausted (15%)**: dsv4p_nv 504 gateway timeout → 5 keys 全失败 → ms_gw relay TimeoutError 132s (relay_started=True). ms_gw streaming sync defect (R832/R1103) — ms_gw 已完成处理但 nv_gw 看不到完成信号. 代码级缺陷, 不可配置修复.

### 参数状态
所有参数已处于 floor/optimal:
- UPSTREAM=66 (floor, BUDGET=UPSTREAM pattern R1440)
- BUDGET_DSV4P=66 (BUDGET Floor Pattern, 504-dominated)
- FASTBREAK 全 1 (PEXEC/INTEGRATE function-level)
- TIER_COOLDOWN=15 (floor)
- MS_GW_FALLBACK_TIMEOUT=120 (generous, 不会被 BUDGET=205 截断: 205-66=139 > 120)
- PEER_FB_SKIP_MODELS=空 (peer-fb 全开, R1039 workaround)

### 为什么不是可修复的
- Zombie: NVCF 上游 content-filter — 网关法正确检测并快速 abort. 无参数能阻止 NVCF 返回空内容.
- 504 ATE: 函数级 NVCF 降级 — 所有 5 个 key 都返回 504, FASTBREAK 不适用 (504 走 NV-CYCLE 非 FASTBREAK). BUDGET=66 已是最紧 floor (UPSTREAM_TIMEOUT). 降低 BUDGET 会在大请求时过早截断成功请求.
- ms_gw relay TimeoutError: streaming sync defect — nv_gw 与 ms_gw 之间的流同步问题, 非配置参数可修复.

## 3. 决策: NOP

零配置修改. 所有参数 floor/optimal, 所有失败根因不可配置修复. ms_gw 100% SR 为可靠回退.

## 4. 铁律确认
- 改前必有数据: §1 (DB + logs + env) ✓
- 改后必有验证: NOP, 无需验证 ✓
- 聚焦 nv_gw: 仅分析 nv_gw 链路 ✓
- 所有修改写入仓库: 本轮文件 commit + push ✓
- 铁律: 只改HM1不改HM2 (本轮无改动) ✓

## ⏳ 轮到HM1优化HM2
