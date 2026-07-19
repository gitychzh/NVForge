# R1926 (HM2→HM1): NVU_TIER_BUDGET_GLM5_2_NV 40→38 (-2s)

## 数据收集 (6h window, 2026-07-19 14:10 UTC)

### 6h 总览
| 指标 | 值 |
|------|-----|
| 总请求 | 38 |
| 成功 | 26 (68.4% SR) |
| 失败 | 12 |

### 按模型
| 模型 | 总请求 | 成功 | 平均延迟 | 最大延迟 | 错误类型 |
|------|--------|------|----------|----------|----------|
| glm5_2_nv | 32 | 22 | 8757ms | 35687ms | 10 zombie_empty_completion |
| dsv4p_nv | 6 | 4 | 10991ms | 43081ms | 2 phantom ATE (status=200) |

### 错误详情
- glm5_2_nv: 10 zombie_empty_completion, ALL big_input (>115K chars, 128K-141K)
- glm5_2_nv: 22 key_cycle_429s (1-cycle: 20, 2-cycle: 2)
- dsv4p_nv: 2 all_tiers_exhausted but status=200 (phantom, not real failures)
- 0 peer-fallback triggered (peer-fb logs empty)
- 0 SSLEOF errors in logs

### 漂移检查
- NVU_TIER_BUDGET_GLM5_2_NV: compose=40, env=40 ✓ (no drift)
- All other params: compose matches env ✓

## 计划

R1925 将 glm5_2 BUDGET 从 42→40。本轮继续微调：
- **变更**: NVU_TIER_BUDGET_GLM5_2_NV 40→38 (-2s)
- **理由**: OK max=27809ms (R1925 confirmed) << 38s (10s margin safe)
- 所有 10 zombie 都是 big_input，zombie 路径每次节省 2s
- 2s 更接近实测 OK max，但保留 10s 安全余量
- Budget: 30(UPSTREAM) + 122(PEER) = 152 < 153(BUDGET) ✓ (1s margin)
- 单参数；铁律：只改 HM1 不改 HM2

## 执行
- `sed` 编辑 compose: NVU_TIER_BUDGET_GLM5_2_NV: "40" → "38"
- `docker compose up -d nv_gw` → 容器重建，env 确认 38 ✓
- `/health`: status=ok ✓

## 验证
- `docker exec nv_gw env | grep NVU_TIER_BUDGET_GLM5_2_NV`: 38 ✓
- `curl /health`: status=ok, 3 tiers active ✓
- 0 drift: all params match compose ✓
## ⏳ 轮到HM1优化HM2
