# R1730 (HM2→HM1): NOP — R1729 just deployed 6min ago, zero post-restart data, dsv4p peer-fb budget-cap gap identified

> **轮次**: R1730 | **日期**: 2026-07-18 06:05 UTC | **操作者**: HM2 (opc2_uname)
> **决策**: ⏸️ NOP — nv_gw restarted 6min ago (R1729), zero post-restart data, all params consistent
> **铁律**: 只改HM1不改HM2

## 数据收集

### 容器状态
- **nv_gw**: Up 6 minutes (healthy) — R1729 刚重启
- **cc4101**: Up 28 hours
- **ms_gw**: Up 29 hours (healthy)
- **logs_db**: Up 29 hours (healthy)

### 6h 窗口 (2026-07-18 ~00:00–06:00 UTC)

| 指标 | 值 |
|------|-----|
| 总请求 | 55 |
| 成功 (200) | 46 |
| 失败 (502) | 9 |
| **成功率** | **83.6%** |
| 0 fallback | 55/55 |

### 错误分布 (6h)

| 错误类型 | 模型 | 数量 | 平均延迟 | 备注 |
|---------|------|------|---------|------|
| zombie_empty_completion | glm5_2_nv | 7 | 8,077ms | 全 >250K chars, BIG_INPUT breaker tiers_tried=1 |
| all_tiers_exhausted | dsv4p_nv | 2 | 69,524ms | 无救援 (peer-fb+ms_gw双跳过), status=502 |
| all_tiers_exhausted | glm5_2_nv | 3 | ~30,000ms | 幻影ATE (status=200, 非真实失败) |

### Zombie 详情 (7)
| ts | input_chars | duration_ms | tiers_tried |
|----|------------|-------------|-------------|
| 21:33 | 345,529 | 7,282 | 1 |
| 19:33 | 340,872 | 5,303 | 1 |
| 19:03 | 340,263 | 8,690 | 1 |
| 18:33 | 339,652 | 10,809 | 1 |
| 17:33 | 323,428 | 13,773 | 1 |
| 17:05 | 330,072 | 3,038 | 1 |

全 7 zombie: input >250K, tiers_tried=1, BIG_INPUT breaker 正确生效, avg 8.1s (vs 20-30s pre-breaker).

### dsv4p ATE 分析 (2)
| ts | input_chars | duration_ms | tiers_tried | fallback | peer-fb |
|----|------------|-------------|-------------|----------|---------|
| 18:07 | 82,280 | 70,017 | 1 | f | f |
| 18:04 | 82,280 | 69,030 | 1 | f | f |

**预算帽问题**: 70s (ATE实测) + 125s (PEER_FALLBACK_TIMEOUT) = 195s > BUDGET=145s → peer-fb 被预算帽跳过。ms_gw modelmap 不含 dsv4p_nv → 无双救援路径。2 ATE 完全无救援, 直接返回 502。

### OK 延迟
| 模型 | OK数 | avg | p50 | p95 | max |
|------|------|-----|-----|-----|-----|
| glm5_2_nv | 44 | 10,416ms | 8,779ms | 18,873ms | 46,061ms |
| dsv4p_nv | 1 | 25,141ms | 25,141ms | 25,141ms | 25,141ms |

### Tier Attempts (6h)
| tier | error_type | count | avg_ms | max_ms |
|------|-----------|-------|--------|--------|
| glm5_2_nv | pexec_success | 48 | 9,045 | 19,328 |
| glm5_2_nv | pexec_SSLEOFError | 1 | 5,002 | 5,002 |
| glm5_2_nv | pexec_429 | 1 | — | — |

### 429 分布
| 模型 | key_cycle_429s | 数量 |
|------|---------------|------|
| glm5_2_nv | 1 | 46 |
| glm5_2_nv | 2 | 2 |
| **总计** | | **48/55 (87.3%)** |

单IP固有特性, KEY_COOLDOWN=60 已最优, 非配置可修复。

### 日志 (nv_gw --tail 100)
```
[NV-GLM52-IDX] restored from glm52_mode_idx.json: idx=0
[NV-RR] restored from rr_counter.json: dsv4p=2568, kimi=83, glm5_2=843, minimax_m3=1
[NV-PROXY] Starting NV-unified proxy on 0.0.0.0:40006
[NV-PROXY] Listening on 0.0.0.0:40006 (role=passthrough, default_tier=dsv4p_nv)
```
零 ERROR/WARN/exception, 零 504, 零 NVCFPexecTimeout, 零 empty_200. 干干净净.

### 参数快照 (docker exec nv_gw env)

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 55 | R1729 刚部署 |
| TIER_TIMEOUT_BUDGET_S | 145 | R1725 |
| KEY_COOLDOWN_S | 60 | R1708 |
| TIER_COOLDOWN_S | 60 | R1708 |
| NVU_PEER_FALLBACK_ENABLED | 1 | enabled |
| NVU_PEER_FALLBACK_TIMEOUT | 125 | R1714 |
| NVU_PEER_FB_SKIP_MODELS | (空) | all models active |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms | dsv4p_nv 无映射 |
| NVU_TIER_BUDGET_DSV4P_NV | 60 | R1718 |
| NVU_TIER_BUDGET_GLM5_2_NV | 120 | |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | R1707 (floor) |
| NVU_EMPTY_200_FASTBREAK | 1 | R1707 (floor) |
| NVU_BIG_INPUT_THRESHOLD | 250000 | |
| NVU_BIG_INPUT_FAIL_N | 1 | R1713 |
| NVU_BIG_INPUT_COOLDOWN_S | 5400 | R1728 |
| NVU_BIG_INPUT_MODELS | glm5_2_nv | |
| NVU_SSLEOF_RETRY_DELAY_S | 0.5 | R1705 |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| NV_INTEGRATE_MODELS | (空) | disabled |

### 容器漂移检查
所有参数 container env == compose ✓, 零漂移。

## 候选参数评估

| 参数 | 当前值 | 候选 | 分析 | 结论 |
|------|--------|------|------|------|
| 全部参数 | — | — | nv_gw 重启 6min, 零 post-restart 数据 | ❌ 不可改 |
| TIER_TIMEOUT_BUDGET_S | 145 | 195 | 70+125=195, 解锁 dsv4p peer-fb | ❌ +50s 太大, 需观察 |
| NVU_PEER_FALLBACK_TIMEOUT | 125 | — | 125 ≥ HM2 glm5_2 BUDGET 120+2+3, 不可降 | ❌ |
| UPSTREAM_TIMEOUT | 55 | — | R1729 刚部署, 零 post-restart 数据 | ❌ |
| 其他参数 | — | — | 全 floor/optimal | ❌ |

## 分析

### R1729 部署状态
R1729 (UPSTREAM_TIMEOUT 53→55) 6 分钟前部署, 容器重启。仅 2 个 post-restart glm5_2 请求 (2 OK, p50=6.4s), 零 dsv4p 流量, 不足以评估任何指标。

### dsv4p peer-fb 预算帽问题
**关键发现**: 2 dsv4p ATE 在 6h 窗口内完全无救援 (peer-fb 跳过, ms_gw 无 dsv4p 映射)。

**根因**: 预算帽 `TIER_TIMEOUT_BUDGET_S=145` 阻塞了 peer-fb:
- dsv4p ATE 实测: 69-70s (尽管 NVU_TIER_BUDGET_DSV4P_NV=60, R1725: budget 非硬上限)
- PEER_FALLBACK_TIMEOUT=125s
- 合计: 70+125=195s > BUDGET=145s → peer-fb 被预算帽跳过
- ms_gw modelmap: `glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms` — dsv4p_nv 无映射
- 结论: dsv4p ATE 路径完全无救援, 100% 失败

**修复方案**: 提高 BUDGET 至 ≥195s (70+125), 或降低 PEER_FALLBACK_TIMEOUT (但 glm5_2 需要 125s)。

**为什么本轮不改**: 
1. nv_gw 重启 6min, 零 post-restart dsv4p 流量
2. dsv4p 仅 1 次 OK 在 6h 窗口内 (低频模型)
3. BUDGET 145→195 是 +50s 大跳, 违反 "少改多轮" 原则
4. 需要观察 R1729 UPSTREAM=55 对 ATE 实测时间的影响

### BIG_INPUT breaker 验证
- 7/7 zombie 全部 input >250K (323K-346K) ✓ (breaker 正确识别)
- 7/7 zombie 全部 tiers_tried_count=1 ✓ (FAIL_N=1 正确生效)
- 零 false positive (无 <250K 的 zombie) ✓
- avg 8.1s (vs 20-30s pre-breaker) ✓
- 1 SSLEOF (正常, 非 breaker 相关)

### SR 趋势
- R1729 (UPSTREAM 53→55): 85.2% SR (61req/52OK)
- R1730 (NOP): 83.6% SR (55req/46OK)

SR 稳定在 83-85% 区间, BIG_INPUT breaker 持续生效中。

### 为什么不能改
1. **零 post-restart 数据**: 容器重启 6min, 仅 2 glm5_2 请求, 任何改动都是盲操作
2. **dsv4p peer-fb 预算帽修复需 +50s BUDGET**: 违反 "少改多轮" 原则, 需观察 R1729 效果
3. **所有参数 floor/optimal**: 无单参数小幅调整空间
4. **BIG_INPUT breaker 需持续观察**: COOLDOWN=5400s (90min) 刚部署 R1728, 需验证

## 决策

**⏸️ NOP** — R1729 刚部署 6min, 零 post-restart 数据, 所有参数 floor/optimal/consistent。dsv4p peer-fb 预算帽问题 (70+125=195>145) 已识别但需多轮渐进式修复。保留所有参数不变, 仅维持 HM1↔HM2 交替节奏。
## ⏳ 轮到HM1优化HM2
