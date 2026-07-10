# HM2 Optimize HM1 — Round R1097

## 触发
R1096 NOP (false trigger, post-restart glm5_2_nv-only traffic) 后 cron 检测到 HM1 提交了新 commit → 轮到 HM2 优化 HM1。

## 数据收集 (改前必有数据)

### nv_gw 容器状态
- 重启时间: 2026-07-10 12:09 UTC (R1088 时重启)
- 容器: nv_gw, Up healthy
- 有效窗口: 重启后 ~9.5h

### 24h 窗口 (含重启前数据)
| 指标 | 值 |
|------|-----|
| 总请求 | 549 |
| 成功 | 512 (93.3% SR) |
| 失败 | 37 |
| avg TTFB | 14,822ms |
| avg duration | 22,581ms |
| max duration | 208,108ms |
| avg key_cycle_429s | 0.01 |

### 24h 错误分类
| error_type | cnt |
|------------|-----|
| all_tiers_exhausted | 27 |
| NVStream_TimeoutError | 7 |
| stream_total_deadline | 3 |

### 24h 按路径+模型分解
| request_model | upstream_type | cnt | ok | SR | avg_ttfb | avg_dur | max_dur |
|---------------|---|---|-----|-----|------|----------|---------|---------|
| glm5_2_nv | nv_integrate | 359 | 350 | 97.5% | 15,802ms | 19,600ms | 129,132ms |
| dsv4p_nv | nvcf_pexec | 61 | 61 | **100%** | 15,380ms | 15,385ms | 59,548ms |
| kimi_nv | nvcf_pexec | 61 | 61 | **100%** | 10,706ms | 10,723ms | 71,985ms |
| minimax_m3_nv | nv_integrate | 33 | 32 | 97.0% | 10,772ms | 13,500ms | 75,345ms |
| dsv4p_nv | (ATE) | 13 | 0 | 0% | 878ms | 60,060ms | 132,017ms |
| minimax_m3_nv | (ATE) | 11 | 4 | 36.4% | 0ms | 110,940ms | 159,342ms |
| glm5_2_nv | (ATE) | 8 | 2 | 25.0% | 583ms | 130,133ms | 208,108ms |

### dsv4p_nv ATE 详情 (24h, 全部 single-tier)
| ts | duration_ms | fallback_occurred | fallback_tiers_used | error_subcategory |
|----|------------|-------------------|---------------------|-------------------|
| 09:06 UTC | 132,017 | f | {dsv4p_nv} | all_tiers_failed_in_mapped_tier |
| 08:20 UTC | 1,328 | f | {dsv4p_nv} | all_tiers_failed_in_mapped_tier |
| 06:07 UTC | 110,073 | f | {dsv4p_nv} | all_tiers_failed_in_mapped_tier |
| 05:59 UTC | 110,058 | f | {dsv4p_nv} | all_tiers_failed_in_mapped_tier |
| 20:16 UTC | 61,249 | f | {dsv4p_nv} | all_tiers_failed_in_mapped_tier |
| 19:37 UTC | 61,105 | f | {dsv4p_nv} | all_tiers_failed_in_mapped_tier |
| 19:03 UTC | 61,151 | f | {dsv4p_nv} | all_tiers_failed_in_mapped_tier |
| (其余 pre-restart) | ~60-110s | f | {dsv4p_nv} | all_tiers_failed_in_mapped_tier |

- 13 ATE 全部 single-tier, fallback_occurred=false, fallback_actually_attempted=false
- 0 tier_attempts 行 (无 key 级失败记录 — NVCF function-level reject)
- 1,328ms ATE 极快 — 疑似 empty_200 FASTBREAK=1 立即中止 tier
- 60-132s ATE — 疑似 NVCF 504 gateway timeout 循环 (R1078: 504 bypasses FASTBREAK, burns per-tier budget)
- 所有下游 tier (kimi_nv 100% SR, glm5_2_nv 97.5%, minimax_m3_nv 97.0%) 均未被尝试

### 2h 窗口 (重启后纯数据, 低流量)
| 指标 | 值 |
|------|-----|
| 总请求 | 3 |
| 成功 | 3 (100.0% SR) |
| 失败 | 0 |
| 路径 | 全部 nv_integrate (glm5_2_nv) |
| avg TTFB | 20,200ms |

### 24h tier_attempts
| tier | error_type | cnt | avg_ms | max_ms |
|------|-----------|-----|--------|--------|
| glm5_2_nv | IntegrateRemoteDisconnected | 1 | 20,284ms | 20,284ms |
| glm5_2_nv | IntegrateTimeout | 1 | 90,566ms | 90,566ms |
| kimi_nv | empty_200 | 1 | — | — |
| minimax_m3_nv | IntegrateTimeout | 1 | 90,762ms | 90,762ms |

### peer-fallback 统计 (24h)
| 指标 | 值 |
|------|-----|
| 对端 HM2 请求 | 0 (零 peer-fallback 触发) |

### 关键 env vars
| 参数 | 值 |
|------|-----|
| TIER_TIMEOUT_BUDGET_S | 198 |
| NVU_TIER_BUDGET_DSV4P_NV | 66 |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 |
| UPSTREAM_TIMEOUT | 66 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 180 |
| NVU_EMPTY_200_FASTBREAK | 2 (⚠️ R1039: pexec 路径不生效) |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv |
| **NVU_FALLBACK_HEALTH_THRESHOLD** | **0.10** ← 本轮目标 |
| NVU_STREAM_TOTAL_DEADLINE_S | 90 |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 |

## 诊断

### 核心问题: dsv4p_nv ATE 全部 single-tier, 下游 tier 被排除
```
dsv4p_nv ATE 13 次 → fallback_tiers_used={dsv4p_nv} only
→ fallback_occurred=f → 下游 tier 均未尝试
→ kimi_nv (100% SR), glm5_2_nv (97.5% SR), minimax_m3_nv (97.0% SR) 全部被排除
```

### 根因: NVU_FALLBACK_HEALTH_THRESHOLD=0.10 过于激进
```
NVU_FALLBACK_HEALTH_THRESHOLD=0.10:
  → 健康度 < 10% 的 tier 被排除出 fallback chain
  → 低流量时 MIN_SAMPLES 过期, health 数据回退到默认值
  → 下游 tier 临时被判定为 unhealthy (< 10%) → 被排除
  → dsv4p_nv 单 tier 失败 → 无 fallback → ATE
```

R982 已验证此模式: "dsv4p_nv 被排除出 tier_chain (MIN_SAMPLES expired, health<0.10), 导致 glm5_2→dsv4p fallback 消失 → 2 single-tier ATE"

### 24h 验证: 0.05 安全可行
```
kimi_nv: 61/61 (100%) → 任何阈值都不会排除
glm5_2_nv: 350/359 (97.5%) → 任何阈值都不会排除
minimax_m3_nv: 32/33 (97.0%) → 任何阈值都不会排除
```

0.05 仅排除真正死掉 (0% SR) 的 function，保留任何有微弱存活率的 fallback。所有下游 tier 均有 >95% SR，降低阈值到 0.05 不会引入不可靠 tier。

### 影响评估
```
0.10 → 0.05:
  - 成功路径: 零影响 (健康 tier 本就不被排除)
  - 失败路径: dsv4p_nv ATE 时保留 kimi_nv/glm5_2_nv/minimax_m3_nv fallback
  - 预期: 13/13 dsv4p_nv ATE 中至少部分能通过下游 tier 或 ms_gw 救回
  - 风险: 极小 — 0.05 仅增加 5% 阈值区间, 不会引入死 tier
```

## 变更

**参数**: `NVU_FALLBACK_HEALTH_THRESHOLD`

**旧值**: `0.10` (R982)

**新值**: `0.05` (-0.05)

**理由**: 0.10 在低流量/健康数据过期时排除高可用下游 tier (kimi 100%, glm5_2 97.5%, minimax 97.0%), 导致 dsv4p_nv ATE 全变 single-tier 无 fallback。降低到 0.05 仅排除真死 (0% SR) function, 保留任何有微弱存活率的 fallback。R982 已验证此模式安全。单参数, 铁律: 只改 HM1 不改 HM2。

## 验证

```bash
# 容器重启后确认
ssh -p 222 opc_uname@100.109.153.83 'docker exec nv_gw env | grep NVU_FALLBACK_HEALTH_THRESHOLD'
# → NVU_FALLBACK_HEALTH_THRESHOLD=0.05 ✓

# 健康检查
ssh -p 222 opc_uname@100.109.153.83 'curl -s http://localhost:40006/health'
# → {"status": "ok"} ✓

# 容器状态
ssh -p 222 opc_uname@100.109.153.83 'docker inspect nv_gw --format "{{.State.Health.Status}}"'
# → healthy ✓

# fallback chain 完整
ssh -p 222 opc_uname@100.109.153.83 "docker logs nv_gw --tail 5 2>&1 | grep 'fallback_chain'"
# → fallback_chain=['kimi_nv', 'dsv4p_nv', 'glm5_2_nv', 'minimax_m3_nv'] ✓
```

## 评判
- 更少报错: dsv4p_nv ATE 时保留下游 tier fallback → 减少 single-tier 无 fallback ATE
- 更快请求: 不影响成功路径延迟 (健康阈值仅影响 ATE 时的 fallback chain 构成)
- 超低延迟: glm5_2_nv integrate, dsv4p_nv pexec, kimi_nv pexec 延迟均不受影响
- 稳定优先: 0.05 保守, 仅排除 0% SR 死 tier, R982 已验证安全

**铁律: 只改 HM1 不改 HM2** ✓

## ⏳ 轮到HM1优化HM2