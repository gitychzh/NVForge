# R2073_hm2_oc2 — NOP 巡检轮 21

> 2026-07-21 ~08:30 UTC (HM2). 冗余第二 nv_gw 优化者.

## TL;DR

**0 改动 0 restart. 连续第 21 轮 NOP 冻结.** 四重佐证全成立:

1. glm5_2_nv 6h 98.6% (778/789) 持平 R2072, 30min 100% (65/65)
2. R2145 model 修复持续生效: caller=other 30min 32 次全 glm5_2_nv 全 200, 6h cc-glm5-2 last_seen = NULL (彻底清零, 不退化)
3. fallback 30min = 0, 真中断连续第 31 轮 = 0
4. env 无漂移, StartedAt=01:44:55Z 与 R2072 一致, RestartCount=0

dsv4p_nv 6h SR 2.8% (5/180, all_tiers_exhausted 主导, NVCF function 74f02205 仍全挂) — 非本域.

## 数据

### 30min (R2073)

| mapped_model | 200 | 502 | 备注 |
|---|---|---|---|
| glm5_2_nv | 65 | 0 | 100% ★ |
| dsv4p_nv | 0 | 6 | 全 all_tiers_exhausted |

- caller=other (openclaw2 直连): **32 次全 glm5_2_nv 全 200** ★
- caller=cc4101-primary: 33 次 glm5_2_nv 全 200
- caller=unknown: 6 次 dsv4p 502 (走 default, 非 openclaw2 路径)

### 6h

| mapped_model | 200 | 502 | 429 | SR |
|---|---|---|---|---|
| glm5_2_nv | 778 | 11 | 0 | **98.6%** ★ |
| dsv4p_nv | 5 | 169 | 5 | 2.8% |

- glm5_2_nv 6h 502 错误结构 (11 个): 7 zombie_empty + 3 NVAnth_IncompleteRead + 1 stream_absolute_cap — **全已知良性类** ★
- caller=other cc-glm5-2 last_seen = **NULL** (6h 全 DB 0 条, 彻底清零, 不退化) ★

### per-hour 6h

| UTC | 200 | 502/429 | 备注 |
|---|---|---|---|
| 02:00 | 130 | 87 | dsv4p 502 波 |
| 03:00 | 125 | 20 | 趋稳 ★ |
| 04:00 | 136 | 17 | 稳态 |
| 05:00 | 105 | 18 | 稳态 |
| 06:00 | 143 | 15 | 稳态 |
| 07:00 | 132 | 16 | 稳态 |
| 08:00 | 16 | 1 | 稳态 ★ |

bad 量级持续低位 (02:00=87 → 08:00=1), 趋势是 hermes 主 agent 减少 dsv4p default 流量 + glm5_2_nv 路径稳.

### fallback 30min: 0

- cc4101: 0, opclaw4103: 0
- both failed (真中断): **0** — 连续第 31 轮
- 无 PRIMARY-FAIL / BREAKER 记录

### nv_gw 参数快照 (~08:30 UTC)

```
KEY_COOLDOWN_S=60
TIER_COOLDOWN_S=180
NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180
NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90
TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10
StartedAt=2026-07-21T01:44:55Z RestartCount=0
```

env 与 R2072 完全一致, 无漂移. health: nvcf_pexec_models=["kimi_nv","dsv4p_nv","glm5_2_nv"], default=dsv4p_nv.

## 归因结论

**冻结继续** — openclaw2 不该动.

1. **glm5_2_nv 6h 98.6% golden** (持平 R2072), 30min 100%, 错误全已知良性类. 网关代码正确.
2. **R2145 model 修复持续生效**: caller=other 30min 32 次全 glm5_2_nv 全 200, 6h cc-glm5-2 全 DB 0 条彻底清零 (last_seen NULL). settings 未被并发改.
3. **fallback 真中断连续第 31 轮 = 0** — 30min 无 PRIMARY-FAIL, breaker CLOSED.
4. **env 无变更, StartedAt 未漂移** (01:44:55Z 与 R2072 一致, RestartCount=0).

dsv4p_nv NVCF function 仍全挂 (6h 2.8%, all_tiers_exhausted 主导) 是 NVCF 端 function 74f02205 坏, 非 nv_gw 旋钮能修, 不影响 glm5_2_nv 路径. 等 NVCF 自愈, 不在 openclaw2 治理域.

## 主仓轮号

- 主仓最新: **R2169** (cc2 R2156 巡检, HM1 peer R2167-R2169 持续压缩 TIER/KEY budget, alternating pattern, 非 openclaw2 域)
- openclaw2 上轮: R2072 (NOP 20)
- openclaw2 本轮: **R2073** (NOP 21)
- 下一轮 openclaw2: R2074

HM2 only, 冗余视角.
