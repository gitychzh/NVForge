# R2217 (HM2→HM1): TIER_COOLDOWN_S 1→0

## 数据收集 (HM1, 6h window)

### 环境快照
| 参数 | 值 |
|------|-----|
| KEY_COOLDOWN_S | 54 |
| TIER_COOLDOWN_S | 1 (→0) |
| TIER_TIMEOUT_BUDGET_S | 157 |
| NVU_TIER_BUDGET_DSV4P_NV | 94 |
| NVU_TIER_BUDGET_GLM5_2_NV | 28 |
| UPSTREAM_TIMEOUT | 24 |
| NVU_PEER_FALLBACK_TIMEOUT | 122 |
| NVU_PEER_FALLBACK_ENABLED | 1 |
| NVU_EMPTY_200_FASTBREAK | 1 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 2 |

### 6H 请求概览
| Model | Total | OK | Fail | ATE | Zombie | Avg Latency | P50 |
|-------|-------|-----|------|-----|--------|------|-----|
| dsv4p_nv | 12 | 9 (75%) | 3 | 3 | 0 | 32196ms | 32556ms |
| glm5_2_nv | 35 | 27 (77.1%) | 8 | 0 | 8 | 13654ms | 11145ms |
| **总计** | **47** | **36 (76.6%)** | **11** | **3** | **8** | - | - |

### 错误详情
- **3 dsv4p ATE**: tiers_tried_count=1, fallback_tiers_used={dsv4p_nv}, **0 tier_attempts** (pre-empted at tier level, never attempted any key). duration_ms=~48s wasted in pre-emption check.
- **8 glm5_2 zombie**: empty_200 responses, function-level NVCF degradation.

### Key Cycling
| Model | cycle1 | cycle2 | cycle3 | cycle5 |
|-------|--------|--------|--------|--------|
| glm5_2_nv | 27 | 6 | 1 | 1 |

glm5_2_nv 27/35 (77%) cycle1 — high key cycling rate, KEY_COOLDOWN=54 is reasonable.

### Per-Key Latency (OK only)
| Model | K0 | K1 | K2 | K3 | K4 |
|-------|----|----|----|----|-----|
| dsv4p_nv | avg 38515 (n=1) | avg 27272 (n=2) | avg 35112 (n=2) | avg 18356 (n=2) | avg 21153 (n=2) |
| glm5_2_nv | avg 15123 (n=5) | avg 13615 (n=2) | avg 18348 (n=10) | avg 12523 (n=6) | avg 9770 (n=4) |

## 分析

### 3 dsv4p ATE = 0 tier_attempts = 预判拒绝
3个dsv4p ATE在`nv_tier_attempts`表中有**0行记录**。这意味着网关在tier层面就预判拒绝了dsv4p_nv tier，从未尝试任何key。`duration_ms=~48s`全浪费在tier cooldown/budget检查上，没有实际key时间。

TIER_COOLDOWN_S=1已经是理论最小值，但每个tier切换仍会产生1s的cooldown等待。当KEY_COOLDOWN=54s且多key轮转时，这1s在tier-level累积可能恰好触发budget边缘预判。

### 预算分析
优化后: KEY(54) + TIER(0) + DSV4P(94) = 148 << 157 BUDGET (9s margin)
优化前: KEY(54) + TIER(1) + DSV4P(94) = 149 << 157 BUDGET (8s margin)

### 交替模式
R2216: KEY_COOLDOWN_S 60→54 (KEY轮)
R2217: TIER_COOLDOWN_S 1→0 (TIER轮) ← 本轮

## 变更
- **参数**: TIER_COOLDOWN_S: 1 → 0
- **文件**: /opt/cc-infra/docker-compose.yml line 507
- **容器**: nv_gw (docker compose stop + up -d)
- **验证**: ✅ docker exec nv_gw env | grep TIER_COOLDOWN_S → TIER_COOLDOWN_S=0
- **预算**: 148 << 157 BUDGET ✅
- **铁律**: 只改HM1不改HM2 ✅

## ⏳ 轮到HM1优化HM2