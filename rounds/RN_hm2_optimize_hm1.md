# R734: HM2→HM1 — NVU_FORCE_STREAM_UPGRADE_TIMEOUT 44→50 (+6s)

## TL;DR
6h: 334req/222OK(66.5%)/112ATE(33.5%). dsv4p_nv SR 56.5% (primary bottleneck), glm5_2_nv SR 96.5% (healthy fallback). R733 bumped UPSTREAM 48→50 but left NVU_FORCE_STREAM_UPGRADE_TIMEOUT at 44 — drift correction. Aligns with UPSTREAM=50. BUDGET=110>>50 safe. FASTBREAK=1 unchanged. Single param per round; iron rule: only change HM1 never HM2.

单参数少改多轮。铁律：只改 HM1 不改 HM2。

---

## 一、当前配置快照（R734, pre-change）

| 参数 | 值 | 说明 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 50 | R733 +2s |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 44 | R727 aligned with UPSTREAM=44, now 6s behind |
| TIER_TIMEOUT_BUDGET_S | 110 | per-tier budget |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | 1 key attempt before fallback |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | floor (R708 fix) |
| KEY_COOLDOWN_S | 25 | standard |
| TIER_COOLDOWN_S | 25 | standard |
| NVU_PEER_FALLBACK_ENABLED | 1 | enabled |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | standard |

## 二、6h 数据（2026-07-05 01:03–14:33 UTC）

### 总体
| 指标 | 值 |
|------|-----|
| 总请求 | 334 |
| 成功 (200) | 222 (66.5%) |
| ATE (502) | 112 (33.5%) |
| 其他错误 | 0 |
| 数据窗口 | 01:03–14:33 UTC |

### 每小时 SR
| 小时 (UTC) | 请求 | OK | ATE | SR% |
|-----------|------|-----|-----|-----|
| 01:00 | 13 | 8 | 5 | 61.5 |
| 02:00 | 49 | 35 | 14 | 71.4 |
| 03:00 | 27 | 20 | 7 | 74.1 |
| 04:00 | 21 | 14 | 7 | 66.7 |
| 05:00 | 20 | 7 | 13 | 35.0 |
| 06:00 | 29 | 22 | 7 | 75.9 |
| 07:00 | 24 | 21 | 3 | 87.5 |
| 08:00 | 23 | 13 | 10 | 56.5 |
| 09:00 | 21 | 17 | 4 | 81.0 |
| 10:00 | 26 | 12 | 14 | 46.2 |
| 11:00 | 18 | 12 | 6 | 66.7 |
| 12:00 | 30 | 17 | 13 | 56.7 |
| 13:00 | 27 | 18 | 9 | 66.7 |
| 14:00 | 6 | 6 | 0 | 100.0 |

### 按模型 SR
| 模型 | 请求 | OK | SR% |
|------|------|-----|-----|
| dsv4p_nv | 248 | 140 | 56.5 |
| glm5_2_nv | 85 | 82 | 96.5 |
| kimi_nv | 1 | 0 | 0.0 |

### ATE 诊断
| tiers_tried_count | 数量 | avg_dur | 解读 |
|-------------------|------|---------|------|
| 1 | 35 (31.3%) | 51,733ms | 单 tier 耗尽，fallback 未尝试（全部 pre-restart） |
| 2 | 77 (68.7%) | 101,695ms | 双 tier 都耗尽，NVCF upstream |

#### 单 tier ATE 详情
- start_tier_idx=0 (kimi_nv): 1 个
- start_tier_idx=1 (dsv4p_nv): 32 个, avg 51,466ms
- start_tier_idx=3 (glm5_2_nv): 2 个
- **全部 fallback_actually_attempted=f** → pre-restart 容器，fallback 未部署

### nv_tier_attempts 分析
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

- k2 max=48,422ms = UPSTREAM=48 + 422ms → R733 前绑定
- UPSTREAM=50 后（R733）可捕获 48-50s 范围

### 成功请求 fallback 统计
| fallback_occurred | 数量 | avg_dur | max_dur |
|-------------------|------|---------|---------|
| f (无 fallback) | 155 | 21,471ms | 80,892ms |
| t (触发 fallback) | 67 | 61,364ms | 145,104ms |

### 容器状态
- nv_gw: Up 10 minutes (pre-change), restarted at 14:23 UTC
- tier_chain=['dsv4p_nv', 'glm5_2_nv'] (dynamic fallback, health={}) — 刚重启，MIN_SAMPLES 未积累
- 双向 fallback 正常工作
- 14:33 UTC 出现 8 个 DNS 临时解析失败 (gaierror) — HM1 直连间歇性网络问题，非配置可修复

### 日志关键发现
- NV-STARTUP-RETRY: 14:33 UTC DNS 错误后自动重试成功
- 容器重启后 MIN_SAMPLES 保护期，health 值尚未显示
- glm5_2_nv SR 96.5% — 健康 fallback，远优于 R733 周期（health 0.125-0.273）

## 三、决策分析

### 为什么改 NVU_FORCE_STREAM_UPGRADE_TIMEOUT

1. **Drift correction**: R733 将 UPSTREAM_TIMEOUT 从 48→50，但未同步更新 NVU_FORCE_STREAM_UPGRADE_TIMEOUT（仍为 44，自 R727 与 UPSTREAM=44 对齐后未更新）。
   - 当 thinking-detected streaming 请求触发 extended timeout 时，`NVU_FORCE_STREAM_UPGRADE_TIMEOUT=44` 会先于 `UPSTREAM=50` 到期
   - 两端不对称：pexec 路径 50s，thinking-stream 路径仅 44s
   - 对齐到 50 消除此不对称

2. **glm5_2_nv 状态显著改善**: R733 周期 glm5_2_nv health 0.125-0.273（非常不健康），但当前周期 SR 96.5%（85/82 OK）。Fallback 不再脆弱，允许直接路径更长的 timeout。

3. **BUDGET 余量充足**: BUDGET=110 >> 50s safe。Streaming 请求触发 extended timeout 后仍远在预算内。

4. **历史先例**: R727 做了完全相同的事（FORCE_STREAM 42→44 对齐 UPSTREAM=44）。R733 触发新一轮 drift，需新一轮对齐。

### 为什么不是其他参数
- UPSTREAM_TIMEOUT=50: 刚改（R733），需观察新值效果
- TIER_TIMEOUT_BUDGET_S=110: 余量充足
- FASTBREAK=1: glm5_2_nv SR 96.5% fallback 健康，无需增加 key 尝试
- KEY_COOLDOWN_S=25: 无 429 问题
- FALLBACK_HEALTH_THRESHOLD=0.10: 已是地板

## 四、变更

**参数**: NVU_FORCE_STREAM_UPGRADE_TIMEOUT: 44 → 50 (+6s)

**理由**: Drift correction — aligns with UPSTREAM=50 (R733). R727 aligned at 44 with UPSTREAM=44; R733 bumped UPSTREAM to 50 left FORCE_STREAM at 44. Prevents asymmetric timeout between pexec path (50s) and thinking-stream path (44s).

**安全验证**:
- BUDGET=110 >> 50s ✓
- FASTBREAK=1 unchanged ✓
- YAML 验证通过 ✓
- 容器重启成功 (Recreated) ✓
- Health check: OK ✓
- `docker exec nv_gw env | grep NVU_FORCE_STREAM_UPGRADE_TIMEOUT` → 50 ✓

## 五、验证结果
- compose YAML: OK
- `docker compose up -d nv_gw`: Container nv_gw Recreated → Started
- `curl localhost:40006/health`: {"status": "ok"}
- `docker exec nv_gw env | grep NVU_FORCE_STREAM_UPGRADE_TIMEOUT`: NVU_FORCE_STREAM_UPGRADE_TIMEOUT=50

## ⏳ 轮到HM1优化HM2