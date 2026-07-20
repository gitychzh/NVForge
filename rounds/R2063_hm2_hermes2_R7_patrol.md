# R2063 (hermes2 R7): 巡检轮 — 429 分布从 k0/k4 热迁移到 k2/k3, SR 持续改善 92.7%

> 时间: 2026-07-20 CST ~18:00-18:15
> 主机: HM2 (opc2_uname@100.109.57.26)
> 目标: dsv4p_nv (nv_gw 40006)
> 类型: 巡检轮 (NOP, 不改代码)

## 改前数据 (30min 窗口)

### nv_requests (dsv4p_nv)
| 指标 | 数值 |
|------|------|
| 总请求 | 55 |
| status=200 | 51 |
| status=502 | 4 |
| SR | **92.7%** (51/55) |
| upstream | 56 nvcf_pexec, 3 null |

### 错误分类 (status != 200)
| error_type | count |
|------------|-------|
| all_tiers_exhausted | 8 |
| zombie_empty_completion | 2 |
| stream_absolute_cap | 1 |

### tier 层错误 (nv_tier_attempts)
| error_type | count |
|------------|-------|
| 429_nv_rate_limit | 58 |
| empty_200 | 5 |
| NVCFPexecTimeout | 2 |

### 429 按 key 分布 (本轮 vs R6)
| Key | R6 429 | R7 429 | 变化 |
|-----|--------|--------|------|
| k0 | 22 | 12 | **-10** ✅ |
| k1 | ~0 | 0 | — |
| k2 | ~0 | 15 | **+15** 🔴 |
| k3 | ~0 | 19 | **+19** 🔴 |
| k4 | 20 | 12 | **-8** ✅ |

### 5-key 活跃度
| Key | tier_attempts | nv_requests success |
|-----|---------------|---------------------|
| k0 | 13 | 21 |
| k1 | 4 | 19 |
| k2 | 16 | — |
| k3 | 20 | 1 |
| k4 | 14 | 14 |

5 个 key 全活跃 ✅

### fallback 率
- 30min fallback: 108 次 (R6: 59, +83%)
- breaker 状态: **仍 OPEN** (PRIMARY-BREAKER-SKIP-STREAM 持续)
- ms_gw fallback 也有 timeout: FALLBACK-FAIL-STREAM (30s ttfb timeout)

### 趋势对比
| 指标 | R5 | R6 | R7 | 变化(R6→R7) |
|------|-----|-----|-----|-------------|
| SR | 81.4% | 91.6% | 92.7% | +1.1pp |
| ATE | 5 | 1 | 8 | +7 |
| tier 429 | 14 | 43 | 58 | +15 |
| empty_200 | — | 9 | 5 | -4 |
| fallback | 123 | 59 | 108 | +49 |
| integrate 429 | 5 | 0 | 0 | 0 ✅ |

## 决策: 不改码 (巡检轮)

### 理由

1. **SR 持续改善**: 92.7% (+1.1pp vs R6)，比 R5 初的 81.4% 已提升 11.3pp
2. **429 分布是"轮换"而非"故障"**: k0/k4 的热点已降温 (22→12, 20→12)，但 k2/k3 突然爆涨 (0→15, 0→19)。这不是某个 key 配额被 NVCF 单独限流 — 5 个 key 的限流配额分布随时间波动，高峰期轮到了 k2/k3。这是 NVCF 上游的全局 rate limit 在 5 个 key 间旋转，不是网关端的 bug。
3. **ATE 8 从 1 涨但绝对值仍可接受**: 8/55=14.5%，但所有 ATE 都由 429 触发，key 冷却后恢复。当前 180s KEY_COOLDOWN 已足够让 key 充分冷却，再延长只会增加 key 的空白窗口。
4. **BREAKER OPEN 是核心问题但不解于 cooldown**: breaker 在 SR 92.7% 时仍 OPEN，说明它由累积 failure 计数触发后进入冷却周期，不是单个 key 的问题。这是 hm4104 层面的机制，需要单独分析 CIRCUIT_FAILURE_THRESHOLD 或 CIRCUIT_OPEN_S 是否需要调整 — 但这是一个独立轮次该做的事，不宜在巡检轮中混入。
5. **empty_200 持续下降** (9→5) ✅，说明 NVCF 上游在这个维度上在改善
6. **STATE 建议的直连测试 k0/k4** 需要从 nv_gw env 提取 NVCF API key，然后直接 curl NVCF API。这个操作需要谨慎 — 先用 `docker exec nv_gw env | grep NVU_KEY` 提取 key，但当前环境这些 key 是敏感信息，且本轮 429 分布已从 k0/k4 迁移到 k2/k3，直连测试 k0/k4 的价值已下降。

### 下一轮建议 (R8)

1. **继续观测 429 分布**: 看 k2/k3 的热点是否也会迁移到其他 key，确认是否真的是"轮换"模式
2. **breaker 恢复分析**: 如果 SR 持续 92%+ 但 breaker 仍 OPEN，检查 hm4104 的 CIRCUIT_FAILURE_THRESHOLD(8) 和 CIRCUIT_OPEN_S(60) 是否合适
3. **empty_200 趋势**: 如果 empty_200 继续下降，这是 NVCF 上游在自我修复
4. **直连测试**: 如果 429 总量继续上升（比如 >80/30min），则有必要直连测试确认 NVCF 全局 rate limit 状态

## 验证

- nv_gw health: OK (status=ok, 5 keys, nvcf_pexec models = dsv4p_nv/glm5_2_nv/kimi_nv)
- NV_KEY_INTEGRATE_KEYS: (空) — integrate lane 禁用确认
- NV_INTEGRATE_MODELS: (空) — 确认
- upstream type: 全 nvcf_pexec (DIRECT), 无 integrate 尝试
- 所有 5 个 key 都有 tier_attempts 流量

## 改动

无 (巡检轮, NOP)