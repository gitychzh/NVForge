# HM2 Optimize HM1 — Round R921

## 触发分析

- **cron 脚本输出**: `"这是我提交的, 不触发"`
- **最新 commit**: `d15a223` (R920: HM2→HM1 — NOP)
- **最新 commit author**: `opc2_uname` (HM2)
- **判定**: **False trigger** — 37th consecutive false-trigger dispatch. R920 是 NOP 轮次，由前一次 cron dispatch 完成。本轮 cron 重新派遣了同一触发条件。

## 数据采集 (HM1 100.109.153.83)

### nv_gw 容器 env (key params)

| 参数 | 值 |
|---|---|
| FALLBACK_HEALTH_THRESHOLD | 0.05 (R919) |
| ACTUAL HEALTH_THRESHOLD (func_health.py) | 0.1 |
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

### nv_gw 容器状态

- 容器启动时间: 2026-07-08 19:35 UTC
- 运行状态: running
- 日志: 安静，仅启动行，无 error/warn/fallback 事件
- fallback_chain: ['kimi_nv', 'dsv4p_nv', 'glm5_2_nv']

### nv_requests DB (6h)

| 指标 | 值 |
|---|---|
| 总请求 | 57 |
| 成功 (200) | 57 |
| 失败 (502) | 0 |
| **6h SR** | **100.0%** ✅ |
| dsv4p_nv SR | 6/6 = 100.0% |
| glm5_2_nv SR | 51/51 = 100.0% |
| Fallback 触发 | 2/57 (3.5%) |
| 直连平均 duration | 12,584ms |
| Fallback 平均 duration | 96,857ms |
| 最大 duration | 120,515ms |

### nv_requests DB (1h, 最新)

| 指标 | 值 |
|---|---|
| 总请求 | 6 |
| 成功 (200) | 6 |
| 失败 | 0 |
| 1h SR | 100.0% |

### nv_requests DB 最近 10 条请求

| duration_ms | mapped_model | tier_model | fallback | status |
|---|---|---|---|---|
| 3004 | glm5_2_nv | glm5_2_nv | f | 200 |
| 4851 | glm5_2_nv | glm5_2_nv | f | 200 |
| 7197 | glm5_2_nv | glm5_2_nv | f | 200 |
| 8496 | glm5_2_nv | glm5_2_nv | f | 200 |
| 3227 | glm5_2_nv | glm5_2_nv | f | 200 |
| 2778 | glm5_2_nv | glm5_2_nv | f | 200 |
| 6981 | glm5_2_nv | glm5_2_nv | f | 200 |
| 9729 | glm5_2_nv | glm5_2_nv | f | 200 |
| 6308 | glm5_2_nv | glm5_2_nv | f | 200 |
| 6327 | glm5_2_nv | glm5_2_nv | f | 200 |

全部成功，延迟 2.8-9.7s，正常。

### nv_tier_attempts (6h)

| Tier | Error Type | Count | Max ms |
|---|---|---|---|
| dsv4p_nv | NVCFPexecTimeout | 1 | 52,849 |
| dsv4p_nv | empty_200 | 1 | — |
| glm5_2_nv | 504_nv_gateway_timeout | 1 | — |
| glm5_2_nv | empty_200 | 1 | — |

仅 4 次 minor tier 错误，无系统性故障。NVCFPexecTimeout max=52,849ms << UPSTREAM=64 → UPSTREAM 非绑定。

### ms_gw 状态

- 6h 请求: 0 (完全空闲)
- 无错误
- EMPTY_200_FASTBREAK_THRESHOLD=3 (已在地板)

## 优化决定: NOP

**理由**:
1. **6h SR = 100.0%** — 完美，无优化空间
2. **nv_gw 所有参数已在地板**: UPSTREAM_TIMEOUT=64, TIER_TIMEOUT_BUDGET_S=114, KEY_COOLDOWN_S=25, TIER_COOLDOWN_S=25, NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_EMPTY_200_FASTBREAK=3, MIN_OUTBOUND_INTERVAL_S=0, NVU_CONNECT_RESERVE_S=0
3. **ms_gw 完全空闲** — 无优化空间
4. **NVCFPexecTimeout max=52,849ms << UPSTREAM=64** — UPSTREAM 非绑定，减少无意义
5. **FALLBACK_HEALTH_THRESHOLD=0.05** (R919) 已生效 — 6h 内无 ATE 可验证效果，但 100% SR 表明系统健康
6. **1h 窗口 6/6 100%** — 最新数据与 6h 窗口一致，无退化

**无参数需要调整。铁律: 只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2