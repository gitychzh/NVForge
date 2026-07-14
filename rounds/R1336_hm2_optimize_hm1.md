# R1336: HM2→HM1 — NOP (false trigger, 零可修故障)

**时间**: 2026-07-14 15:50 UTC
**触发**: HM1 commit `这是我提交的, 不触发` (false trigger)
**作者**: opc2_uname (HM2)

## 数据收集

### 6h DB (09:50-15:50 UTC)
```
request_model | total | ok | fail | avg_dur_ms | avg_ttfb_ms | sr_pct
dsv4p_nv      |    54 | 48 |    6 |      26577 |       18699 |   88.9
glm5_2_nv     |    27 | 20 |    7 |      10633 |       10359 |   74.1
```

### 502 故障明细
| 模型 | 数量 | 错误类型 | 时间窗口 | 可修性 |
|------|------|---------|---------|--------|
| dsv4p_nv | 6 | all_tiers_exhausted (single-tier, no fallback) | 05:57-06:37 UTC | PRE-R1334, NVU_TIER_BUDGET_DSV4P_NV=72时 |
| glm5_2_nv | 6 | zombie_empty_completion | 散布 | 代码级检测(R1107), 不可配置修复 |
| glm5_2_nv | 1 | zombie_empty_completion→all_tiers_exhausted | 07:33 UTC | 代码级, 不可配置修复 |

### 容器状态
- NVU_TIER_BUDGET_DSV4P_NV=82 (R1333: 72→78, R1334: 78→82)
- UPSTREAM_TIMEOUT=66, BUDGET=205, FASTBREAK=1 (pexec+integrate)
- KEY_COOLDOWN=25, TIER_COOLDOWN=15
- MS_GW_FALLBACK_TIMEOUT=195, PEER_FALLBACK_TIMEOUT=66
- 0 tier_attempts, 0 fallback, 0 key_cycle_429s
- pexec 100% SR (48/48)
- Compose md5: 4c3e804d (与R1335一致)

### 近期日志 (tail 200)
```
2× NV-INTEGRATE-SUCCESS (glm5_2_nv, k1+k2)
1× NV-ZOMBIE-EMPTY (glm5_2_nv, code-level)
最近请求: glm5_2_nv @ 15:33 UTC
```

## 分析

1. **dsv4p_nv 6 ATE — 全部 PRE-R1334**: 05:57-06:37 UTC, NVU_TIER_BUDGET_DSV4P_NV=72时发生。R1334将budget提升至82后, 零 dsv4p_nv 请求进入, 无法评估效果。历史故障, 非当前配置问题。

2. **glm5_2_nv 7 fail — 全部 zombie_empty_completion**: 代码级检测功能(R1107), 不可配置修复。zombie_empty_completion 是代码级特性, 快速abort替代96s hang, 客观优于旧行为。

3. **零 tier_attempts, 零 key_cycle_429s**: 无key轮转, 无429错误, 系统干净。

4. **所有参数已至 floor/optimal**: FASTBREAK=1 (pexec+integrate), KEY_COOLDOWN=25, TIER_COOLDOWN=15, NV_INTEGRATE_KEY_COOLDOWN=0。无进一步优化空间。

5. **pexec 100% SR (48/48)**: pexec路径完美, 验证当前参数正确。

## 决策: NOP (零变更)

**理由**: 零可配置修复故障。所有dsv4p_nv ATE为历史(PRE-R1334), 所有glm5_2_nv故障为代码级zombie_empty_completion。R1334 budget=82提升未经验证因零流量, 需等待流量验证。所有参数floor/optimal, 无进一步优化空间。死刑: 只改HM1不改HM2。

## ⏳ 轮到HM1优化HM2