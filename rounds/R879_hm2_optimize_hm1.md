# R879: HM2→HM1 — NOP (false trigger, 37/37 100% 6h SR, zero ATE, 4 rescued 504, identical to R865-R878)

## 1. 触发分析

```
cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author = opc2_uname (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发
- HM1 本地 git log 停留在 R821，未提交任何新内容（58 轮落后）
```

## 2. HM1 环境快照

| 项 | 值 |
|---|---|
| container | nv_gw Up 6 hours (healthy) |
| health | `{"status": "ok"}` |
| tier_chain (glm5_2_nv) | `['glm5_2_nv', 'dsv4p_nv']` (dynamic fallback) |
| tier_chain (dsv4p_nv) | `['dsv4p_nv', 'glm5_2_nv']` (dynamic fallback) |

## 3. 参数状态

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | 稳定, 6h 零 NVCFPexecTimeout |
| TIER_TIMEOUT_BUDGET_S | 114 | 稳定, per-tier budget |
| FASTBREAK / NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor (1), pexec单key |
| KEY_COOLDOWN_S | 25 | 稳定 |
| TIER_COOLDOWN_S | 25 | 稳定 |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | 安全地板, 不改 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | 稳定 |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor, integrate当前无模型 |
| NV_INTEGRATE_MODELS | (空) | consensus |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_EMPTY_200_FASTBREAK | 1 | floor (1) |
| NVU_FORCE_STREAM_UPGRADE | 0 | consensus |

**结论**: 零参数变更 — 全系统零错误稳定, 6h 100% SR, 零 ATE.

## 4. 数据收集

### 4.1 6h 窗口

```
total | ok | ate | sr_pct
    37 | 37 |   0 |  100.0

upstream_type  | cnt | ok | avg_ttfb | avg_dur | max_dur
nvcf_pexec     |  37 | 37 |    16849 |   16850 |   72409

errors: 0 行
ATE by tiers_tried_count: 0 行 (零 ATE)
```

### 4.2 6h 成功率耗时分布

| bucket | cnt | fallback |
|--------|-----|----------|
| <10s | 23 | 0 |
| 10-20s | 6 | 0 |
| 20-30s | 2 | 0 |
| 50-60s | 2 | 0 |
| 60-70s | 3 | 0 |
| 70-80s | 1 | 0 |

4 条 rescued 504: key_cycle_429s=1, 全部 glm5_2_nv 单key 504→cycle→成功.

### 4.3 按 key 分布

| key | cnt | avg_dur (ms) |
|-----|-----|-------------|
| k0 | 9 | 27242 |
| k1 | 6 | 14311 |
| k2 | 9 | 13367 |
| k3 | 7 | 10111 |
| k4 | 6 | 16890 |

均匀分布, 无 key 级异常.

### 4.4 tier_attempts (6h)

```
error_type               | cnt
504_nv_gateway_timeout   |   4

NVCFPexecTimeout: 0 行
```

4 条 504_nv_gateway_timeout 全部 rescued (key_cycle_429s=1), 零最终失败.

### 4.5 日志分析

- tier_chain 始终为 `['glm5_2_nv', 'dsv4p_nv']` (dynamic fallback) — FALLBACK_GRAPH 健康
- 无 (no fallback, 3model) 标记
- 无 ERROR/WARN
- 2 条 NV-CYCLE 504→cycle: glm5_2_nv k5 (15:34) 和 k2 (16:35), 均成功 rescue

## 5. 历史轮次健康追踪

| 轮次 | 6h SR | 6h 失败 | 6h 总量 | 决策 |
|------|-------|---------|---------|------|
| R865 | 100% (37/37) | 0 | 37 | NOP |
| R866 | 100% (36/36) | 0 | 36 | NOP |
| R867 | 100% (37/37) | 0 | 37 | NOP |
| R868 | 100% (35/35) | 0 | 35 | NOP |
| R869 | 100% (37/37) | 0 | 37 | NOP |
| R870 | 100% (36/36) | 0 | 36 | NOP |
| R871 | 100% (38/38) | 0 | 38 | NOP |
| R872 | 100% (37/37) | 0 | 37 | NOP |
| R873 | 100% (36/36) | 0 | 36 | NOP |
| R874 | 100% (37/37) | 0 | 37 | NOP |
| R875 | 100% (37/37) | 0 | 37 | NOP |
| R876 | 100% (37/37) | 0 | 37 | NOP |
| R877 | 100% (37/37) | 0 | 37 | NOP |
| R878 | 100% (37/37) | 0 | 37 | NOP |
| **R879** | **100% (37/37)** | **0** | **37** | **NOP** |

系统持续健康 15 轮, 无退化信号.

## 6. 决策: NOP

**零参数变更**: 所有参数处于最佳值, 6h 100% SR, 零 ATE, 零错误. 4 rescued 504 都是 glm5_2_nv 单key 504→cycle→成功, 上游 NVCF 间歇性 gateway timeout 已自动 rescue. FALLBACK_GRAPH 双向健康, 无 transient disappearance.

UPSTREAM_TIMEOUT=66 非绑定: 6h 内零 NVCFPexecTimeout, 所有请求直接成功或单次 cycle rescue.

## ⏳ 轮到HM1优化HM2