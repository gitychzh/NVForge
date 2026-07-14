# HM2 Optimize HM1 — Round R1335

## 触发分析
- **cron 脚本输出**: `[2026-07-14 15:30:34] 这是我提交的, 不触发`
- **最新 commit**: `981473a` author=`opc2_uname` (HM2, R1334)
- **HM1 本地 git**: `de04120` (R1206, 129 轮落后)
- **判定**: 误触发 (false trigger / double-dispatch) — HM2 自提交，脚本正确检测并标记 "不触发"
- **最后一次请求**: 2026-07-14 07:33:36 UTC — 容器重启后 (R1334, ~15:25 UTC) **0 请求**

## 6h 数据 (2026-07-14 09:30–15:30 UTC)

### 总体
| 指标 | 值 |
|------|-----|
| 总请求 | 81 |
| 成功 | 68 |
| 失败 | 13 |
| 成功率 | 84.0% |
| 0 tier_attempts | ✅ |
| 0 fallback 触发 | ❌ (代码级 ABORT-NO-FALLBACK) |

### 按路径
| 路径 | 模型 | 请求 | 成功 | 失败 | SR | avg_ttfb | avg_dur |
|------|------|------|------|------|-----|----------|---------|
| nvcf_pexec | dsv4p_nv | 48 | 48 | 0 | 100% | 20,934ms | 20,938ms |
| nv_integrate | glm5_2_nv | 27 | 20 | 7 | 74.1% | 10,359ms | 10,633ms |
| (ATE) | dsv4p_nv | 6 | 0 | 6 | 0% | 820ms | 71,694ms |

### 错误分类
| 错误类型 | 数量 | avg_dur | 说明 |
|----------|------|---------|------|
| zombie_empty_completion | 7 | 7,300ms | glm5_2_nv integrate, NVCF content-filter stop+12chars, 175K-185K input — **非配置可修复** |
| all_tiers_exhausted | 6 | 71,694ms | dsv4p_nv pexec, **全部 PRE-R1334** (05:57–06:37 UTC), tiers_tried_count=1, ttfb 533-1246ms, 72K-244K input |

### ATE 详细分析
- **全部 6 个 ATE 发生在 PRE-R1334** 时段 (R1334 在 ~15:25 UTC 部署)
- `tiers_tried_count=1` — 仅尝试 1 个 key，预算耗尽
- `fallback_occurred=false, fallback_actually_attempted=false` — 无 fallback
- `duration_ms ≈ 72,000ms` = `UPSTREAM_TIMEOUT=66s` + ~6s overhead
- k1 pexec 运行满 66s → 剩余预算 82-66=16s → k2 无足够预算 → ATE
- 与 R1334 分析一致：budget exhaustion after k1 UPSTREAM_TIMEOUT
- **R1334 后 0 请求，无法评估 BUDGET=82 是否有效**

### 僵尸详细
- 全部 glm5_2_nv integrate, NVCF content-filter stop+12chars
- 网关检测 `[NV-ZOMBIE-EMPTY]` 正确 → 3-15s 内 502
- 非配置可修复的代码级问题

### ms_gw
| 指标 | 值 |
|------|-----|
| 总请求 | 6 |
| 成功 | 5 |
| 失败 | 1 |
| SR | 83.3% |

## HM1 配置快照
```
NVU_TIER_BUDGET_DSV4P_NV=82    ← R1334 变更 (78→82, +4s)
UPSTREAM_TIMEOUT=66
TIER_COOLDOWN_S=15
NVU_EMPTY_200_FASTBREAK=2
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_MS_GW_FALLBACK_TIMEOUT=195
NVU_PEER_FB_SKIP_MODELS=
KEY_AUTHFAIL_COOLDOWN_S=60
KEY_COOLDOWN_S=25
NVU_CONNECT_RESERVE_S=0
TIER_TIMEOUT_BUDGET_S=205
```

## 决策
**NOP** — 误触发 (false trigger / double-dispatch):
- cron 脚本输出 "这是我提交的, 不触发"
- HM1 最新请求在容器重启前 (07:33 UTC)，R1334 后 0 请求
- 6 个 ATE 全部 PRE-R1334，无法评估 BUDGET=82 效果
- 所有参数在 floor/optimal 状态
- 零参数变更，零 compose 变更，零容器重启
- ms_gw 无优化空间
- Compose md5: `4c3e804d68a158d76937dfae32764edf` (HM1 编辑 R1334 变更后)

## ⏳ 轮到HM1优化HM2
