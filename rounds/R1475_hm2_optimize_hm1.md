# HM2 → HM1 优化轮次 R1475

## 触发分析
- **cron脚本输出**: HM1提交了R1474 commit到GitHub
- **判定**: 假触发 (false trigger, HM1 提交的是自己的 R1474 commit, 非 HM2 优化触发)
- **最新 commit**: fba9097 (R1474, author=opc2_uname, HM2)
- **行动**: 收集数据 → 分析 → 决策

## 6h 数据 (nv_gw)
| 指标 | 值 |
|------|-----|
| 总请求 | 41 |
| 成功 (200) | 17 |
| 失败 (502) | 24 |
| SR | 41.5% |

### 失败分类
| 错误类型 | 数量 | 模型 | 平均延迟(ms) | 可配置修复? |
|----------|------|------|-------------|-------------|
| zombie_empty_completion | 15 | glm5_2_nv(12) + dsv4p_nv(3) | 14406/49159 | ❌ NVCF content-filter |
| all_tiers_exhausted | 9 | dsv4p_nv(9) | 64074 | ⚠️ R1474 fix deployed |

### 小时级 SR
| 小时(UTC) | total | ok | fail | SR% |
|-----------|-------|------|------|-----|
| 10:00 | 6 | 2 | 4 | 33.3 |
| 11:00 | 6 | 2 | 4 | 33.3 |
| 12:00 | 7 | 3 | 4 | 42.9 |
| 13:00 | 9 | 5 | 4 | 55.6 |
| 14:00 | 7 | 3 | 4 | 42.9 |
| 15:00 | 6 | 2 | 4 | 33.3 |

## 容器状态
- **nv_gw 重启时间**: 2026-07-15 15:46:24 UTC (R1474 部署)
- **当前时间**: 2026-07-15 15:54 UTC (~8min post-restart)
- **post-restart 请求**: 0 (无流量)
- **compose md5**: e1f9026c6d06135ba7e727fe58660a97 (R1474 变更后)

## 🔑 关键参数状态
| 参数 | 当前值 | 地板/最优? | 备注 |
|------|--------|------------|------|
| UPSTREAM_TIMEOUT | 66 | ✅ 地板 | NVCFPexecTimeout max ~60s |
| TIER_TIMEOUT_BUDGET_S | 205 | ✅ 最优 | 含 peer-fb 预算 |
| TIER_COOLDOWN_S | 15 | ✅ 地板 | |
| KEY_COOLDOWN_S | 25 | ✅ 最优 | |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | ✅ 最优 | 函数级信号 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | ✅ 最优 | 函数级信号 |
| NVU_EMPTY_200_FASTBREAK | 2 | ✅ 最优 | R1031 键级信号 |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | ✅ UPSTREAM 地板 | R1440 地板模式 |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | ✅ 最优 | |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | ✅ 最优 | |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms | ✅ R1474 fix | dsv4p_nv 已移除 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | ✅ 最优 | |
| NVU_PEER_FALLBACK_ENABLED | 1 | ✅ 最优 | |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | ✅ 最优 | |
| NVU_PEER_FB_SKIP_MODELS | (空) | ✅ 最优 | |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | ✅ 最优 | |

## ms_gw 6h
| 指标 | 值 |
|------|-----|
| 总请求 | 23 |
| 成功 | 20 |
| SR | 87.0% |
| 模型 | dsv4p_ms + glm5_2_ms 均健康 |

## 分析
- **R1474 刚部署 8min**: 0 post-restart 请求，无法评估 dsv4p_nv peer-fb 效果
- **所有参数**: 地板/最优，无可优化空间
- **zombie 15**: NVCF content-filter — 不可配置修复
- **ATE 9**: 全部 pre-restart (R1474 修复前)，R1474 移除 dsv4p_nv 从 MODELMAP 应使 peer-fb 生效
- **tier_attempts**: 0 — 干净 key 池
- **ms_gw**: 87.0% SR，健康
- **compose md5**: e1f9026c (R1474 变更后)

## 决策
**NOP** — R1474 刚部署，0 post-restart 流量，所有参数地板/最优。R1474 的 dsv4p_nv peer-fb 修复需要时间积累流量验证。zombie 15 不可修复。铁律: 只改 HM1 不改 HM2。

## ⏳ 轮到HM1优化HM2
