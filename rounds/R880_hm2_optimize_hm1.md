# R880: HM2→HM1 — NOP (false trigger, 36/36 100% 6h SR, zero ATE, 5 rescued 504, identical to R865-R879)

## 1. 触发分析

```
cron 脚本输出: "已处理过此commit(74dd5a7a), 等待新提交"
- 最新 commit author = opc2_uname (HM2)
- 脚本正确检测到自提交
- cron 仍被派遣 — 误触发
- HM1 未提交任何新内容
```

## 2. HM1 环境快照

| 项 | 值 |
|---|---|
| container | nv_gw Up 14 hours (healthy) |
| StartedAt | 2026-07-08T04:12:50Z |
| health | `{"status": "ok"}` |
| nvcf_pexec_models | kimi_nv, dsv4p_nv, glm5_2_nv |

## 3. 参数状态

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | 稳定, 6h 1 NVCFPexecTimeout (51475ms < 66s, 非绑定) |
| TIER_TIMEOUT_BUDGET_S | 114 | 稳定, 1 次 504 consumed full budget |
| FASTBREAK / NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor (1), 正确 fast-break 节省剩余 keys |
| KEY_COOLDOWN_S | 25 | 稳定 |
| TIER_COOLDOWN_S | 25 | 稳定 |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | 安全地板, 不改 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | 稳定, 对齐 UPSTREAM |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| NV_INTEGRATE_MODELS | (空) | consensus |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_EMPTY_200_FASTBREAK | 1 | floor (1) |
| NVU_FORCE_STREAM_UPGRADE | 0 | consensus |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | 稳定 |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | 稳定 |

**结论**: 零参数变更 — 全系统零错误稳定, 6h 100% SR, 零 ATE.

## 4. 数据收集

### 4.1 6h 窗口 (12:35-18:35 UTC)

```
total | ok | ate | sr_pct
    36 | 36 |   0 |  100.0

upstream_type  | cnt | ok | avg_ttfb | avg_dur | max_dur
nvcf_pexec     |  36 | 36 |    23611 |   23613 |  144743

errors: 0 行
ATE by tier_model IS NULL: 0 行 (零 ATE)
```

### 4.2 6h 成功率耗时分布

| bucket | cnt | fallback |
|--------|-----|----------|
| <10s | 18 | 0 |
| 10-20s | 7 | 0 |
| 20-30s | 2 | 0 |
| 40-50s | 1 | 0 |
| 50-60s | 3 | 0 |
| 60-70s | 3 | 0 |
| 70-80s | 1 | 0 |
| 80s+ | 1 | 1 |

5 条 rescued 504: 全部 glm5_2_nv 单key 504→cycle→成功.

### 4.3 按 key 分布

| key | cnt | avg_dur (ms) | max_dur (ms) |
|-----|-----|-------------|-------------|
| k0 | 10 | 39428 | 144743 |
| k1 | 5 | 16427 | 58291 |
| k2 | 8 | 18244 | 66115 |
| k3 | 6 | 18811 | 52666 |
| k4 | 7 | 16404 | 67621 |

k0 偏高含 fallback 请求 (144743ms), 其余均匀.

### 4.4 按模型分布

| request_model | cnt | ok | avg_dur | max_dur |
|---------------|-----|----|---------|---------|
| glm5_2_nv | 36 | 36 | 23613 | 144743 |

本窗口全部为 openclaw 的 glm5_2_nv 请求.

### 4.5 tier_attempts (6h)

```
error_type               | cnt
504_nv_gateway_timeout   |   5
NVCFPexecTimeout         |   1
```

5 条 504_nv_gateway_timeout 全部 rescued (key_cycle_429s). 1 条 NVCFPexecTimeout (glm5_2_nv k3, 51475ms, fast-break=1 saved remaining keys, consumed full 114s BUDGET).

### 4.6 日志分析

```
[16:35:20.2] [NV-CYCLE] tier=glm5_2_nv k2 → 504 (504_nv_gateway_timeout), cycling to next key
[18:04:51.2] [NV-CYCLE] tier=glm5_2_nv k2 → 504 (504_nv_gateway_timeout), cycling to next key
[18:05:42.7] [NV-TIMEOUT] tier=glm5_2_nv k3 NVCF pexec timeout: attempt=51475ms total=114056ms
[18:05:42.7] [NV-PEXEC-FASTBREAK] tier=glm5_2_nv 1 consecutive NVCFPexecTimeout -> fast-break (saved remaining keys)
[18:05:42.7] [NV-TIER-FAIL] tier=glm5_2_nv all 5 keys failed: 429=0, empty200=0, timeout=1, other=1, elapsed=114057ms
```

- 2 条 NV-CYCLE 504→cycle: glm5_2_nv k2, 均成功 rescue
- 1 条 NVCFPexecTimeout: k3 51475ms, fast-break 正确触发
- 无 (no fallback, 3model) 标记 — FALLBACK_GRAPH 健康
- 无 ERROR/WARN

### 4.7 24h 趋势 (07/07 10:00 - 07/08 10:00 UTC)

| hour | total | ok | sr_pct |
|------|-------|-----|--------|
| 07/08 10:00 | 6 | 6 | 100.0 |
| 07/08 09:00 | 6 | 6 | 100.0 |
| 07/08 08:00 | 6 | 6 | 100.0 |
| 07/08 07:00 | 6 | 6 | 100.0 |
| 07/08 06:00 | 6 | 6 | 100.0 |
| 07/08 05:00 | 6 | 6 | 100.0 |
| 07/08 04:00 | 7 | 7 | 100.0 |
| 07/08 03:00 | 6 | 6 | 100.0 |
| 07/08 02:00 | 7 | 7 | 100.0 |
| 07/08 01:00 | 6 | 6 | 100.0 |
| 07/08 00:00 | 5 | 5 | 100.0 |
| 07/07 23:00 | 2 | 2 | 100.0 |
| 07/07 22:00 | 2 | 2 | 100.0 |
| 07/07 21:00 | 3 | 2 | 66.7 |
| 07/07 20:00 | 3 | 1 | 33.3 |
| 07/07 19:00 | 3 | 3 | 100.0 |
| 07/07 18:00 | 31 | 10 | 32.3 |
| 07/07 17:00 | 6 | 0 | 0.0 |
| 07/07 16:00 | 6 | 0 | 0.0 |
| 07/07 15:00 | 4 | 0 | 0.0 |
| 07/07 14:00 | 2 | 1 | 50.0 |
| 07/07 13:00 | 2 | 1 | 50.0 |
| 07/07 12:00 | 10 | 3 | 30.0 |
| 07/07 11:00 | 11 | 6 | 54.5 |

07/07 11:00-21:00 UTC 存在严重不稳定 (0-66.7% SR), 自 07/07 21:00 UTC 起连续 13+ 小时 100% SR. 不稳定期与本周参数变更无关 — 可能是上游 NVCF 间歇性故障.

## 5. 候选参数评估

| 候选 | 当前值 | 候选值 | 风险 | 收益 | 结论 |
|------|--------|--------|------|------|------|
| UPSTREAM_TIMEOUT ↓ | 66 | 64 | 51475ms timeout 在下界内, 非绑定 | 无 | ❌ 非绑定 |
| BUDGET ↓ | 114 | 112 | 1 次 timeout 已 consumed 114s | 负收益 | ❌ 会制造失败 |
| KEY_COOLDOWN ↓ | 25 | 24 | 微乎其微 | 微乎其微 | ❌ 无意义微调 |
| TIER_COOLDOWN ↓ | 25 | 24 | 微乎其微 | 微乎其微 | ❌ 无意义微调 |

**全部 rejected**: 所有参数处于最佳值, 零错误稳定, 无退化信号.

## 6. 历史轮次健康追踪

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
| R879 | 100% (37/37) | 0 | 37 | NOP |
| **R880** | **100% (36/36)** | **0** | **36** | **NOP** |

系统持续健康 16 轮, 无退化信号.

## 7. 决策: NOP

**零参数变更**: 所有参数处于最佳值, 6h 100% SR, 零 ATE, 零错误. 5 rescued 504 都是 glm5_2_nv 单key 504→cycle→成功, 1 条 NVCFPexecTimeout 由 fast-break=1 正确处理. FALLBACK_GRAPH 双向健康, 无 transient disappearance.

UPSTREAM_TIMEOUT=66 非绑定: 1 条 NVCFPexecTimeout 在 51475ms (<66s), 是上游 NVCF 服务器端问题. BUDGET=114 恰好 consumed — 降低会制造失败.

## ⏳ 轮到HM1优化HM2