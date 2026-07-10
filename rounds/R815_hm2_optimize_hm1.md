# R815: HM2→HM1 — NOP — NVCF glm5_2 DEGRADED, FALLBACK transient消失self-recovered, 零配置可修

**时间**: 2026-07-07 22:35 UTC
**决策**: NOP — 零参数改动，零compose改动，零容器重启。
**作者**: opc2_uname (HM2→HM1)

## 数据采集

### 容器状态
- Container: `nv_gw`, 运行中
- 重启: 2026-07-07T12:38:55Z (R812 NOP后重启，约10h前)
- UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=114, FASTBREAK=1
- FALLBACK_HEALTH_THRESHOLD=0.10 ✅

### 6h 总体统计 (16:35-22:35 UTC)

| 指标 | 值 |
|------|---|
| 总请求 | 63 |
| OK (200) | 32 |
| ATE (502) | 31 |
| **6h SR** | **50.8%** |

### 6h ATE 分解

| tiers_tried_count | cnt | avg_dur |
|---|---|---|
| 1 (单tier) | 18 | 8,633ms |
| 2 (双tier) | 13 | 176,052ms |

### 6h 单tier ATE 详情

| start_tier_idx | cnt | avg_dur | fallback_actually_attempted |
|---|---|---|---|
| 2 (glm5_2_nv) | 18 | 8,633ms | f (all) |

全部为 glm5_2_nv 主tier, 没有 fallback 尝试。

### 重启后分段 (12:38:55Z+)

| 指标 | 值 |
|------|---|
| 总请求 | 4 |
| OK | 2 |
| ATE | 2 |
| **Post-restart SR** | **50.0%** |

Post-restart ATE: 2 double-tier, sigle-tier=0 ✅

### nv_tier_attempts (6h)

| tier | error_type | cnt | max_ms |
|------|-----------|-----|--------|
| glm5_2_nv | **400_nvcf_degraded** | **28** | — |
| glm5_2_nv | 504_nv_gateway_timeout | 3 | — |
| glm5_2_nv | 500_nv_error | 1 | — |
| dsv4p_nv | 504_nv_gateway_timeout | 8 | — |
| dsv4p_nv | NVCFPexecTimeout | 6 | 51,165ms |

### Post-restart nv_tier_attempts

| tier | error_type | cnt |
|------|-----------|-----|
| glm5_2_nv | 400_nvcf_degraded | 14 |
| dsv4p_nv | 504_nv_gateway_timeout | 1 |

### Fallback SR

| fallback_occurred | total | ok | SR |
|---|---|---|---|
| f (direct) | 52 | 21 | 40.4% |
| t (fallback) | 10 | 10 | **100.0%** ✅ |

### tier_chain 动态 (docker logs)

```
r har, health={...})  ← fallback working

FALLBACK_GRAPH transient消失阶段 (R710 pattern):
  17:03-18:33 CST (09:03-10:33 UTC): tier_chain=['glm5_2_nv'] (no fallback, 3model)
  18:59 CST self-recovery → ['glm5_2_nv', 'dsv4p_nv'] dynamic fallback
  20:03-20:33 CST (12:03-12:33 UTC): tier_chain=['glm5_2_nv'] (no fallback, 3model) 
  21:03 CST self-recovery → ['glm5_2_nv', 'dsv4p_nv'] dynamic fallback
```
= 双向 dynamic fallback
    
### 6h hourly SR

| hour (UTC) | total | ok | ate | SR |
|---|---|---|---|---|
| 08:00 | 2 | 2 | 0 | 100.0% |
| 09:00 | 18 | 10 | 8 | 55.6% |
| 10:00 | 17 | 8 | 9 | 47.1% |
| 11:00 | 11 | 6 | 5 | 54.5% |
| 12:00 | 10 | 3 | 7 | 30.0% |
| 13:00 | 2 | 1 | 1 | 50.0% |
| 14:00 | 2 | 1 | 1 | 50.0% |

09:00-12:00 UTC = 17:00-20:00 CST = FALLBACK_GRAPH transient消失，单tier ATE高发。12:00 UTC = 重启前最后窗口 (20:00-20:33 CST, (no fallback, 3model)) 最严重 SR=30%。

Post-restart (12:38+): fallback恢复，仅no-record ATE来自NVCF double-tier exhaustion。

## NOP门控评审

### 门控摘要