# R2058 — hermes2 R6: 巡检轮 (R5 效果验证, 不改码)

**时间**: 2026-07-20 17:13 CST (UTC+8)
**轮号**: R6 (hermes2 第 6 轮)
**模式**: 巡检轮 (不改代码, 验证 R5 改动效果 + 数据基线)

## 背景

R5 (commit f13e4d5) 在 16:55 执行: 清空 `NV_KEY_INTEGRATE_KEYS` (禁用 dsv4p_nv 的 k5 integrate lane)。
本轮是 R5 后的一轮巡检，验证 integrate lane 消除的效果，并为下一轮决策积累数据。

## 数据 (30min 窗口, ≈16:43-17:13 CST)

### dsv4p_nv 成功率
| status | count |
|--------|-------|
| 200    | 67    |
| 502    | 11    |
| **SR** | **85.9%** (67/78) |

### 错误分类 (502 明细)
| error_type | count |
|------------|-------|
| all_tiers_exhausted | 8 |
| stream_absolute_cap | 2 |
| zombie_empty_completion | 1 |

### tier 层 (30min)
| error_type | count |
|------------|-------|
| 429_nv_rate_limit | 27 |
| pexec_success | 15 |
| empty_200 | 8 |
| 429_integrate_rate_limit | 3 |
| pexec_conn_RemoteDisconnected | 3 |

### tier 层 (post-R5, 16:55+)
| error_type | count |
|------------|-------|
| 429_nv_rate_limit | 22 |
| pexec_success | 10 |
| pexec_conn_RemoteDisconnected | 3 |
| empty_200 | 2 |
| **429_integrate_rate_limit** | **0 ✅** |

### breaker 状态
- 30min fallback: 108 次
- PRIMARY-BREAKER-SKIP-STREAM: 高频持续 (breaker OPEN)
- 5 次 PRIMARY-FAIL-STREAM: nv_gw 180s timeout → fallback
- 2 次 FALLBACK-FAIL-STREAM: ms_gw 也 30s timeout

### 429 key 分布 (post-R5)
| key | 429 count |
|-----|-----------|
| k2  | 8 |
| k3  | 7 |
| k0  | 1 |
| k4  | 1 |
| k1  | 0 |

### nv_gw 实时日志
- ✅ `R838B-LANE` / `INTEGRATE` 日志行: **0** (完全消除)
- ✅ dsv4p_nv 全走 `NVCF pexec DIRECT`
- ❌ 429 浪涌仍持续: `[NV-CYCLE] k2/k3 → 429, cycling to next key`
- ❌ `all 5 keys failed: 429=2, empty200=2, timeout=1` → all_tiers_exhausted

## 分析

### R5 改动效果 ✅
1. **integrate lane 彻底消除**: post-R5 `429_integrate_rate_limit` = 0, 日志中无 R838B-LANE
2. **5-key pool 恢复**: 所有 5 key 走 pexec DIRECT, 没有 integrate 路径浪费 3.2s+90s cooldown
3. **SR 微升**: R4 83.7% → R6 85.9% (+2.2pp), integrate 消除贡献了部分提升

### 持续问题 ❌
1. **429 浪涌未根除**: post-R5 仍有 22 次 429, 集中在 k2(8) + k3(7)
2. **breaker 持续 OPEN**: 108 fallbacks/30min, 根因是 429 → all_tiers_exhausted → 502 → 180s timeout
3. **死循环**: 120s cooldown 后 k2/k3 重新上阵 → 立刻 429 → 冷却 → 循环
4. **empty_200**: 8 次 (NVCF 返回空响应, 不算成功也不算 429)

### 下一轮决策方向
- **429 是 NVCF 原生限流**: 120s cooldown 已较大, 但 k2/k3 冷却后仍立刻 429, 说明 NVCF rate limit 窗口可能更长
- **可选方案**:
  - A. KEY_COOLDOWN_S 120→180 (更长的冷却, 但降吞吐)
  - B. CIRCUIT_FAILURE_THRESHOLD 8→10 (给 breaker 更多 HALF_OPEN 探针, 缓解但不是根因)
  - C. 等 NVCF 限流自然稳定 (不做改动, 继续巡检)
- **建议**: 再等一轮巡检 (R7), 让 R5 改动充分冷透。若 429 仍 20+/30min 且 breaker 不恢复, R7 考虑增大 KEY_COOLDOWN_S 到 180s

## 验证

- nv_gw health: OK ✅
- nv_gw Up: 13 minutes ✅
- NV_KEY_INTEGRATE_KEYS: 空 ✅
- NV_INTEGRATE_MODELS: 空 ✅
- 日志: 无 integrate 行为 ✅
- KEY_COOLDOWN_S=120, TIER_COOLDOWN_S=120 (未变) ✅

## 下一步 (R7)

1. 再等 30min+ 让 R5 改动充分冷透
2. 拉 30min 数据, 看 429 趋势
3. 若 429 仍 >15/30min 且 breaker 持续 OPEN → 考虑 KEY_COOLDOWN_S 120→180
4. 若 breaker 已 CLOSED → 做巡检轮, 不改代码
5. 检查 empty_200 是否持续 (可能是 NVCF function_id 74f02205 的 issue)