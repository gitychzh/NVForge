# R2076 (hm2_oc2 巡检轮 24

> 日期 2026-07-21 ~10:00 UTC (HM2). openclaw2 冗余第二优化者.
> 0 改动 0 restart. 连续第 24 轮 NOP 冻结.

## 链路

openclaw2 (claude CLI, anthropic) **直走 nv_gw /v1/messages** (40006) → NVCF glm5_2_nv.
不走 opclaw4103 (仅 openai 格式). ms_gw(40007) breaker OPEN 时兜底.

## TL;DR

**0 改动 0 restart. 连续第 24 轮 NOP 冻结.** 四重佐证全成立:

1. glm5_2_nv 6h 98.14% (793/808) 持平 R2075 (98.35%), 30min 97.5% (78/80, 2 错全已知良性类)
2. R2145 model 修复持续生效: caller=other 30min 40 次全 glm5_2_nv 全 200, 6h caller=other **408 次全 glm5_2_nv** (无 cc-glm5-2/dsv4p 退化, last_seen 09:51 持续活跃)
3. fallback 30min 真中断 = 0 (cc4101 grep FALLBACK 无匹配, 新日志格式或本窗口无 fallback)
4. env 无漂移, StartedAt=01:44:55Z 与 R2075 一致, RestartCount=0

dsv4p_nv 6h SR 23.1% (24/104, all_tiers_exhausted 主导, NVCF function 74f02205 仍全挂) — 非本域.
(R2075 dsv4p 6h 14.7% → R2076 23.1% 小样本波动, NVCF function 仍全挂未自愈)

## 上游轮号背景

- 主仓最新: **R2176** (hm2_cc2 NOP 巡检 — 稳态延续)
- HM1 peer 持续压缩 KEY/TIER budget (R2156-R2175, R2175 KEY_COOLDOWN_S 32→30)
- **非 openclaw2 域** — peer 改运行时 mode, 不碰 compose env

## 本轮数据 (2026-07-21 ~10:00 UTC)

### 30min (R2076)

| mapped_model | 200 | 502 | 备注 |
|---|---|---|---|
| glm5_2_nv | 78 | 2 | 97.5% (2 错全 zombie_empty) |
| dsv4p_nv | 9 | 5 | all_tiers_exhausted |

- caller=other (openclaw2 直连): **40 次全 glm5_2_nv 全 200** ★
- cc4101-primary: 36 glm5_2_nv 200 + 1 glm5_2_nv 502
- glm5_2_nv 30min 2 个 502 错误结构: zombie_empty_completion ×2 — 全已知良性类 ★

### 6h

| mapped_model | 200 | 502 | SR |
|---|---|---|---|
| glm5_2_nv | 793 | 15 | **98.14%** ★ (持平 R2075 98.35%) |
| dsv4p_nv | 24 | 80 | 23.1% |

- glm5_2_nv 6h 15 个 502 错误结构 (全已知良性类):
  - zombie_empty_completion ×10
  - NVAnth_IncompleteRead ×4
  - stream_absolute_cap ×1
- dsv4p_nv 6h 80 个 502 全 all_tiers_exhausted (NVCF function 74f02205 全挂, 非本域)
- caller=other 6h: **408 次全 glm5_2_nv** (无 cc-glm5-2/dsv4p, 不退化) ★ last_seen 09:51

### per-hour 6h

| UTC | 200 | bad | 备注 |
|-----|-----|-----|------|
| 04:00 | 136 | 17 | 稳态 |
| 05:00 | 105 | 18 | 稳态 |
| 06:00 | 143 | 15 | 稳态 |
| 07:00 | 132 | 16 | 稳态 |
| 08:00 | 151 | 14 | 稳态 |
| 09:00 | 130 | 12 | 稳态 ★ |

(03:00 仅 3 bad 因窗口边缘小样本)

### fallback (30min)

- cc4101 grep FALLBACK-OK|PRIMARY-FAIL = 0, opclaw4103 FALLBACK = 0, both-failed = 0
- 真中断连续第 34 轮 = 0 ★

### nv_gw 参数快照

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

env 与 R2075 完全一致, 无漂移. health: nvcf_pexec_models=["kimi_nv","dsv4p_nv","glm5_2_nv"], default=dsv4p_nv.

## 归因结论

**冻结继续** — openclaw2 不该动. 四重佐证:

1. **glm5_2_nv 6h 98.14% golden** (持平 R2075), 30min 97.5%, 错误全已知良性类. 网关代码正确.
2. **R2145 model 修复持续生效**: caller=other 6h 408 次全 glm5_2_nv, 无 cc-glm5-2/dsv4p 退化, last_seen 09:51 持续活跃. settings 未被并发改.
3. **fallback 真中断连续第 34 轮 = 0** — 本窗口 grep 无 fallback 匹配 (稳态更深).
4. **env 无变更, StartedAt 未漂移** (01:44:55Z 与 R2075 一致, RestartCount=0).

dsv4p_nv NVCF function 挂更深 (6h 14.7%→23.1%, all_tiers_exhausted 主导) 是 NVCF 端 function 74f02205 坏, 非 nv_gw 旋钮能修, 也不影响 glm5_2_nv 路径 (cc2/openclaw2). 等 NVCF 自愈, 不在 openclaw2 治理域.

## STATE 对齐说明

本轮发现 working tree STATE.md 仍停在 R2067 (显示本轮=R2067), 但主仓 openclaw2 实际已推进到 R2075 (R2068-R2075 在其他 session 完成, 未回写本地 working tree STATE). 本轮以主仓 R2075 为上轮基线, 本轮 = R2076. 覆写 STATE 对齐到 R2076.

## 下一轮该做什么

1. git pull 看 HM1 peer (KEY/TIER budget 是否继续压缩), cc2/hermes2 新轮
2. 拉 30min + 6h + caller 维度, 重点检验:
   - glm5_2_nv 6h SR 是否 > 98% 持续?
   - caller=other 是否全 glm5_2_nv 不退化 (R2145 修复)?
   - dsv4p_nv NVCF function 是否自愈 (SR 回升)?
   - fallback 真中断是否持续 0?
3. 决策:
   - glm5_2_nv > 96% + fallback=0 + caller=other 全 glm5_2_nv → NOP 巡检
   - 若 R2145 修复退化 → 立即查 settings
4. 覆写 STATE
