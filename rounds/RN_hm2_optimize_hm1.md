# R726: HM2→HM1 — UPSTREAM_TIMEOUT 42→44 (+2s)

## 数据收集 (2026-07-05 ~11:30 UTC)

### 容器状态
- 容器: nv_gw, Up 30 minutes (healthy)
- 重启后: UPSTREAM_TIMEOUT=44 ✓

### 6h DB 聚合
| 指标 | 值 |
|------|-----|
| 总请求 | 144 |
| OK (200) | 97 (67.4%) |
| 失败 (ATE) | 47 (32.6%) |
| 平均成功延迟 | 30,236ms |
| 最大成功延迟 | 71,833ms |
| total key_cycle_429s | 42 |

### Per-model 6h
| Model | cnt | OK | fail | SR | avg_ok_ms | avg_fail_ms |
|-------|-----|-----|------|------|-----------|-------------|
| dsv4p_nv | 106 | 60 | 46 | 56.6% | 36,335 | 74,067 |
| glm5_2_nv | 37 | 37 | 0 | 100% | 20,345 | - |

### ATE 诊断
- tiers_tried_count=1: 9 ATEs (avg 42,328ms, start_tier_idx=1 dsv4p_nv)
- tiers_tried_count=2: 37 ATEs (avg 81,787ms)
- 1h health view: dsv4p_nv 48.9% (66 OK / 69 fail), glm5_2_nv 97.8% (88 OK / 2 fail)

### nv_tier_attempts (失败记录)
| tier | error_type | cnt | avg_ms | max_ms |
|------|-----------|-----|--------|--------|
| dsv4p_nv | NVCFPexecTimeout | 32 | 36,010 | 40,457 |
| glm5_2_nv | NVCFPexecTimeout | 10 | 41,269 | **42,309** |

### 关键发现
- **glm5_2_nv NVCFPexecTimeout max=42,309ms > UPSTREAM=42 → binding constraint**
- dsv4p_nv NVCFPexecTimeout max=40,457ms, gap=1,543ms (also near binding)
- 9 single-tier ATEs: avg 42,328ms, glm5_2 health=0.0 at sampling time blocked fallback
- 37 double-tier ATEs: genuine NVCF upstream dual exhaustion
- FALLBACK_GRAPH bidirectional working, fallback 100% SR (40/40)
- glm5_2 primary 3b9748d8 health 0.0-0.25 (unstable), dsv4p_nv 74f02205 1.0→0.667 (declining)
- Duration buckets: 30 ATEs >72s (double-tier exhaustion), 7 at 60-72s, 9 at 42-50s (single-tier)

## 优化决策

**变更**: UPSTREAM_TIMEOUT 42→44 (+2s)

**依据**:
1. glm5_2_nv NVCFPexecTimeout max=42,309ms 超过当前 UPSTREAM=42，导致不必要的 tier 级失败 → 级联 fallback
2. +2s 捕获 42-44s 边缘窗口，直接成功而非通过 fallback
3. 减少 fallback 负载，保护 dsv4p_nv（74f02205 health 1.0→0.667 下降中）
4. BUDGET=110 >> 44+44=88s safe（per-tier budget, R707 corrected）
5. FASTBREAK=1 unchanged（基于 R709 教训，NVCF 双 function 不稳定时期不增加 key 尝试次数）

**风险评估**: 低风险。BUDGET 余量 22s (110-88)，成功路径最大 71,833ms << 88s。无新增风险。

**单参数每轮；铁律: 只改HM1不改HM2**

## 验证
- `docker ps`: nv_gw Up (healthy) ✓
- `docker exec nv_gw env | grep UPSTREAM_TIMEOUT`: 44 ✓
- `docker logs --tail 20`: clean start, no errors ✓
- compose 行 483: `UPSTREAM_TIMEOUT: "44"` ✓

## 参数状态 (post-R726)
| 参数 | 值 | 趋势 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 44 | 30→25→28→31→34→32→30→36→38→40→42→44 |
| TIER_TIMEOUT_BUDGET_S | 110 | - |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | - |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 42 | - |
| KEY_COOLDOWN_S | 25 | - |
| TIER_COOLDOWN_S | 25 | - |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor (integrate无模型) |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | - |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | - |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | floor |

## ⏳ 轮到HM1优化HM2