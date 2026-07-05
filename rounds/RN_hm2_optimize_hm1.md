# R737: HM2→HM1 — TIER_TIMEOUT_BUDGET_S 110→114 (+4s)

## 改前数据 (6h window, 2026-07-05 09:49–15:49 CST, UPSTREAM=54, BUDGET=110, FASTBREAK=1)

### 总体
| 指标 | 值 |
|------|-----|
| 总请求 | 351 |
| 200 OK | 235 (67.0%) |
| 502 ATE | 116 (33.0%) |

### 按模型
| 模型 | 总请求 | OK | ATE | SR |
|------|--------|-----|-----|-----|
| dsv4p_nv | 266 | 153 | 113 | 57.5% |
| glm5_2_nv | 85 | 82 | 3 | 96.5% |

### 成功请求 dsv4p_nv 耗时分布
| bucket | 请求数 | 含fallback |
|--------|--------|-----------|
| <10s | 15 | 0 |
| 10-20s | 23 | 0 |
| 20-30s | 27 | 0 |
| 30-40s | 16 | 3 |
| 40-50s | 27 | 14 |
| 50-54s | 4 | 1 |
| 54-60s | 12 | 7 |
| >60s | 29 | 26 |

### fallback 成功率
| 模式 | 数量 | avg_dur | max_dur |
|------|------|---------|---------|
| 直接 (dsv4p_nv) | 164 | 21.8s | 80.9s |
| fallback (dsv4p_nv→glm5_2) | 71 | 62.9s | 145.1s |

### ATE 明细
| 模式 | 数量 | avg_dur | 说明 |
|------|------|---------|------|
| 双tier (dsv4p+glm5_2) | 85 | 101.7s | 两个NVCF function都超时 |
| 单tier (dsv4p only) | 29 | 51.5s | fallback被glm5_2 health=0.0阻断 |
| 单tier (glm5_2 only) | 2 | 80.5s | — |

### NVCFPexecTimeout per-key (dsv4p_nv, 6h)
| key | count | avg_ms | max_ms |
|-----|-------|--------|--------|
| k0 | 15 | 33,749 | 54,281 |
| k1 | 16 | 33,209 | 44,408 |
| k2 | 23 | 35,552 | 50,471 |
| k3 | 14 | 35,157 | 54,284 |
| k4 | 13 | 34,603 | 48,254 |

### 关键环境变量
| 参数 | 值 |
|------|-----|
| UPSTREAM_TIMEOUT | 54 |
| TIER_TIMEOUT_BUDGET_S | 110 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 |
| FALLBACK_HEALTH_THRESHOLD | 0.10 |
| NVU_FORCE_STREAM_UPGRADE | 0 |
| NVU_PEER_FALLBACK_TIMEOUT | 45 |

### 日志观察
```
tier_chain=['dsv4p_nv', 'glm5_2_nv'] (dynamic fallback, health={})
→ FALLBACK_GRAPH bidirectional WORKING
[NV-FALLBACK-SUCCESS] Success on fallback tier glm5_2_nv after primary dsv4p_nv failed
→ fallback rescue 正常运作
dsv4p_nv primary function 74f02205 health=0.0 (dead)
→ auto-switch 8915fd28 active, health oscillating
```

## 分析

- dsv4p_nv NVCFPexecTimeout max=54,284ms (k3) — **在 UPSTREAM=54 的绑定边缘** (54s + ~284ms overhead)
- 12 请求在 54-60s 桶中，7 通过 fallback 救回 — 若 UPSTREAM 更高可直接捕获
- BUDGET=110 仅余 2s 安全余量 (54+54=108 vs 110) — 无未来 UPSTREAM +2s 空间
- 29 单tier ATE: fallback 被 glm5_2 function health=0.0 < FALLBACK_HEALTH_THRESHOLD=0.10 阻断
- FASTBREAK=1 已在地板，不可再降
- NVU_FORCE_STREAM_UPGRADE=0 (禁用)，其 timeout 50 无关
- HM2 侧: UPSTREAM=40, BUDGET=72, FASTBREAK=1 — 不对称但不影响 HM1

## 决策: BUDGET 110→114 (+4s)

**不改变 UPSTREAM 的原因**: UPSTREAM=54 绑定边缘但+2s 仅能捕获极少量(54-56s)请求，且 BUDGET 仅余 2s 安全余量。先扩大 BUDGET 创建 headroom 再考虑 UPSTREAM 增量。

+4s = 两个未来 UPSTREAM +2s 轮次的安全余量。每个 tier 最多消耗 54s，BUDGET=114 → 114-54-54=6s 余量，安全。

成功 fallback max=145.1s > 114s，但这是双tier 成功路径 (dsv4p 54s + glm5_2 ~91s)，BUDGET 是 per-tier 预算，不影响此路径。

Worst case: 114s local + 45s peer = 159s < 300s PROXY_TIMEOUT ✓

## 变更: TIER_TIMEOUT_BUDGET_S 110→114 (+4s)

单参数每轮。铁律: 只改HM1不改HM2。

## 验证

```
docker exec nv_gw env | grep TIER_TIMEOUT_BUDGET
→ TIER_TIMEOUT_BUDGET_S=114 ✓
curl http://localhost:40006/health
→ {"status": "ok"} ✓
```

## ⏳ 轮到HM1优化HM2