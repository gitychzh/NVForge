# HM2 Optimize HM1 — Round R1606

## 决策: NOP (同R1604-R1605: 所有失败 zombie+504, 参数全 floor/optimal, ms_gw 100% SR)

## 1. 改前数据 (2026-07-16 10:25 CST)

### 触发判定
脚本输出: `"这是我提交的, 不触发"` — R1605 由 HM2 提交, 无 HM1 新提交. Cron 误派遣.

### 容器状态
- nv_gw: Up 2 hours (healthy), restarted 2026-07-16 00:36 UTC
- compose md5: 64e8fc1a (与 R1604-R1605 一致, 无变化)
- ms_gw: Up 27 hours (healthy)
- logs_db: Up 27 hours (healthy)

### 关键参数 (全 floor/optimal)
| 参数 | 值 | 评价 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | floor |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | floor (BUDGET=UPSTREAM pattern R1440) |
| NVU_TIER_BUDGET_GLM5_2_NV | 120 | optimal |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | optimal |
| TIER_TIMEOUT_BUDGET_S | 205 | optimal |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | optimal |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| TIER_COOLDOWN_S | 15 | floor |
| KEY_COOLDOWN_S | 25 | optimal |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | optimal |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | optimal |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | optimal |
| NVU_PEER_FB_SKIP_MODELS | (空) | optimal (peer-fb 全开) |
| NVU_FORCE_STREAM_UPGRADE | 0 | floor (disabled) |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 | optimal |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | optimal |

### 6h 总体统计
| total | ok | fail | SR |
|-------|-----|------|-----|
| 67 | 47 | 20 | 70.1% |

(与 R1604-R1605 计数完全一致)

### 按模型
| 模型 | total | ok | fail | SR | avg_dur |
|------|-------|-----|------|-----|---------|
| glm5_2_nv | 36 | 26 | 10 | 72.2% | 13,256ms |
| dsv4p_nv | 31 | 21 | 10 | 67.7% | 11,734ms |

### 错误分类 (20 失败)
| 错误类型 | 数量 | 占比 |
|---------|------|------|
| zombie_empty_completion | 17 | 85% |
| all_tiers_exhausted | 3 | 15% |

### Zombie 详情 (17 条)
| 模型 | 数量 | avg_dur |
|------|------|---------|
| dsv4p_nv | 8 | 9,126ms |
| glm5_2_nv | 9 | 5,365ms |

全部 ~223K input_chars, output 2-48 chars. NVCF content-filter → 代码级 zombie 检测 (R1107), 快速 abort 3-15s, 不可配置修复.

### ATE 详情 (3 条)
| 模型 | 数量 | avg_dur |
|------|------|---------|
| dsv4p_nv | 2 | 35,119ms |
| glm5_2_nv | 1 | 8,411ms |

Log 证据: dsv4p_nv k5 → 504 gateway timeout → all 5 keys failed (other=1, 429=0, empty200=0, timeout=0) → NV-CYCLE → NV-ALL-TIERS-FAIL ABORT-NO-FALLBACK → NV-MS-FB ms_gw relay TimeoutError 132,529ms (relay_started=True). ms_gw streaming sync defect (R832/R1103), 代码级, 不可配置修复.

### ms_gw 信号
13/13 **100% SR** (ms_gw 健康, 可靠回退)

### tier_attempts (6h)
| tier | error_type | cnt | avg_ms | max_ms |
|------|-----------|-----|--------|--------|
| glm5_2_nv | pexec_success | 19 | 14,873 | 51,657 |
| glm5_2_nv | pexec_NameError | 1 | 3,310 | 3,310 |
| glm5_2_nv | pexec_empty_200 | 1 | — | — |

dsv4p_nv 无 tier_attempts 记录 (504 是 gateway-level, 不触发 per-function 记录).

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

### 最近 10 条请求
| ts | model | status | ttfb | dur | error | input_tok | output_tok |
|----|-------|--------|------|-----|-------|-----------|------------|
| 10:08 | dsv4p_nv | 502 | 520 | 63,895 | all_tiers_exhausted | 0 | 0 |
| 10:03 | glm5_2_nv | 502 | 6,723 | 6,725 | zombie | 56,553 | 12 |
| 10:03 | glm5_2_nv | 200 | 5,228 | 5,229 | — | 56,461 | 75 |
| 09:37 | dsv4p_nv | 502 | 33,518 | 33,519 | zombie | 0 | 0 |
| 09:36 | dsv4p_nv | 200 | 45,963 | 45,964 | — | 0 | 0 |
| 09:33 | glm5_2_nv | 502 | 5,206 | 5,207 | zombie | 56,550 | 6 |
| 09:33 | glm5_2_nv | 200 | 5,300 | 5,301 | — | 56,461 | 72 |
| 09:06 | dsv4p_nv | 502 | 4,888 | 4,888 | zombie | 0 | 0 |
| 09:06 | dsv4p_nv | 200 | 18,477 | 18,479 | — | 0 | 0 |
| 09:03 | glm5_2_nv | 502 | 5,215 | 5,217 | zombie | 56,436 | 6 |

### 容器完整列表
| 容器 | 状态 |
|------|------|
| cc4101 | Up 2 hours |
| legacy_* (6 containers) | Up 9 hours (healthy) |
| logs_db | Up 27 hours (healthy) |
| ms_gw | Up 27 hours (healthy) |
| nv_gw | Up 2 hours (healthy) |

## 2. 分析

### 失败根因
1. **zombie_empty_completion (85%)**: NVCF content-filter — 输入 ~223K chars, 输出 2-48 chars, finish_reason=stop. 代码级 zombie 检测功能 (R1107), 快速 abort (3-15s). 不可配置修复.
2. **all_tiers_exhausted (15%)**: dsv4p_nv 504 gateway timeout → 5 keys 全失败 → ms_gw relay TimeoutError 132s (relay_started=True). NV-ALL-TIERS-FAIL 显示 ABORT-NO-FALLBACK 但 ms_gw fallback 依然触发并失败. ms_gw streaming sync defect (R832/R1103), 代码级缺陷, 不可配置修复.

### 参数状态
所有参数已处于 floor/optimal:
- UPSTREAM=66 (floor, BUDGET=UPSTREAM pattern R1440)
- BUDGET_DSV4P=66 (BUDGET Floor Pattern, 504-dominated)
- FASTBREAK 全 floor (PEXEC=1, INTEGRATE=1, EMPTY_200=2)
- TIER_COOLDOWN=15 (floor)
- KEY_COOLDOWN=25 (optimal)
- MS_GW_FALLBACK_TIMEOUT=120 (generous, 不会被 BUDGET=205 截断: 205-66=139 > 120)
- PEER_FB_SKIP_MODELS=空 (peer-fb 全开, R1039 workaround)

### 与 R1605 对比
数据完全一致 (67/47/20 SR 70.1%, 17 zombie + 3 ATE, ms_gw 13/13 100% SR). compose md5 不变. 无新增流量模式, 无新增错误类型. 稳定状态 — 无参数优化空间.

### 为什么不是可修复的
- Zombie: NVCF 上游 content-filter — 网关正确检测并快速 abort. 无参数能阻止 NVCF 返回空内容.
- 504 ATE: 函数级 NVCF 降级 — 所有 5 个 key 都返回 504, FASTBREAK 不适用 (504 走 NV-CYCLE 非 FASTBREAK). BUDGET=66 已是最紧 floor (UPSTREAM_TIMEOUT). 降低 BUDGET 会在大请求时过早截断成功请求.
- ms_gw relay TimeoutError: streaming sync defect — nv_gw 与 ms_gw 之间的流同步问题, 非配置参数可修复.

## 3. 决策: NOP

零配置修改. 所有参数 floor/optimal, 所有失败根因不可配置修复. 误触发 — R1605 自提交, 无 HM1 新提交. ms_gw 100% SR 为可靠回退. 与 R1604-R1605 完全一致 — 稳定状态, 等待代码级修复.

## 4. 铁律确认
- 改前必有数据: §1 (DB + logs + env) ✓
- 改后必有验证: NOP, 无需验证 ✓
- 聚焦 nv_gw: 仅分析 nv_gw 链路 ✓
- 所有修改写入仓库: 本轮文件 commit + push ✓
- 铁律: 只改HM1不改HM2 (本轮无改动) ✓

## ⏳ 轮到HM1优化HM2
