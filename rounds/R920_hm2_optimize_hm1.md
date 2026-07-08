# HM2 Optimize HM1 — Round R920

## 触发分析

- **cron 脚本输出**: `"这是我提交的, 不触发"`
- **最新 commit**: `03a4f58` (R919: HM2→HM1 — FALLBACK_HEALTH_THRESHOLD 0.10→0.05)
- **最新 commit author**: `opc2_uname` (HM2)
- **判定**: **False trigger** — 36th consecutive false-trigger dispatch. R919 是真实优化轮次（FALLBACK_HEALTH_THRESHOLD 0.10→0.05），由前一次 cron dispatch 完成。本轮的 cron 重新派遣了同一触发条件。
- **锚文件状态**: 原锚文件为 regular file 指向 R919 内容，已清理后重新创建。

## 数据采集 (HM1 100.109.153.83)

### nv_gw 容器 env (key params)

| 参数 | 值 |
|---|---|
| FALLBACK_HEALTH_THRESHOLD | **0.05** (R919 变更确认 ✅) |
| UPSTREAM_TIMEOUT | 64 |
| TIER_TIMEOUT_BUDGET_S | 114 |
| MIN_OUTBOUND_INTERVAL_S | 0 |
| KEY_COOLDOWN_S | 25 |
| TIER_COOLDOWN_S | 25 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 |
| NVU_EMPTY_200_FASTBREAK | 3 |
| NVU_CONNECT_RESERVE_S | 0 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 |
| NV_INTEGRATE_MODELS | (空) |

### nv_gw 日志 (最近 100 行)

- 无 error/warn/fail/fallback 事件
- 仅显示启动行: `Listening on 0.0.0.0:40006 (role=passthrough, default_tier=dsv4p_nv, fallback_chain=['kimi_nv', 'dsv4p_nv', 'glm5_2_nv'])`
- 日志安静，无异常

### nv_requests DB (6h)

| 指标 | 值 |
|---|---|
| 总请求 | 57 |
| 成功 (200) | 57 |
| 失败 | 0 |
| **6h SR** | **100.0%** ✅ |
| 平均 TTFB | 15,498ms |
| 平均 Duration | 15,541ms |
| 最大 Duration | 120,515ms |
| Fallback 触发 | 2/57 (3.5%) |
| 上游类型 | 全部 nvcf_pexec |

### nv_requests DB (24h)

| 指标 | 值 |
|---|---|
| 总请求 | 181 |
| 成功 (200) | 177 |
| 失败 | 4 |
| 24h SR | 97.8% |
| 错误类型 | 4x all_tiers_exhausted (全部为 R919 前数据) |

### nv_tier_attempts 6h

| Tier | Error Type | Count | Max ms |
|---|---|---|---|
| dsv4p_nv | NVCFPexecTimeout | 1 | 52,849 |
| dsv4p_nv | empty_200 | 1 | — |
| glm5_2_nv | 504_nv_gateway_timeout | 1 | — |
| glm5_2_nv | empty_200 | 1 | — |

仅 4 次 minor tier 错误，无系统性故障。

### ms_gw 状态

- 6h 请求: 0 (完全空闲)
- 无错误
- EMPTY_200_FASTBREAK_THRESHOLD=3 (已在地板)

## 优化决定: NOP

**理由**:
1. **6h SR = 100.0%** — 完美，无优化空间
2. **nv_gw 所有参数已在地板**: UPSTREAM_TIMEOUT=64, TIER_TIMEOUT_BUDGET_S=114, KEY_COOLDOWN_S=25, TIER_COOLDOWN_S=25, NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_EMPTY_200_FASTBREAK=3, MIN_OUTBOUND_INTERVAL_S=0, NVU_CONNECT_RESERVE_S=0
3. **ms_gw 完全空闲** — 无优化空间
4. **R919 变更 (FALLBACK_HEALTH_THRESHOLD 0.10→0.05) 已生效** — 从 24h 数据看，R919 前的 4 个 ATE 若发生在 R919 后可能被救回，但 6h 窗口内无 ATE 可验证
5. **24h SR 97.8%** — 4 个 ATE 均为 R919 前历史数据，新数据干净

**无参数需要调整。**

## 配置快照 (HM1 nv_gw 当前)

| 参数 | 值 |
|---|---|
| UPSTREAM_TIMEOUT | 64 |
| TIER_TIMEOUT_BUDGET_S | 114 |
| FALLBACK_HEALTH_THRESHOLD | 0.05 (R919) |
| MIN_OUTBOUND_INTERVAL_S | 0 |
| KEY_COOLDOWN_S | 25 |
| TIER_COOLDOWN_S | 25 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 |
| NVU_EMPTY_200_FASTBREAK | 3 |
| NVU_CONNECT_RESERVE_S | 0 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 |
| NV_INTEGRATE_MODELS | (空) |

## ⏳ 轮到HM1优化HM2
