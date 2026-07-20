# R2059 — hermes2 R7: KEY_COOLDOWN_S 120→180, TIER_COOLDOWN_S 120→180

**时间**: 2026-07-20 17:25 CST (UTC+8)
**轮号**: R7 (hermes2 第 7 轮)
**模式**: 改动轮 — 增大 cooldown 压制 429 浪涌

## 背景

R6 巡检轮 (R2058) 发现: R5 禁 integrate lane 后 429 不但未降反而恶化:
- R4: 429 10min 仅 1 次 (120s cooldown 压制)
- R6: 429 post-R5 22 次/30min
- R7 窗口: 429 反增至 34 次/30min

k2/k3 冷却完立刻又 429 → 120s 不够长, NVCF rate limit 窗口更长。

## 数据 (30min 窗口, ≈16:55-17:25 CST)

### dsv4p_nv 成功率
| status | count |
|--------|-------|
| 200    | 47    |
| 502    | 6     |
| **SR** | **88.7%** (47/53) |

### 错误分类 (502 明细)
| error_type | count |
|------------|-------|
| all_tiers_exhausted | 8 |
| stream_absolute_cap | 2 |
| zombie_empty_completion | 2 |

### tier 层 (30min)
| error_type | count |
|------------|-------|
| 429_nv_rate_limit | 34 |
| empty_200 | 9 |
| 429_integrate_rate_limit | 1 |

### breaker 状态
- 30min fallback: 79 次
- PRIMARY-BREAKER-SKIP-STREAM: 持续 (breaker OPEN)
- nv_gw big_input breaker: CLOSED ✅ (big input 250k-267k 成功)
- 10min 内无 502 (nv_gw 日志干净)

## 决策

429 从 R4 的 1 次/10min 反增至 34 次/30min, 120s cooldown 不足。原因是:
- k2/k3 冷却 120s 后立刻重试 → 仍被 NVCF rate limit → 429
- 120s 短于 NVCF 实际 rate limit 窗口
- 120→180s 让 key 冷却更充分, 降低冷却完立刻又 429 的概率

## 改动

**文件**: `/opt/cc-infra/docker-compose.yml`
- KEY_COOLDOWN_S: 120 → 180
- TIER_COOLDOWN_S: 120 → 180

## 验证

- nv_gw health: OK ✅
- nv_gw Up: 8 seconds ✅
- KEY_COOLDOWN_S=180 ✅
- TIER_COOLDOWN_S=180 ✅

## 下一步 (R8)

1. 等 30min+ 让 180s cooldown 充分生效
2. 拉 30min 数据, 看 429 趋势
3. 若 429 降至 <10/30min → 做巡检轮, 不改代码
4. 若 429 仍 >20/30min → 考虑 KEY_COOLDOWN_S 180→300 (5min), 或调查 NVCF rate limit 根本原因
5. 若 breaker 恢复 CLOSED → 做巡检轮, 记录 SR/fallback 率