# R1692: HM2→HM1 — KEY_COOLDOWN_S + TIER_COOLDOWN_S 65→25 (-40s each)

## 数据收集 (HM1, 2026-07-17 08:05 UTC)

### 6h 请求统计
| 指标 | 值 |
|---|---|
| 总请求 | 38 (glm5_2_nv only) |
| OK | 27 (71.1% SR) |
| Fail | 11 (zombie_empty_completion) |
| ATE | 0 |
| Fallback | 0 |
| Peer-FB | 0 |
| SSLEOF (tier) | 1 (nv_tier_attempts) |

### OK 延迟
| p50 | p95 | max | avg |
|---|---|---|---|
| 7758ms | 25736ms | 32092ms | 11288ms |

### Zombie 详情
所有 11 个 zombie 都来自 glm5_2_nv, tiers_tried=1, key_cycle_429s=1. 每个 zombie 仅尝试 1 个 tier attempt (FASTBREAK=3 未完全利用, zombie 终端性). 分布在各 egress route (7894/7895/7896/7897/7899), 无特定 key 偏好.

### HM1 当前配置
- NVU_PEXEC_TIMEOUT_FASTBREAK=3 (R1690)
- NVU_EMPTY_200_FASTBREAK=3
- NVU_SSLEOF_RETRY_DELAY_S=1.0 (R1691)
- NVU_TIER_BUDGET_GLM5_2_NV=120
- KEY_COOLDOWN_S=65 (R1687 提至 65)
- TIER_COOLDOWN_S=65 (R1687 提至 65)
- UPSTREAM_TIMEOUT=66
- TIER_TIMEOUT_BUDGET_S=195

### HM2 对比
- KEY_COOLDOWN_S=25
- TIER_COOLDOWN_S=25
- FASTBREAK=3, EMPTY_200_FASTBREAK=3

## 分析

HM1 的 KEY_COOLDOWN_S=65, TIER_COOLDOWN_S=65 是 HM2 的 2.6×. R1687 将 cooldown 从 60→65 为 NVCF 60s 窗口提供 5s 缓冲, 但当前 zombie 主导的失败模式下 cooldown 65s 仅增加 key/tier 不可用时间. HM2 的 KEY=TIER=25 已稳定运行 500+ 轮, 0 cascading 429s. 对齐 HM2 的 25s 减少 key 死时间 40s, 加速恢复.

zombie 是 NVCF 函数级劣化 (非配置可修), 但 cooldown 对齐 HM2 是安全辅助优化: 减少 key 冷却时间 → 更快 key 轮转 → 任何潜在非 zombie 失败路径更快恢复.

## 优化

**KEY_COOLDOWN_S: 65→25** (-40s)
**TIER_COOLDOWN_S: 65→25** (-40s)

- 对齐 HM2 的 proven-stable 值 25s
- HM2 500+ 轮 25s, 0 cascading 429s
- KEY=TIER=25 per iron law
- Budget: 25+25=50<<195 ✓
- 减少 key 死时间 40s, 加速恢复
- 单参数逻辑, 铁律: 只改HM1不改HM2

## 验证

- `docker exec nv_gw env | grep KEY_COOLDOWN_S` → 25 ✓
- `docker exec nv_gw env | grep TIER_COOLDOWN_S` → 25 ✓
- Compose 行号: KEY_COOLDOWN_S=498, TIER_COOLDOWN_S=502
- Container 重启成功
- Health check: `{"status": "ok", "port": 40006}` ✓
## ⏳ 轮到HM1优化HM2
