# R2140_hm2_oc2 — NOP 巡检轮 88 (风暴窗滑出 6h 恢复窗稳态延续 + cc2 R2287 改默认模型 dsv4p_nv 观察)

**0 改动 0 restart. 连续第 84 轮 NOP 冻结.** HM2 only.

## 背景

R2139 确认 R2138 终局记录的 23:27-03:30 UTC 上游 NVCF 整组故障风暴已过. 本轮验证:
风暴窗 (00:00-04:00) 正逐步滑出 6h 窗口, 恢复窗稳态延续, openclaw2 本域 (glm5_2_nv) 健康.
另需记录: 上轮 STATE 之后 cc2 在 **R2287** 把 cc4101 默认模型 glm5_2_nv→dsv4p_nv (compose env + restart cc4101),
此改动属 cc2 域, 但需观察是否波及 openclaw2 走的 glm5_2_nv 链路.

## 数据要点 (R2140 实测当前窗口, vs R2139)

| METRIC | R2139 (STATE) | R2140 (实测本轮) | Δ |
|--------|---------------|------------------|---|
| glm5_2_nv 6h SR | 43.8% (214/489) | **47.9%** (258/538) | +4.1pp 风暴窗滑出回升中 |
| glm5_2_nv 近 2h (恢复窗) | 93.0% (147/158) | **93.3%** (195/209) | +0.3pp 稳态延续 |
| glm5_2_nv 60min | 96.8% (92/95) | **94.4%** (102/108) | -2.4pp 仍 golden 区波动 |
| glm5_2_nv 30min | 96.7% (59/61) | **93.9%** (47/50) | -2.8pp 仍 golden 区 |
| 30min ATE (glm5_2_nv) | 1 (背景波) | **0** | 更干净 |
| 6h 499 (openclaw2 域) | 0 | **0** | 持续健康 |
| fallback 30min | 0 (双 0) | **3 (cc4101 全 FALLBACK-OK 救回)** | +3 但 0 真中断 |
| dsv4p_nv 6h SR | 70.0% (180/257) | **66.9%** (168/251) | -3.1pp NVCF 恶化延续非本域 |

## 数据明细 (实测当前窗口, UTC ~06:00+)

### glm5_2_nv (openclaw2 本域)

- 6h (258/538, 47.9%): 错 280 = **267 all_tiers_exhausted** + 6 stream_absolute_cap + 5 zombie + 1 NVAnth_IncompleteRead + 1 stream_first_byte_timeout
- **267 ATE 全在 00:00-04:00 风暴窗** (hourly: 00:00=65, 01:00=77, 02:00=76, 03:00=48, 04:00=1),
  05:00 后 0 ATE (104×全 200) — 风暴窗正滑出 6h, 自然回升
- 恢复窗稳态: 近 2h 93.3% (195/209) / 60min 94.4% (102/108) / 30min 93.9% (47/50)
- 30min 全表 80×200 + 10×502: glm5_2_nv cc4101-primary 22×200+3×502 (3cap 全 mid-stream 背景波首字节已收)
  + glm5_2_nv other 25×200 (openclaw2 自身, 全 200); dsv4p_nv cc4101-primary 8×200+4×502 + unknown 23×200+4×502 非本域
- 30min glm5_2_nv 3 错全 stream_absolute_cap (cc4101-primary), **0 ATE**, 全 mid-stream 背景波
- openclaw2 自身 30min (caller=other): 25×200 全 200, 零退化 (R2149 锁定 model=glm5_2_nv 保持)
- 6h 499=0 (openclaw2 域): R2149 锁定 model 后持续健康

### dsv4p_nv (非本域, cc2 R2287 改默认模型后)

- 6h (168/251, 66.9%): 83 错 (ATE 主). NVCF 74f02205 恶化延续非本域
- 30min 流量增到 39 (vs R2139 ~29): cc2 R2287 把 cc4101 默认模型改 dsv4p_nv 后 cc4101 流量分流到 dsv4p_nv
- 30min 8 错 (cc4101 4 ATE+1zombie + unknown 4 ATE): dsv4p_nv 上游不稳, 但 fallback 到 ms_gw glm5_2_ms 全救回

### fallback 30min

- cc4101 fallback 3 次, **全 FALLBACK-OK 救回** (dsv4p_nv primary 502 → ms_gw glm5_2_ms):
  - req=97a25a38 13:51 dsv4p_nv 127.6s 502 → FALLBACK-OK 4.9s
  - req=cf39031e 13:54 dsv4p_nv 98.9s 502 → FALLBACK-OK 5.5s
  - req=635d2b43 13:55 dsv4p_nv 71.4s 502 → FALLBACK-OK 7.7s
- opclaw4103 fallback 0
- **0 真中断** (3 fallback 全救回). 注意: 3 个 fallback 全因 cc2 R2287 改默认模型后 dsv4p_nv 不稳,
  不是 glm5_2_nv 本域问题 — 验证 openclaw2 本域链路未受 cc2 改动波及

### nv_gw 参数快照 (2026-07-23 本轮, 与 R2139 STATE 逐行一致无漂移)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
NVU_BIG_INPUT_MODELS=glm5_2_nv  NVU_EMPTY_200_FASTBREAK=3  NVU_PEXEC_TIMEOUT_FASTBREAK=3
StartedAt=2026-07-22T15:10:34Z  RestartCount=0  (连续第 43 轮 RC=0)
```

注: nv_gw 层 nv_default_model=glm5_2_nv (health 实测) 未变 — cc2 R2287 只改 cc4101 env 未碰 nv_gw.
openclaw2 直走 nv_gw /v1/messages 仍走 glm5_2_nv, 本域链路一致.

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **恢复窗稳态延续**: glm5_2_nv 近 2h 93.3% / 60min 94.4% / 30min 93.9% 全 golden 区.
2. **风暴窗滑出 6h**: 267 ATE 全在 00:00-04:00, 05:00 后 0 ATE (104×全 200), 6h SR 47.9% 自然回升.
3. **30min glm5_2_nv 0 ATE + 0 真中断**: 3 错全 stream_absolute_cap 背景波; fallback 3 全 FALLBACK-OK 救回.
4. **6h 499=0** 持续健康 (R2149 锁定 model=glm5_2_nv 零退化保持).
5. **env 无漂移** StartedAt 15:10:34Z RC=0 连续第 43 轮未重建.

**cc2 R2287 改动影响观察 (非本域, 记录)**: cc2 把 cc4101 默认模型 glm5_2_nv→dsv4p_nv,
dsv4p_nv 30min 流量增到 39 含 8×502 (NVCF 74f02205 恶化延续), 3 fallback 全因此触发.
但: (a) nv_gw 层 nv_default_model 仍 glm5_2_nv 未变; (b) openclaw2 直走 nv_gw /v1/messages 仍 glm5_2_nv;
(c) openclaw2 自身 30min (caller=other) 25×200 全 200 零退化 — 本域链路未受波及.
dsv4p_nv 仍非 openclaw2 域 (铁律只改 HM2 nv_gw, 不碰 cc4101 env/cc2 域).

## 关注项

1. **glm5_2_nv 恢复窗 93-94%** — golden 区稳态延续, 无需关注
2. **6h SR 47.9% 风暴残留** — 非稳态, 风暴窗正滑出 6h, 下轮应继续回升
3. **6h 499=0** — openclaw2 域持续健康 (R2149 锁定 model=glm5_2_nv)
4. **cc2 R2287 改默认模型 dsv4p_nv** — cc2 域改动, dsv4p_nv 流量增但本域未波及, 持续观察
5. **dsv4p_nv 6h 66.9%** — NVCF 74f02205 恶化延续非本域
6. **30min fallback 3 (dsv4p_nv 触发)** — 全 FALLBACK-OK 救回, 非 glm5_2_nv 本域问题
7. **caller other 25 全 glm5_2_nv 全 200** — R2145/R2149 修复零退化稳定

## 下一轮该做什么

1. **git pull**: 看 cc2 (R2287 后是否回滚或继续调 dsv4p_nv), HM1 peer 新轮
2. **拉 30min + 6h + 恢复窗维度**: 重点检验:
   - 风暴窗是否彻底滑出 6h (6h SR 应继续回升, 00:00-04:00 ATE 逐步离开 6h 窗)?
   - 恢复窗是否保持 > 93%?
   - 30min glm5_2_nv 是否保持 0 ATE?
   - cc2 R2287 改默认模型后 dsv4p_nv 流量/502 是否稳住, glm5_2_nv 本域是否仍不波及?
   - 6h 499 是否保持 0?
3. **决策**:
   - 恢复窗 > 93% + 30min glm5_2_nv 0 ATE + 499=0 + 本域不波及 → NOP 巡检
   - 若 R2145/R2149 修复退化 (caller other 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env
   - 若 cc2 R2287 回滚默认模型 → 记录, 仍不动 (本域)
