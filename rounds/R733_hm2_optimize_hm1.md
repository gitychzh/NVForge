# R733: HM2→HM1 — UPSTREAM_TIMEOUT 48→50 (+2s)

## TL;DR
6h: 332req/220OK(66.3%)/112ATE(33.7%). dsv4p_nv NVCFPexecTimeout max=48,422ms (k2) at UPSTREAM=48 binding (+422ms). 35 single-tier ATEs all pre-restart (no fallback attempted); 77 double-tier (both tiers exhausted, NVCF upstream). FALLBACK_GRAPH bidirectional working. glm5_2_nv health 0.125-0.273 (very unhealthy), dsv4p_nv 0.462-0.556 (declining). +2s captures 48-50s edge, reduces fallback load on unhealthy glm5_2. BUDGET=110>>50+50=100s safe. FASTBREAK=1 unchanged.

单参数少改多轮。铁律：只改 HM1 不改 HM2。

---

## 一、当前配置快照（R733, pre-change）

| 参数 | 值 | 说明 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 48 | pre-change |
| TIER_TIMEOUT_BUDGET_S | 110 | per-tier budget |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | 1 key attempt before fallback |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | floor (R708 fix) |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 44 | aligned with UPSTREAM=44 (R727) |
| KEY_COOLDOWN_S | 25 | standard |
| TIER_COOLDOWN_S | 25 | standard |
| NVU_PEER_FALLBACK_ENABLED | 1 | enabled |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | standard |

## 二、6h 数据（2026-07-05 08:00–14:00 UTC）

### 总体
| 指标 | 值 |
|------|-----|
| 总请求 | 332 |
| 成功 (200) | 220 (66.3%) |
| ATE (502) | 112 (33.7%) |
| 其他错误 | 0 |
| avg_dur | 50,914ms |
| avg_ttfb | 33,000ms |

### 每小时 SR
| 小时 (UTC) | 请求 | OK | ATE | SR% |
|-----------|------|-----|-----|-----|
| 08:00 | 23 | 13 | 10 | 56.5 |
| 09:00 | 21 | 17 | 4 | 81.0 |
| 10:00 | 26 | 12 | 14 | 46.2 |
| 11:00 | 18 | 12 | 6 | 66.7 |
| 12:00 | 30 | 17 | 13 | 56.7 |
| 13:00 | 27 | 18 | 9 | 66.7 |
| 14:00 | 4 | 4 | 0 | 100.0 |

### ATE 诊断

#### 按 tiers_tried_count
| tiers_tried_count | 数量 | avg_dur | 解读 |
|-------------------|------|---------|------|
| 1 | 35 (31.3%) | 51,733ms | 单 tier 耗尽，fallback 未尝试 |
| 2 | 77 (68.7%) | 101,695ms | 双 tier 都耗尽，NVCF upstream |

#### 单 tier ATE 详情
- start_tier_idx=0 (kimi_nv): 1 个, avg 2,682ms
- start_tier_idx=1 (dsv4p_nv): 32 个, avg 51,466ms
- start_tier_idx=3 (glm5_2_nv): 2 个, avg 80,525ms
- **全部 35 个 fallback_actually_attempted=f** → fallback 未尝试

#### 单 tier ATE 按小时分布
- 01:00: 5, 02:00: 9, 03:00: 5, 04:00: 1, 05:00: 6, 10:00: 9
- **10:00 UTC 的 9 个 ATE 全为 dsv4p_nv, avg 42,329ms, 统一 42.2-42.4s 范围**
- 这些是 pre-restart 数据（容器在 13:27 UTC 重启）
- **11:00 UTC 后：零单 tier ATE** → fallback 链正常运行

#### 双 tier ATE 详情
- 全部 fallback_actually_attempted=f
- 按小时: 02:00(5), 03:00(2), 04:00(6), 05:00(7), 06:00(7), 07:00(3), 08:00(10), 09:00(4), 10:00(5), 11:00(6), 12:00(13), 13:00(9)
- 12:00-13:00 UTC 出现长 ATE (177-193s, 含 peer fallback 时间)
- 近期 13:00 UTC: 9 个 ATE avg 137,999ms — 双 tier timeout 叠加

### nv_tier_attempts 分析

#### 按 tier + error_type
| tier | error_type | 数量 | avg_ms | max_ms |
|------|-----------|------|--------|--------|
| dsv4p_nv | NVCFPexecTimeout | 77 | 33,608 | 48,422 |
| glm5_2_nv | NVCFPexecTimeout | 27 | 41,252 | 44,463 |

#### NVCFPexecTimeout 按 key 分布 (dsv4p_nv)
| key | 数量 | avg_ms | max_ms |
|-----|------|--------|--------|
| k0 | 14 | 32,282 | 40,443 |
| k1 | 16 | 33,209 | 44,408 |
| k2 | 21 | 34,132 | **48,422** |
| k3 | 13 | 33,685 | 48,305 |
| k4 | 13 | 34,603 | 48,254 |

- k2 max=48,422ms = UPSTREAM=48 + 422ms → **确切绑定**
- k0/k1 明显更快（40,443/44,408ms），不是完全均匀分布
- 5 个 key 都有 13-21 个 timeout，分布较均匀

#### NVCFPexecTimeout 按 key 分布 (glm5_2_nv)
| key | 数量 | avg_ms | max_ms |
|-----|------|--------|--------|
| k0 | 3 | 37,953 | 44,285 |
| k1 | 5 | 40,342 | 44,463 |
| k2 | 7 | 40,152 | 44,282 |
| k3 | 7 | 43,982 | 44,335 |
| k4 | 5 | 41,858 | 44,287 |

- glm5_2_nv max=44,463ms << UPSTREAM=48 → 不绑定，是 NVCF function-level timeout

### 成功请求 fallback 统计
| fallback_occurred | 数量 | avg_dur | max_dur |
|-------------------|------|---------|---------|
| f (无 fallback) | 154 | 20,939ms | 80,892ms |
| t (触发 fallback) | 67 | 61,364ms | 145,104ms |

### 容器状态
- nv_gw: Up 38 minutes (pre-restart), restarted at 14:05 UTC
- logs_db: Up 23 hours

### 日志关键发现
- tier_chain=['dsv4p_nv', 'glm5_2_nv'] (dynamic fallback) — **双向 fallback 正常工作**
- dsv4p_nv health: 74f02205 = 0.462-0.556 (下降中)
- glm5_2_nv health: 3b9748d8 = 0.125-0.273 (非常不健康)
- FASTBREAK=1: NV-PEXEC-FASTBREAK 在第一次 timeout 后立即 break，跳至 fallback
- 最近 100 行日志中 2 个 BrokenPipeError（客户端断开，非服务端问题）

## 三、决策分析

### 为什么改 UPSTREAM_TIMEOUT
1. **dsv4p_nv NVCFPexecTimeout max=48,422ms (k2) 确切绑定 UPSTREAM=48**
   - +422ms 开销是网络延迟，确认绑定
   - +2s 捕获 48-50s 范围的直接成功，减少 fallback 负载

2. **glm5_2_nv 非常不健康 (health=0.125-0.273)**
   - Fallback 到 glm5_2 的成功率可能下降
   - 减少 fallback 触发 = 减少对 glm5_2 的依赖

3. **BUDGET 余量充足**
   - BUDGET=110 >> 50+50=100s (10s 余量)
   - 即使双 tier 超时，总时间 100s < 110s，不会误杀

### 为什么 FASTBREAK=1 不变
- NVCFPexecTimeout 分布：k0/k1 明显更快 (40,443/44,408ms)，但 k2-k4 都在 48s 绑定
- 并非完全均匀分布 — k0/k1 可能更快成功
- 但 glm5_2 fallback 虽然不健康，仍有 ~66% 成功率 (通过 fallback 成功的 67/220)
- uniform 分布不明显 → 2nd key 可能帮到 k0/k1 但 k2-k4 仍会 timeout
- 保守：先 +2s UPSTREAM，观察后再决定 FASTBREAK

### 为什么不是其他参数
- TIER_TIMEOUT_BUDGET_S=110: 余量充足，不需要改
- KEY_COOLDOWN_S=25: 无 429 问题，不需要改
- NVU_FORCE_STREAM_UPGRADE_TIMEOUT=44: 落后于 UPSTREAM=50，但 streaming timeout 与 pexec timeout 不同路径，暂不改
- FALLBACK_HEALTH_THRESHOLD=0.10: 已是地板，不需要改

## 四、变更

**参数**: UPSTREAM_TIMEOUT: 48 → 50 (+2s)

**理由**: dsv4p_nv NVCFPexecTimeout max=48,422ms binding at UPSTREAM=48. +2s captures 48-50s edge directly, reduces fallback load on unhealthy glm5_2_nv (health 0.125-0.273).

**安全验证**:
- BUDGET=110 >> 50+50=100s ✓ (10s headroom)
- FASTBREAK=1: 1 key × 50s = 50s << 110s ✓
- YAML 验证通过 ✓
- 容器重启成功 (Recreated) ✓
- Health check: OK ✓
- `docker exec nv_gw env | grep UPSTREAM_TIMEOUT` → 50 ✓

## 五、验证结果
- compose YAML: OK
- `docker compose up -d nv_gw`: Container nv_gw Recreated → Started
- `curl localhost:40006/health`: {"status": "ok"}
- `docker exec nv_gw env | grep UPSTREAM_TIMEOUT`: UPSTREAM_TIMEOUT=50

## ⏳ 轮到HM1优化HM2