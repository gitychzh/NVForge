# R724: HM2→HM1 — NVU_FORCE_STREAM_UPGRADE_TIMEOUT 40→42 (+2s)

## 改前数据 (6h window, ~04:50-10:50 UTC)

### 总体统计
| 指标 | 数值 |
|------|------|
| 总请求 | 301 |
| 成功 (200) | 199 |
| 失败 (ATE=502) | 102 |
| 总体 SR | 66.1% |

### 按小时 SR
| 小时 (UTC) | 总请求 | 成功 | ATE | SR% |
|-----------|--------|------|-----|-----|
| 04:00 | 21 | 14 | 7 | 66.7% |
| 05:00 | 20 | 7 | 13 | 35.0% |
| 06:00 | 29 | 22 | 7 | 75.9% |
| 07:00 | 24 | 21 | 3 | 87.5% |
| 08:00 | 23 | 13 | 10 | 56.5% |
| 09:00 | 21 | 17 | 4 | 81.0% |
| 10:00 | 18 | 10 | 8 | 55.6% |

### ATE 分层
| tiers_tried | 数量 | avg_dur | 说明 |
|------------|------|---------|------|
| 1 (fallback 未尝试) | 53 | 48,845ms | 49 dsv4p_nv + 4 glm5_2 + 1 kimi |
| 2 (双tier真正耗尽) | 49 | 93,077ms | 双tier均失败 |

### 单层 ATE (start_tier_idx)
| start_tier_idx | 数量 | avg_dur | fallback_attempted |
|---------------|------|---------|-------------------|
| 1 (dsv4p_nv) | 49 | 49,669ms | f (全部, peer-originated hop=1) |
| 3 (glm5_2_nv) | 5 | 47,377ms | f |
| 0 (kimi_nv) | 1 | 2,682ms | f |

### NVCFPexecTimeout (nv_tier_attempts, 6h)
| tier | 次数 | avg_elapsed | max_elapsed |
|------|------|------------|-------------|
| dsv4p_nv | 69 | 32,048ms | 40,492ms |
| glm5_2_nv | 16 | 34,319ms | 40,297ms |

dsv4p_nv max=40,492ms < UPSTREAM_TIMEOUT=42 (R723) — UPSTREAM 不再绑定，NVCF 函数级 timeout

### R710 FALLBACK_GRAPH 瞬态消失 — 当前激活
日志分析确认 dsv4p_nv fallback 在 10:38:20 UTC 消失:
- 10:33-10:37: `tier_chain=['dsv4p_nv', 'glm5_2_nv']` (dynamic fallback, `3b9748d8` health=0.0)
- **10:38:20**: `tier_chain=['dsv4p_nv']` (no fallback, 3model) — FALLBACK_GRAPH 消失
- 10:38-10:51: 持续 14+ min 无 fallback，所有 dsv4p_nv single-tier ATE 均为 peer-originated hop=1

### 健康度状态
- dsv4p_nv primary `74f02205`: health 0.0-1.0 振荡（auto-switch 到 `8915fd28`）
- glm5_2_nv primary `3b9748d8`: health 0.0（完全死掉，NVCF INACTIVE）
- FALLBACK_GRAPH 双向: dsv4p_nv→glm5_2_nv 消失（10:38+），glm5_2_nv→dsv4p_nv 正常（最后可见 10:34）

## 优化决策

### 参数: NVU_FORCE_STREAM_UPGRADE_TIMEOUT 40→42 (+2s)

**依据**:
1. R723 将 UPSTREAM_TIMEOUT 提到 42s，FORCE_STREAM_UPGRADE_TIMEOUT 仍为 40s
2. 不对称：thinking 请求可能在 40s 被 stream upgrade timeout 截断，但 upstream 还允许到 42s
3. 对齐到 42s 消除这个 2s 缺口，让 thinking 请求充分使用 upstream 余量
4. 容器重启附带修复 R710 FALLBACK_GRAPH 瞬态消失（Python 运行时模块重载）

### 安全分析
- BUDGET=110 >> 42+42=84s (每 tier 26s 余量)
- FASTBREAK=1 不变
- UPSTREAM_TIMEOUT=42 已在 R723 验证
- 容器重启后 MIN_SAMPLES 保护期新启用，glm5_2_nv 短暂进入 fallback 链

### 时序
- 10:51 UTC: compose 编辑完成
- 10:51 UTC: docker compose up -d nv_gw (容器重建)
- 10:52 UTC: 容器恢复，NVU_FORCE_STREAM_UPGRADE_TIMEOUT=42 生效
- health check: OK

## 容器状态
- 容器: nv_gw (healthy)
- UPSTREAM_TIMEOUT: 42
- NVU_FORCE_STREAM_UPGRADE_TIMEOUT: 42 (NEW)
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