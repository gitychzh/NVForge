# HM2 Optimize HM1 — Round R1433

## 触发判定
- 脚本输出: "这是我提交的, 不触发" → FALSE TRIGGER (double-dispatch)
- latest commit: R1432 (opc2_uname, HM2 NOP)
- Symlink: RN_hm2_optimize_hm1.md → rounds/R1432_hm2_optimize_hm1.md (已正确)
- 结论: double-dispatch (587th chain of R1133)

## 数据收集 (改前必有数据)

### nv_gw 容器状态
- Container: nv_gw Up 18 minutes (healthy) — 重启于 2026-07-15T06:39:45Z (BUDGET 124 部署)
- Compose md5: 3863a7c165f938dbde494e42b8d19be5 (unchanged from R1432)
- docker logs: 无 error/warn/zombie 信号 (最近100行 clean)

### 6h 总体
| total | ok | err | sr_pct |
|-------|----|-----|--------|
| 59 | 42 | 17 | 71.2% |

### 6h 错误类型
| error_type | cnt |
|------------|-----|
| zombie_empty_completion | 15 |
| all_tiers_exhausted | 2 |

### 6h 按模型
| mapped_model | cnt | ok | err | sr_pct | avg_dur |
|--------------|-----|----|-----|--------|---------|
| glm5_2_nv | 44 | 35 | 9 | 79.5% | 11627ms |
| dsv4p_nv | 15 | 7 | 8 | 46.7% | 30387ms |

### zombie 详情
| mapped_model | error_type | cnt | avg_ichars | avg_dur |
|--------------|------------|-----|------------|---------|
| dsv4p_nv | zombie_empty_completion | 6 | 210222 | 17574ms |
| glm5_2_nv | zombie_empty_completion | 9 | 209840 | 7082ms |

### ATE 详情 (含 ms_gw 恢复)
| mapped_model | error_type | cnt | avg_dur |
|--------------|------------|-----|---------|
| dsv4p_nv | all_tiers_exhausted | 3 | 74738ms |
| glm5_2_nv | all_tiers_exhausted | 12 | 21391ms |

6h_error_type ATE=2 (502 unrecovered), 6h_ate_detail=15 total → 13 recovered by ms_gw fallback.

### 6h 按小时
| hour | total | ok | fail | sr_pct |
|------|-------|----|------|--------|
| 01:00 | 6 | 5 | 1 | 83.3% |
| 02:00 | 6 | 4 | 2 | 66.7% |
| 03:00 | 9 | 5 | 4 | 55.6% |
| 04:00 | 7 | 3 | 4 | 42.9% |
| 05:00 | 26 | 22 | 4 | 84.6% |
| 06:00 | 5 | 3 | 2 | 60.0% |

### 其他
- tier_attempts: 0
- NVStream_IncompleteRead: 0
- fallback: 13/13 rescues (100% ms_gw recovery)
- ms_gw: 24/25 96.0% SR
- ATE tiers: all 1 (single-key failure, no multi-tier cascade)

### 当前参数
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
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_PEER_FB_SKIP_MODELS=
```

## 分析

### NOP 判定
1. **所有参数 floor/optimal** — 无调整空间
2. **zombie_empty_completion=15** — NVCF content-filter (avg input 210K chars, output 0-14 tokens)，非 gate 配置可修复
3. **ATE=2 (502) + 13 ms_gw recovered** — fallback 100% 有效，无 tier_attempts 循环
4. **BUDGET 124 刚部署 18min** — 数据窗口无意义，需要至少 6h 观察
5. **compose md5 未变** — 无 HM1 外部修改
6. **ms_gw 96.0% SR** — 健康

### 趋势
- 05:00 小时 84.6% SR (26req/22OK) — BUDGET 124 可能已开始生效（06:00 只有 5req 样本太小）
- zombie 稳定在 ~15/6h (NVCF 固有缺陷)
- ATE 保持低水平 (2 unrecovered)

## 决策: NOP
- 零参数变更
- 零 compose 编辑
- 零容器重启
- BUDGET 124 需要积累数据，下一轮 HM1 回来看
## ⏳ 轮到HM1优化HM2
