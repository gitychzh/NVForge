# R723: HM2→HM1 — UPSTREAM_TIMEOUT 40→42 (+2s)

## 改前数据 (post-restart, 02:14-10:22 UTC, ~8h)

### 总体统计
| 指标 | 数值 |
|------|------|
| 总请求 | 207 |
| 成功 (200) | 148 |
| 失败 (ATE=502) | 59 |
| 总体 SR | 71.5% |

### 按模型
| 模型 | 总请求 | 成功 | 失败 | SR% | avg_ttfb | avg_dur |
|------|--------|------|------|-----|----------|---------|
| dsv4p_nv | 151 | 94 | 57 | 62.3% | 40,849ms | 58,539ms |
| glm5_2_nv | 56 | 54 | 2 | 96.4% | 11,000ms | 13,507ms |

### 最近1h
| 模型 | 总请求 | 成功 | 失败 | SR% |
|------|--------|------|------|-----|
| dsv4p_nv | 174 | 104 | 70 | 59.8% |
| glm5_2_nv | 58 | 56 | 2 | 96.6% |

### ATE 分层 (post-restart, dsv4p_nv)
| tiers_tried | 数量 | avg_dur | fallback_attempted |
|------------|------|---------|-------------------|
| 1 (fallback 未尝试) | 23 | 55,042ms | f (全部) |
| 2 (双tier真正耗尽) | 47 | 93,429ms | — |

### NVCFPexecTimeout 分布 (dsv4p_nv, post-restart 8h)
| nv_key_idx | 次数 | avg_ms | max_ms |
|------------|------|--------|--------|
| 0 | 13 | 32,815 | 40,443 |
| 1 | 12 | 31,085 | 40,418 |
| 2 | 19 | 32,629 | 40,457 |
| 3 | 11 | 31,213 | 36,475 |
| 4 | 11 | 32,475 | 40,381 |

**NVCFPexecTimeout max=40,457ms** — 仍精确绑定 UPSTREAM_TIMEOUT=40（+~457ms overhead）

### dsv4p_nv 成功时长分布 (post-restart, >30s)
| 桶 | 数量 | avg_ttfb |
|----|------|----------|
| 30-35s | 4 | 31,431ms |
| 35-40s | 4 | 36,918ms |
| 40-42s | 4 | 40,913ms |
| 42-45s | 7 | 43,541ms |
| 45-50s | 9 | 47,495ms |
| 50-60s | 15 | 56,246ms |
| >60s | 17 | 73,418ms |

40-42s 桶有 4 次成功，全部 via glm5_2  fallback（avg 63-81s 总耗时）

### FALLBACK_GRAPH 状态 — R710 瞬态消失模式
日志分析确认多次 FALLBACK_GRAPH 瞬态消失 (多模型同时 `(no fallback, 3model)`):
- 03:07-03:19 UTC: 消失 → 自恢复
- 04:28-04:36 UTC: 消失 → 自恢复
- 05:07-05:23 UTC: 消失 → 自恢复
- 06:01+ UTC: 正常 (`dynamic fallback, health={...}`)
- 09:00-10:27 UTC: 持续正常

23 次 single-tier ATE 全部发生在 FALLBACK_GRAPH 消失期间（duration ~60.8s = dsv4p_nv 2-key 耗尽，fallback 未尝试）

### 健康度状态
- dsv4p_nv primary `74f02205`: health 0.0-0.3 振荡（极不健康）
- dsv4p_nv auto-switch `8915fd28`: health ~0.09（接近 FALLBACK_HEALTH_THRESHOLD=0.10 地板）
- glm5_2_nv primary `3b9748d8`: health 0.5-1.0（健康）
- FALLBACK_GRAPH 双向: 当前正常（09:00+ 持续动态 fallback）

## 优化决策

### 参数: UPSTREAM_TIMEOUT 40→42 (+2s)

**依据**:
1. NVCFPexecTimeout max=40,457ms > UPSTREAM_TIMEOUT=40 — 精确绑定，~457ms overhead
2. 40-42s 成功桶有 4 次请求，全部 via glm5_2 fallback（avg 63-81s 总耗时）
3. +2s 可将这些请求从 fallback 路径救回为直接成功，减轻 fallback 负载
4. dsv4p_nv primary  function 不健康（health 0.0-0.3），fallback 链路是救命稻草
5. R710 FALLBACK_GRAPH 瞬态消失不可配置修复，但 fallback 当前正常时，不给它增加不必要负载

### 安全分析
- BUDGET=110 >> 42+42=84s (每 tier 26s 余量)
- FASTBREAK=1 不变 (单 key 快速失败)
- glm5_2_nv fallback SR=96.4% — 安全网健康
- FALLBACK_GRAPH 当前正常（09:00+ 持续）
- 42s 后成功请求大部分 via fallback (avg 60-80s), BUDGET=110 足够

### 时序
- 10:27 UTC: compose 编辑完成
- 10:27 UTC: docker compose up -d nv_gw (容器重建)
- 10:27 UTC: 容器恢复，UPSTREAM_TIMEOUT=42 生效
- health check: OK

## 容器状态
- 容器: nv_gw (healthy)
- UPSTREAM_TIMEOUT: 42 (NEW)
- TIER_TIMEOUT_BUDGET_S: 110
- KEY_COOLDOWN_S: 25
- TIER_COOLDOWN_S: 25
- FASTBREAK: 1
- FALLBACK_HEALTH_THRESHOLD: 0.10

## 铁律
- 单参数每轮 ✓
- 改前必有数据 ✓
- 改后必有验证 ✓
- 只改 HM1 不改 HM2 ✓

## ⏳ 轮到HM1优化HM2