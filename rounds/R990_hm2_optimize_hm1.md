# HM2 Optimize HM1 — Round R990

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = opc2_uname (HM2, R989 NOP)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (false trigger)

## 2. 数据收集 (改前必有数据 — 6h 窗口, 2026-07-09 19:20 UTC)

### 2.1 nv_requests 请求概览
| 指标 | 值 |
|------|-----|
| Total | 47 |
| Success | 39 (83.0%) |
| Error | 8 (17.0%) |

### 2.2 Per-tier 明细
| tier_model | cnt | ok | err | avg_ms | p95_ms |
|------------|-----|----|-----|--------|--------|
| glm5_2_nv | 33 | 25 | 8 | 29,230 | 174,366 |
| dsv4p_nv | 14 | 14 | 0 | 89,050 | 139,129 |

### 2.3 Error 分类
| error_type | cnt |
|------------|-----|
| all_tiers_exhausted | 8 |

所有 8 个 error 均为 glm5_2_nv NVCFPexecTimeout → all_tiers_exhausted.  
NVCFPexecTimeout max = 62,606ms, UPSTREAM=66, buffer=3.4s ≥ 3s ✓.

### 2.4 nv_tier_attempts (ATE, 6h)
| id | tier | error_type | elapsed_ms |
|----|------|------------|------------|
| 621 | glm5_2_nv | NVCFPexecTimeout | 49,205 |
| 620 | glm5_2_nv | 504_nv_gateway_timeout | - |
| 619 | glm5_2_nv | NVCFPexecTimeout | 49,043 |
| 618 | glm5_2_nv | 504_nv_gateway_timeout | - |
| 617 | glm5_2_nv | NVCFPexecTimeout | 62,439 |
| 615 | glm5_2_nv | empty_200 | - |
| 616 | glm5_2_nv | NVCFPexecTimeout | 51,499 |
| 614 | glm5_2_nv | NVCFPexecTimeout | 62,351 |
| 613 | glm5_2_nv | NVCFPexecTimeout | 62,606 |
| 612 | glm5_2_nv | NVCFPexecTimeout | 62,426 |
| 611 | glm5_2_nv | NVCFPexecTimeout | 62,423 |
| 610 | glm5_2_nv | NVCFPexecTimeout | 62,461 |
| 609 | glm5_2_nv | NVCFPexecTimeout | 60,341 |
| 608 | glm5_2_nv | NVCFPexecTimeout | 60,380 |
| 607 | glm5_2_nv | NVCFPexecTimeout | 60,373 |
| 606 | glm5_2_nv | NVCFPexecTimeout | 60,352 |
| 605 | glm5_2_nv | NVCFPexecTimeout | 60,350 |

17 ATE, 全部 glm5_2_nv, NVCFPexecTimeout (8 次超时导致 all_tiers_exhausted)。16 ATE 在 ~08:00 UTC 之前（R988 重启前），1 ATE (id 621) 在重启后约 15 分钟。

### 2.5 ms_gw
- 6h: 18 requests, ms_gw 日志正常 (MS-OK-STREAM/MS-STREAM-DONE)，无 error
- ms_gw DB `ms_requests`: 18 rows
- ms_gw params floor: EMPTY_200_FASTBREAK_THRESHOLD=3, KEY_COOLDOWN_S=60, VARIANT_COOLDOWN_S=30, MIN_OUTBOUND_INTERVAL_S=1.0

### 2.6 HM1 nv_gw 当前配置
```
FALLBACK_HEALTH_THRESHOLD=0.05
KEY_AUTHFAIL_COOLDOWN_S=60
KEY_COOLDOWN_S=25
MIN_OUTBOUND_INTERVAL_S=0
NV_INTEGRATE_KEY_COOLDOWN_S=0
NVU_EMPTY_200_FASTBREAK=3
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
NVU_PEXEC_TIMEOUT_FASTBREAK=2
TIER_COOLDOWN_S=25
TIER_TIMEOUT_BUDGET_S=112
UPSTREAM_TIMEOUT=66
```

## 3. 优化决策

**NOP** — 所有参数 at floor/optimal, 无合理调整空间:

- UPSTREAM_TIMEOUT=66, buffer 3.4s ≥ 3s ✓ (R988 刚调整)
- TIER_TIMEOUT_BUDGET_S=112, >> 66 充足
- NVU_PEXEC_TIMEOUT_FASTBREAK=2 (floor)
- NVU_EMPTY_200_FASTBREAK=3 (floor)
- KEY_COOLDOWN_S=25 (floor)
- TIER_COOLDOWN_S=25 (R988 内: "iron rule: only change HM1 never HM2")
- KEY_AUTHFAIL_COOLDOWN_S=60 (R922 防御参数, 维持)
- NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv (R923, 维持)
- FALLBACK_HEALTH_THRESHOLD/NVU_FALLBACK_HEALTH_THRESHOLD=0.05 (R982, floor)

dsv4p_nv 14/14 100%, ms_gw 18/18 正常 — 两条链路均稳定。

glm5_2_nv NVCFPexecTimeout 仍是上游 NVCF 固有超时特征 — R988 已将 UPSTREAM 推至 66s, buffer 3.4s 已足够。进一步增大 UPSTREAM_TIMEOUT 会拉长用户等待时间，收益递减。

**决策**: NOP, 所有参数维持不变。

## ⏳ 轮到HM1优化HM2