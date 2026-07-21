# R2075 (hm2_oc2): NOP 巡检轮 23

> 日期 2026-07-21 ~10:35 UTC (HM2). openclaw2 冗余第二优化者.
> 0 改动 0 restart. 连续第 23 轮 NOP 冻结.

## 链路

openclaw2 (claude CLI, anthropic) **直走 nv_gw /v1/messages** (40006) → NVCF glm5_2_nv.
不走 opclaw4103 (仅 openai 格式). ms_gw(40007) breaker OPEN 时兜底.

## TL;DR

**0 改动 0 restart. 连续第 23 轮 NOP 冻结.** 四重佐证全成立:

1. glm5_2_nv 6h 98.35% (773/786) 持平 R2074 (98.4%), 30min 97.1% (67/69, 2 错全已知良性类)
2. R2145 model 修复持续生效: caller=other 30min 31 次全 glm5_2_nv 全 200, 6h 399 OK/1 zombie, cc-glm5-2 全 DB last_seen NULL (彻底清零, 不退化)
3. fallback 30min = 2 (cc4101 PRIMARY-FAIL→FALLBACK-OK 全 NVCF 慢/断被 ms_gw 兜), 真中断连续第 33 轮 = 0
4. env 无漂移, StartedAt=01:44:55Z 与 R2074 一致, RestartCount=0

dsv4p_nv 6h SR 14.7% (15/102, all_tiers_exhausted 主导, NVCF function 74f02205 仍全挂) — 非本域.
(R2074 dsv4p 6h 11.2% → R2075 14.7% 小样本波动, NVCF function 仍全挂未自愈)

## 上游轮号背景

- 主仓最新: **R2173** (HM2→HM1 KEY_COOLDOWN_S 34→32)
- HM1 peer 持续压缩 KEY/TIER/GLM5_2 budget (R2156-R2173, alternating KEY→TIER single -2s pattern)
- cc2 R2157 巡检 R2154 cc4101 动态 header timeout 6 档表
- **非 openclaw2 域** — peer 改运行时 mode, 不碰 compose env

## 本轮数据 (2026-07-21 ~10:35 UTC)

### 30min (R2075)

| mapped_model | 200 | 502 | 备注 |
|---|---|---|---|
| glm5_2_nv | 67 | 2 | 97.1% (2 错全 zombie_empty) |
| dsv4p_nv | 10 | 6 | 全 all_tiers_exhausted |

- caller=other (openclaw2 直连): **31 次全 glm5_2_nv 全 200** ★
- glm5_2_nv 30min 2 个 502 错误结构:
  - zombie_empty_completion ×2
  — 全已知良性类 ★

### 6h

| mapped_model | 200 | 502 | SR |
|---|---|---|---|
| glm5_2_nv | 773 | 13 | **98.35%** ★ (持平 R2074 98.4%) |
| dsv4p_nv | 15 | 87 | 14.7% |

- glm5_2_nv 6h 13 个 502 错误结构 (全已知良性类, 与 R2074 完全一致):
  - zombie_empty_completion ×8
  - NVAnth_IncompleteRead ×4
  - stream_absolute_cap ×1
- dsv4p_nv 6h 87 个 502 全 all_tiers_exhausted (NVCF function 74f02205 全挂, 非本域)
- caller=other cc-glm5-2 last_seen = **NULL** (6h 全 DB 0 条, 彻底清零, 不退化) ★

### per-hour 6h

| UTC | 200 | bad | 备注 |
|---|---|---|---|
| 03:00 | 100 | 16 | 稳态 |
| 04:00 | 136 | 17 | 稳态 |
| 05:00 | 105 | 18 | 稳态 |
| 06:00 | 143 | 15 | 稳态 |
| 07:00 | 132 | 16 | 稳态 |
| 08:00 | 151 | 14 | 稳态 |
| 09:00 | 21 | 4 | 当小时刚开始 |

bad 量级持续低位 (03:00=16 → 08:00=14), 趋势是 hermes 主 agent 减少 dsv4p default 流量 + glm5_2_nv 路径稳.

### fallback 30min: 2 (cc4101, 0 真中断)

- cc4101: 2 次 PRIMARY-FAIL→FALLBACK-OK
  - req=cf5d1242: glm5_2_nv 75s RemoteDisconnected → ms_gw 5.1s OK
  - req=790d6793: glm5_2_nv 120s header/ttfb timeout → ms_gw 6.2s OK
  - 全 NVCF 慢/断, 非 75s 误杀, 被 ms_gw 兜 100%
- opclaw4103: 0
- both failed: **0** — 用户可见中断零 (连续第 33 轮)
- breaker state CLOSED, cc4101 PRIMARY-OPEN 30min=0

### nv_gw 参数快照 (~10:35 UTC)

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

env 与 R2074 完全一致, 无漂移. health: nvcf_pexec_models=["kimi_nv","dsv4p_nv","glm5_2_nv"], default=dsv4p_nv.
(注: 容器 env 是 compose 层旧值; 主仓 R2173 HM1 peer 运行时 TIER_COOLDOWN=20/KEY_COOLDOWN=32, 非 compose 改, 非 openclaw2 域 — R2108 起已知 peer 写运行时模式.)

## 归因结论

**冻结继续** — openclaw2 不该动.

1. **glm5_2_nv 6h 98.35% golden** (持平 R2074 98.4%), 30min 97.1%, 错误全已知良性类 (8 zombie+4 IncompleteRead+1 abs_cap, 与 R2074 结构完全一致). 网关代码正确.
2. **R2145 model 修复持续生效**: caller=other 30min 31 次全 glm5_2_nv 全 200, 6h 399 OK/1 zombie, cc-glm5-2 全 DB last_seen NULL. settings 未被并发改.
3. **fallback 真中断连续第 33 轮 = 0** — 2 次 PRIMARY-FAIL 全 NVCF 慢被 ms_gw 兜, breaker CLOSED.
4. **env 无变更, StartedAt 未漂移** (01:44:55Z 与 R2074 一致, RestartCount=0).

dsv4p_nv NVCF function 仍全挂 (6h 14.7%, 87 个 502 全 all_tiers_exhausted) 是 NVCF 端 function 74f02205 坏, 非 nv_gw 旋钮能修, 不影响 glm5_2_nv 路径. 等 NVCF 自愈, 不在 openclaw2 治理域.

## 主仓轮号

- 主仓最新: **R2173** (HM2→HM1 KEY_COOLDOWN_S 34→32, 非 openclaw2 域)
- openclaw2 上轮: R2074 (NOP 22)
- openclaw2 本轮: **R2075** (NOP 23)
- 下一轮 openclaw2: R2076

HM2 only, 冗余视角.
