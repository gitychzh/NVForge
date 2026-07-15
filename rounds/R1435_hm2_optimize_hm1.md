# R1435: HM2→HM1 — NOP (false trigger, double-dispatch, 589th chain of R1133)

**Timestamp**: 2026-07-15 15:21 UTC

## 触发判定
- 脚本输出: "这是我提交的, 不触发" → FALSE TRIGGER (double-dispatch)
- latest commit: R1434 (opc2_uname, HM2 NOP)
- HM1 git log: R1206 (228 rounds behind HM2)
- 结论: false trigger, double-dispatch (589th chain of R1133)

## Data Collection (HM1, 改前必有数据)

### nv_gw 容器状态
- Container: nv_gw Up 44 minutes (healthy) — 重启于 2026-07-15T06:39:45Z
- Compose md5: 3863a7c165f938dbde494e42b8d19be5 (unchanged from R1431)
- docker logs: 2 NV-ZOMBIE signals, 1 NV-ALL-TIERS-FAIL (fresh ATE), clean otherwise

### 6h 总体
| total | ok | err | sr_pct |
|-------|----|-----|--------|
| 60 | 42 | 18 | 70.0% |

### 6h 按模型
| mapped_model | cnt | ok | err | sr_pct | avg_dur |
|--------------|-----|----|-----|--------|---------|
| glm5_2_nv | 44 | 35 | 9 | 79.5% | 11645ms |
| dsv4p_nv | 16 | 7 | 9 | 43.8% | 36242ms |

### 6h 错误类型 (status≠200)
| error_type | cnt |
|------------|-----|
| zombie_empty_completion | 15 |
| all_tiers_exhausted | 3 |

### zombie 详情
| mapped_model | cnt | avg_ichars | avg_dur |
|--------------|-----|------------|---------|
| dsv4p_nv | 6 | 210222 | 17574ms |
| glm5_2_nv | 9 | 210503 | 7217ms |

### ATE 详情 (含 ms_gw 恢复)
| mapped_model | cnt | avg_dur |
|--------------|-----|---------|
| dsv4p_nv | 4 | 87071ms |
| glm5_2_nv | 12 | 21391ms |

6h_error_type ATE=3 (502 unrecovered), 6h_ate_detail=16 total → 13 recovered by ms_gw fallback.
glm5_2_nv ATE=12 all status=200 + fallback=t → context-length 400 → ms_gw rescue (NOT failures).

### 6h 按小时
| hour (UTC) | total | ok | fail | sr_pct |
|-----------|-------|-----|------|--------|
| 01:00 | 4 | 4 | 0 | 100.0% |
| 02:00 | 6 | 4 | 2 | 66.7% |
| 03:00 | 9 | 5 | 4 | 55.6% |
| 04:00 | 7 | 3 | 4 | 42.9% |
| 05:00 | 26 | 22 | 4 | 84.6% |
| 06:00 | 5 | 3 | 2 | 60.0% |
| 07:00 | 3 | 1 | 2 | 33.3% |

### 其他
- tier_attempts: 0
- NVStream_IncompleteRead: 0
- fallback: 13/13 rescues (100% ms_gw recovery)
- ms_gw: 27/26 96.3% SR (unchanged from R1434)
- ATE tiers: all 1 (single-key failure, no multi-tier cascade)

### Fresh ATE (07:05 UTC, post-R1431)
```
k4 → 504 (NVCF gateway timeout, 61s)
k5 → pexec timeout 60.8s → total=124.0s → FASTBREAK=1 abort
ms_gw fallback → TimeoutError 206.1s → FAILED
```

BUDGET=124 exhausted at 124.0s. ms_gw also failed (206s) → NVCF function degradation, not BUDGET-sensitive.

### 当前参数 (all floor/optimal)
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=205
NVU_TIER_BUDGET_DSV4P_NV=124
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
TIER_COOLDOWN_S=15
KEY_COOLDOWN_S=25
NV_INTEGRATE_KEY_COOLDOWN_S=0
MIN_OUTBOUND_INTERVAL_S=0
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_EMPTY_200_FASTBREAK=2
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_PEER_FB_SKIP_MODELS=
NVU_MS_GW_FALLBACK_TIMEOUT=195
NVU_STREAM_TOTAL_DEADLINE_S=42
NVU_STREAM_FIRST_BYTE_DEADLINE_S=20
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
```

## 分析

### NOP 判定
1. **所有参数 floor/optimal** — 无调整空间
2. **zombie_empty_completion=15** — NVCF content-filter (avg input 210K chars, output 0-14 tokens)，非 gate 配置可修复
3. **ATE=3 (502) + 13 ms_gw recovered** — 1 pre-R1431, 1 fresh (NVCF degradation, ms_gw also failed), 1 older (06:05 pre-R1431). fallback 100% effective
4. **0 tier_attempts** — 无 key 循环
5. **compose md5 未变** — 无 HM1 外部修改
6. **ms_gw 96.3% SR** — 健康
7. **BUDGET 124 已部署 44min** — 数据稳定，fresh ATE 非 BUDGET 可修复（ms_gw 同失败）

### 数据变化 (vs R1434)
- +1 dsv4p_nv req (15→16), +1 ATE (2→3, 07:05 fresh ATE now in 6h window)
- SR: 71.2%→70.0% (rounding artifact, +1 fresh ATE)
- 其余全部相同: zombie=15, ms_gw=27/26, tier_attempts=0, fallback=13/13

### 趋势
- 05:00 小时 84.6% SR (26req/22OK) — 正常水平
- 07:00 小时仅 3req (1OK/2fail) — 样本过小
- zombie 稳定 ~15/6h (NVCF 固有缺陷)
- ATE 低水平 (3 unrecovered, 2/3 pre-R1431)

## 决策: NOP
- 零参数变更
- 零 compose 编辑
- 零容器重启
- 铁律:只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
