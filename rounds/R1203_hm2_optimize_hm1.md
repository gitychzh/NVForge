# HM2 Optimize HM1 — Round R1203

## ⏱️ 时间
2026-07-11 18:20 UTC (cron dispatch)

## 📊 触发分析
- cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit: R1202 (opc2_uname, HM2)
- 脚本正确检测到自提交并标记"不触发"
- cron 仍被派遣 → 误触发 (71st chain of R1133)
- HM1 git log: 停留在 R821 (381 轮落后于 HM2)
- HM1 最后 authored commit: 7625e14 (R818, 2026-07-08)

## 📊 6h 数据 (改前必有数据)

### 总体
| 指标 | 值 |
|------|-----|
| 总请求 | 32 |
| 成功 | 20 (62.5%) |
| 失败 | 12 (37.5%) |
| 全部错误 | zombie_empty_completion × 12 |

### 按模型
| 模型 | 请求 | OK | 失败 | SR% | 平均延迟 |
|------|------|-----|------|-----|---------|
| glm5_2_nv | 32 | 20 | 12 | 62.5% | 8,318ms |
| dsv4p_nv | 0 | 0 | 0 | - | - |
| kimi_nv | 0 | 0 | 0 | - | - |

### 错误类型
| 错误类型 | 数量 | 平均延迟 | 平均输入 |
|----------|------|---------|---------|
| zombie_empty_completion | 12 | 5,155ms | 173,393 chars |

### 小时级 SR
| 小时 | 总 | OK | 失败 | SR% |
|------|-----|-----|------|-----|
| 04:00 | 2 | 1 | 1 | 50.0% |
| 05:00 | 4 | 2 | 2 | 50.0% |
| 06:00 | 4 | 2 | 2 | 50.0% |
| 07:00 | 4 | 2 | 2 | 50.0% |
| 08:00 | 4 | 2 | 2 | 50.0% |
| 09:00 | 11 | 9 | 2 | 81.8% |
| 10:00 | 3 | 2 | 1 | 66.7% |

### fallback
| fallback_occurred | 请求 | OK |
|-------------------|------|-----|
| false | 32 | 20 |

### tier_attempts
0 行 (zombie 检测在 key 耗尽前触发)

### Zombie 详情
- 全部 glm5_2_nv integrate
- NVCF content-filter: finish_reason=stop, content_chars=12-36 < 50
- 输入 173K-176K chars
- 3-15s 快速 abort (vs 旧 96s NVStream_TimeoutError)
- NV-ZOMBIE-EMPTY + NV-ZOMBIE-ERROR-CHUNK 正确触发

### ms_gw
- 6h 流量: 0 (ms_requests 表 0 行)
- nv_gw ms_gw fallback: 0 次触发 (NV-MS-FB 无日志)
- ms_gw 直接请求: 正常 (MS-OK-STREAM + MS-STREAM-DONE)
- 参数: EMPTY_200_FASTBREAK_THRESHOLD=3 (floor), KEY_COOLDOWN_S=60, VARIANT_COOLDOWN_S=30, ALL_EXHAUSTED_COOLDOWN_S=30, MIN_OUTBOUND_INTERVAL_S=1.0

## 🔧 容器状态
- nv_gw: Up 15 hours (healthy), 重启于 2026-07-10T19:03:27Z
- compose md5: 7975939c245761e451a8813852dcb9bf (未变)
- FALLBACK_GRAPH: {} (空, 预期状态)
- tier_chain: ['glm5_2_nv'] (no fallback, 3model) — 预期

## 🎯 决策: NOP — Zero Param

### 诊断
1. **zombie_empty_completion 是 code-level 特性**: gateway 正确检测 NVCF content-filter 返回的空完成 (stop+12chars, 173K input), 在 3-15s 快速 abort, 触发 openclaw fallback。无 config 参数可修复 NVCF content-filter 行为。
2. **所有参数 floor/optimal**: TIER_TIMEOUT_BUDGET_S=198, UPSTREAM=66, KEY_COOLDOWN_S=25, TIER_COOLDOWN_S=15, MIN_OUTBOUND_INTERVAL_S=0, NVU_TIER_BUDGET_DSV4P_NV=72, NVU_TIER_BUDGET_GLM5_2_NV=96, 全部已优化。
3. **ms_gw 无优化空间**: 0 流量 (nv_gw 未触发 ms_gw fallback), EMPTY_200_FASTBREAK_THRESHOLD=3 (floor), 其他参数标准值。
4. **dsv4p_nv 0 流量**: 15h 无请求, 无 ATE, 无 fallback 触发。
5. **数据与 R1202 一致**: 32req/20OK(62.5%)/12zombie, 0 tier_attempts, 0 ms_gw traffic。

### 参数变更: 零
无任何配置参数修改。铁律: 只改HM1不改HM2。

## ✅ 裁决
- 更少报错: N/A (zombie 是 code-level, 非 config-fixable)
- 更快请求: N/A (所有参数已 floor/optimal)
- 超低延迟: N/A (3-15s zombie abort 已是最优)
- 稳定优先: ✅ compose 未变, 容器未重启

## ⏳ 轮到HM1优化HM2
