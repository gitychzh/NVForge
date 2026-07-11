# HM2 Optimize HM1 — Round R1204

## ⏱️ 时间
2026-07-11 18:30 UTC (cron dispatch, 72nd chain of R1133)

## 📊 触发分析
- cron 脚本输出: `"这是我提交的, 不触发"` (R1203 是 HM2 提交)
- 脚本正确检测到自提交, 但 cron 仍被派遣 → 误触发 (72nd chain of R1133)
- HM1 git log: 停留在 R821 (382 轮落后于 HM2)

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

### 24h 全景
| 指标 | 值 |
|------|-----|
| 总请求 | 234 |
| 成功 | 182 (77.8%) |
| 失败 | 52 (22.2%) |
| zombie | 48 |
| all_tiers_exhausted | 3 (dsv4p_nv, 61.1-61.4s, Jul 10 15:50-18:02) |
| NVStream_TimeoutError | 2 (96s, Jul 10) |

### 小时级 Zombie SR
| 小时 | 总 | OK | 失败 | SR% |
|------|-----|-----|------|-----|
| 04:00 | 4 | 2 | 2 | 50.0% |
| 05:00 | 4 | 2 | 2 | 50.0% |
| 06:00 | 4 | 2 | 2 | 50.0% |
| 07:00 | 4 | 2 | 2 | 50.0% |
| 08:00 | 4 | 2 | 2 | 50.0% |
| 09:00 | 11 | 9 | 2 | 81.8% |
| 10:00 | 5 | 3 | 2 | 60.0% |

### Zombie 详情
- 全部 glm5_2_nv integrate, NVCF content-filter
- finish_reason=stop, content_chars=12-36 < 50
- 输入 173K-176K chars
- 3-15s 快速 abort (NV-ZOMBIE-EMPTY + NV-ZOMBIE-ERROR-CHUNK 正确触发)
- 50% 僵尸率自 2026-07-10 22:00 UTC 起持续

### tier_attempts
0 行 (zombie 检测在 key 耗尽前触发)

### ms_gw
- 6h 流量: 0 (ms_requests 表 0 行)
- nv_gw ms_gw fallback: 0 次触发

### 按 key 分布 (成功请求)
| key_idx | 请求 | avg_ttfb | avg_dur |
|---------|------|----------|---------|
| 0 | 4 | 8,289ms | 12,590ms |
| 1 | 4 | 6,855ms | 6,856ms |
| 2 | 4 | 4,962ms | 4,963ms |
| 3 | 4 | 5,665ms | 10,954ms |
| 4 | 4 | 15,719ms | 15,719ms |

## 🔧 容器状态
- nv_gw: Up 15 hours (healthy), 重启于 2026-07-10T19:03:27Z
- compose md5: 未变
- FALLBACK_GRAPH: {} (空, 预期状态)
- tier_chain: ['glm5_2_nv'] (no fallback, 3model)

## 🎯 决策: NOP — Zero Param

### 诊断
1. **数据与 R1203 完全一致**: 32req/20OK(62.5%)/12zombie, 0 tier_attempts, 0 ms_gw, 0 dsv4p/kimi traffic。10 分钟内无新数据。
2. **zombie_empty_completion 是 NVCF 服务端内容过滤**: NVCF 对 173K+ 输入返回 stop+12chars 空完成。Gateway 正确检测并在 3-15s 快速 abort。无 config 参数可修复 NVCF content-filter 行为。
3. **所有参数 floor/optimal**: TIER_TIMEOUT_BUDGET_S=198, UPSTREAM=66, KEY_COOLDOWN_S=25, TIER_COOLDOWN_S=15, MIN_OUTBOUND_INTERVAL_S=0, NVU_TIER_BUDGET_DSV4P_NV=72, NVU_TIER_BUDGET_GLM5_2_NV=96, NVU_TIER_BUDGET_MINIMAX_M3_NV=100。全部已优化。
4. **24h 非 zombie 失败仅 5 例**: 3 dsv4p_nv ATE (Jul 10 15:50-18:02, 已过去 24h+) + 2 NVStream_TimeoutError (96s, Jul 10)。均为历史孤立事件，非当前持续问题。
5. **dsv4p_nv 0 流量**: 15h+ 无请求，无 ATE，无 fallback 触发。
6. **Zombie 50% 率自 22:00 UTC Jul 10 起持续**: 这是 NVCF 服务端变更导致的内容过滤行为变化，与 gateway 配置无关。

### 参数变更: 零
无任何配置参数修改。铁律: 只改HM1不改HM2。

## ✅ 裁决
- 更少报错: N/A (zombie 是 NVCF 服务端内容过滤, 非 config-fixable)
- 更快请求: N/A (所有参数已 floor/optimal)
- 超低延迟: N/A (3-15s zombie abort 已是最优)
- 稳定优先: ✅ compose 未变, 容器未重启

## ⏳ 轮到HM1优化HM2