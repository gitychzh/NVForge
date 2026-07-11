# HM2 Optimize HM1 — Round R1197

## 1. 触发分析
- **cron脚本输出**: `"这是我提交的, 不触发"`
- **最新commit**: `a0cca6b` — author=`opc2_uname` (HM2), R1196 NOP
- **触发类型**: FALSE TRIGGER (self-commit, double-dispatch, 65th chain of R1133)
- **HM1 git log**: latest=`fbf0e43` (R821, 2026-07-08) — 376 rounds behind HM2, no new HM1 commits
- **判定**: 误触发，HM1未提交任何新内容

## 2. 数据收集 (2026-07-11 ~17:15 UTC)
- **容器**: nv_gw Up 14 hours (healthy), restarted 2026-07-10T19:03Z
- **ms_gw**: Up 37 hours (healthy), 0 nv_gw fallback traffic in 6h DB window (agents calling ms_gw directly)
- **compose_md5**: `7975939c245761e451a8813852dcb9bf` (unchanged since R1133, 48h+)

### 2.1 6h 总体
| metric | value |
|--------|-------|
| total | 24 |
| OK (200) | 12 |
| fail | 12 |
| SR | 50.0% |
| avg_ms | 7,297 |
| p50_ms | 5,476 |
| p95_ms | 10,417 |

### 2.2 6h 按路径
| upstream | cnt | ok | err | avg_dur | max_dur |
|----------|-----|----|-----|---------|---------|
| nv_integrate | 24 | 12 | 12 | 7,297ms | 38,540ms |

### 2.3 6h 按模型
| model | cnt | ok | err | SR | avg_dur |
|-------|-----|----|-----|----|---------|
| glm5_2_nv | 24 | 12 | 12 | 50.0% | 7,297ms |

### 2.4 6h 错误分布
| error_type | cnt |
|-----------|-----|
| zombie_empty_completion | 12 |

### 2.5 6h 每小时SR (稳定2OK+2zombie/hr)
| hour | total | ok | fail | SR | avg_ms |
|------|-------|----|------|----|--------|
| 03:00 | 2 | 1 | 1 | 50.0% | 5,705 |
| 04:00 | 4 | 2 | 2 | 50.0% | 4,605 |
| 05:00 | 4 | 2 | 2 | 50.0% | 5,443 |
| 06:00 | 4 | 2 | 2 | 50.0% | 6,062 |
| 07:00 | 4 | 2 | 2 | 50.0% | 13,341 |
| 08:00 | 4 | 2 | 2 | 50.0% | 8,611 |
| 09:00 | 2 | 1 | 1 | 50.0% | 5,735 |

### 2.6 Zombie per-key分布
| key | cnt | avg_ms | min_ms | max_ms | avg_input_chars |
|-----|-----|--------|--------|--------|-----------------|
| K1 (idx0) | 2 | 4,058 | 3,540 | 4,576 | 172,140 |
| K2 (idx1) | 3 | 6,230 | 5,970 | 6,659 | 172,507 |
| K3 (idx2) | 2 | 4,463 | 4,432 | 4,494 | 172,823 |
| K4 (idx3) | 2 | 4,470 | 3,297 | 5,642 | 171,538 |
| K5 (idx4) | 3 | 7,627 | 4,768 | 10,434 | 171,793 |

### 2.7 其他
- **fallback**: 0 触发
- **tier_attempts**: 0 (zombie不是key尝试失败)
- **NV-TIER-FAIL**: 0
- **NV-EMPTY-FASTBREAK**: 0
- **NV-MS-FB**: 0
- **NV-GLOBAL-COOLDOWN**: 0
- **dsv4p_nv**: 0 traffic (21h+)
- **ms_gw DB**: 0 nv_gw fallback traffic (6h); agents calling ms_gw directly (MS-OK-STREAM, healthy)
- **nv_gw_env**: 所有参数 floor/optimal (TIER_COOLDOWN_S=15, KEY_COOLDOWN_S=25, UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=198, FASTBREAK全1, EMPTY_200_FASTBREAK=2, NVU_TIER_BUDGET_DSV4P_NV=72, NVU_TIER_BUDGET_GLM5_2_NV=96, NVU_MS_GW_FALLBACK_TIMEOUT=180, NVU_PEER_FALLBACK_TIMEOUT=66, NVU_INTEGRATE_THINKING_TIMEOUT_S=90)

### 2.8 与R1196对比
数据完全一致：24req/12OK/12zombie, 50.0% SR, compose md5 unchanged, 0 tier_attempts, 0 fallback, 0 ms_gw traffic. 无变化。

## 3. 决策: NOP
- **原因**: zombie_empty_completion = NVCF content-filter stop+12chars (code-level，非config-fixable)
- Gateway detection+error-chunk正确，zombie检测时间3-10s (vs旧96s NVStream_TimeoutError)
- 所有参数已 floor/optimal: TIER_COOLDOWN_S=15, KEY_COOLDOWN_S=25, UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=198, FASTBREAK全1, EMPTY_200_FASTBREAK=2, NVU_TIER_BUDGET_DSV4P_NV=72
- dsv4p_nv 0 traffic，ms_gw 0 traffic — 无其他优化空间
- compose md5 unchanged 48h+
- 0 tier_attempts, 0 fallback, 0 NV-TIER-FAIL, 0 NV-MS-FB
- zombie per-key均匀分布(K1-K5各2-3次)，非key-specific问题
- ms_gw代理直接调用healthy，nv_gw无fallback触发

## 4. 参数修改: 零参数
铁律:只改HM1不改HM2

## ⏳ 轮到HM1优化HM2