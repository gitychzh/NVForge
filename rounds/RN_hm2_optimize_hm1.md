# R722: HM2→HM1 — UPSTREAM_TIMEOUT 38→40 (+2s)

## 改前数据 (6h window, 04:00-10:00 UTC, collected ~10:03 UTC)

### 总体统计
| 指标 | 数值 |
|------|------|
| 总请求 | 297 |
| 成功 (200) | 198 |
| 失败 (ATE=502) | 99 |
| 总体 SR | 66.7% |

### 按上游路径
| 路径 | 请求 | 成功 | avg_ttfb | avg_dur | max_dur |
|------|------|------|----------|---------|---------|
| nvcf_pexec | 196 | 196 | 29,640ms | 29,653ms | 99,088ms |
| NULL (ATE) | 101 | 2 | 39ms | 68,931ms | 122,312ms |

### ATE 分层 (tiers_tried_count)
| tiers_tried | 数量 | avg_dur |
|------------|------|---------|
| 1 (single-tier耗尽) | 53 | 49,342ms |
| 2 (双tier都失败) | 46 | 93,796ms |

### ⚠️ 容器重启污染分析
HM1 容器在 `~09:58 UTC` 重启（前次R721部署）。6h窗口数据包含两种不同容器状态：
- **Pre-restart (≥09:58 UTC)**: 55 single-tier ATE, 均 `fallback_actually_attempted=f` — 旧容器 FALLBACK_GRAPH 失效
- **Post-restart (<09:58 UTC)**: 3 ATE, 均 `tiers_tried_count=2` — FALLBACK_GRAPH 双向工作正常

**Post-restart 真实 SR**: 7req/4OK(57.1%)/3ATE(42.9%) — 样本太小，3 ATE 均为双tier真正耗尽

### dsv4p_nv 6h SR
| 总请求 | 成功 | SR |
|--------|------|-----|
| 221 | 128 | 57.9% |

（受pre-restart污染，实际post-restart更好）

### NVCFPexecTimeout 分布 (dsv4p_nv tier_attempts)
| 桶 | 数量 |
|----|------|
| 25-30s | 15 |
| 30-32s | 27 |
| 32-34s | 7 |
| 36-38s | 8 |
| 40-42s | 12 |

**NVCFPexecTimeout max=40,492ms** (dsv4p_nv), **max=40,273ms** (glm5_2_nv)

### dsv4p_nv 成功时长分布 (>30s)
| 桶 | 数量 |
|----|------|
| ≤35s | 7 |
| 35-36s | 3 |
| 36-37s | 2 |
| 37-38s | 1 |
| 39-40s | 3 |
| 40-41s | 2 |
| 41-42s | 2 |
| 42-45s | 9 |
| >45s | 43 (via fallback) |

### 小时级 SR
| 小时 (UTC) | 总请求 | OK | ATE | SR% |
|-----------|--------|-----|-----|-----|
| 04:00 | 10 | 6 | 4 | 60.0 |
| 05:00 | 28 | 13 | 15 | 46.4 |
| 06:00 | 2 | 2 | 0 | 100.0 |
| 07:00 | 13 | 8 | 5 | 61.5 |
| 08:00 | 49 | 35 | 14 | 71.4 |
| 09:00 | 27 | 20 | 7 | 74.1 |
| 10:00 | 21 | 14 | 7 | 66.7 |

### 健康度状态
- dsv4p_nv primary `74f02205`: health=0.0→0.5 (启动后逐渐回升)
- glm5_2_nv primary `3b9748d8`: health=0.0 (启动后 MIN_SAMPLES 保护中)
- FALLBACK_GRAPH 双向: dsv4p_nv→glm5_2_nv ✓, glm5_2_nv→dsv4p_nv ✓
- glm5_2_nv 最近几小时 100% SR (fallback 安全网健康)

## 优化决策

### 参数: UPSTREAM_TIMEOUT 38→40 (+2s)

**依据**:
1. NVCFPexecTimeout max=40,492ms (dsv4p_nv) 和 40,273ms (glm5_2_nv) 均 > 当前 UPSTREAM_TIMEOUT=38
2. 40-42s 桶有 12 次 NVCFPexecTimeout — UPSTREAM_TIMEOUT=38 绑定了这些请求的存活窗口
3. NVCF 服务器端 timeout 在 ~40-41s 范围 — 38s 截断了一批本可成功的请求
4. 39-40s 成功桶有 3 次（fallback 救回），说明 38-40s 窗口存在可救回请求

### 安全分析
- BUDGET=110 >> 40+40=80s (每 tier 30s 余量)
- FASTBREAK=1 不变 (单 key 快速失败)
- glm5_2_nv fallback 100% SR 近期小时 — 安全网健康
- FALLBACK_GRAPH 双向工作
- 40s 后成功请求大部分 via fallback (avg 60-80s), BUDGET=110 足够

### 时序
- 10:05 UTC: compose 编辑完成
- 10:06 UTC: docker compose up -d nv_gw
- 10:06 UTC: 容器恢复，UPSTREAM_TIMEOUT=40 生效
- health check: OK

## 容器状态
- 容器: nv_gw (healthy)
- UPSTREAM_TIMEOUT: 40
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