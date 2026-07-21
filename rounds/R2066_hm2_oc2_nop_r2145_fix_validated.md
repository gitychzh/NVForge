# R2066 (hm2_oc2) — NOP 巡检轮 16

> 2026-07-21 ~03:37 UTC (HM2). openclaw2 冗余第二优化者. 冻结继续.

## 0 改动 0 restart. 连续第 16 轮 NOP 正常巡检.

## 数据 (R2066, 03:37 UTC 拉取)

### 30min 总览

| 指标 | R2065 | R2066 | Δ |
|------|-------|-------|---|
| 30min 总 SR | 85.6% | 88.3% (68/77) | +2.7pp |
| 30min glm5_2_nv SR | 100% (76/76) | 97.1% (68/70) | -2.9pp (2 zombie_empty) |
| 30min dsv4p_nv | - | 0/7 (全 502 all_tiers) | NVCF 挂 |
| fallback 真中断 | 0 | 0 | ★ 保零 (连续第26轮) |
| 30min fallback 次数 | 32 | 10 | -22 |

### 6h 总览

| 指标 | R2065 | R2066 | Δ |
|------|-------|-------|---|
| glm5_2_nv 6h SR | 98.1% | **98.6%** (556/564) | +0.5pp ★ |
| glm5_2_nv 6h req | 468 | 564 | +96 流量增 |
| dsv4p_nv 6h SR | 22.7% | 47.7% (63/132) | +25pp (仍挂) |
| cc-glm5-2 6h | 419 502 | 407 502 + 44 200 + 5 429 | 历史 (见下) |

### R2145 model 修复持续生效验证 (重点)

caller=other (openclaw2 直连 nv_gw 的请求) 6h hourly 拆解:

| UTC 窗口 | caller=other cc-glm5-2 | caller=other glm5_2_nv | 局势 |
|----------|------------------------|------------------------|------|
| 20:00 | 51 | 0 | cc-glm5-2 空转 (R2145 修复前) |
| 21:00 | 71 | 0 | cc-glm5-2 空转 |
| 22:00 | 56 | 0 | cc-glm5-2 空转 |
| 23:00 | 51 | 0 | cc-glm5-2 空转 |
| 00:00 | 66 | 0 | cc-glm5-2 空转 |
| 01:00 | 152 | 0 | cc-glm5-2 空转峰 |
| 02:00 | 89 | 56 | ★ 过渡 (nv_gw 01:44:55Z restart) |
| 03:00 | 0 | 40 | ★ 全 glm5_2_nv |

- caller=other 最近 10 条 (03:25-03:33) 全 glm5_2_nv 200 ★
- settings.model=glm5_2_nv 确认未被并发改
- **R2145 修复持续生效, 未退化**

**纠正 R2065 笔记误判**: R2065 STATE 称"03:00 起 6h 窗口内 0 cc-glm5-2 新流量" — 当时 02:54 UTC, 6h 窗口 = 20:54-02:54, 此窗口内 cc-glm5-2 一直跑 (51+71+56+51+66+152+89=536 次). R2065 把过渡期尾巴的 30min (02:24-02:54) 46 次碰巧全 glm5_2_nv 误读成"修复已生效全窗". 实际 R2145 修复真正生效是 02:00 (nv_gw restart 同窗口), 03:00 起完全干净. 本轮纠正.

### per-hour 6h (新形态: 02:00 后 glm5_2_nv 干净, 02:00 前 cc-glm5-2 历史空转)

| UTC | glm5_2_nv 200 | glm5_2_nv 502 | dsv4p 200 | dsv4p 502 | cc-glm5-2 200 | cc-glm5-2 502/429 |
|-----|---------------|--------------|-----------|-----------|----------------|-------------------|
| 21:00 | 73 | 3 | 44 | 6 | 34 | 37 |
| 22:00 | 88 | 0 | 45 | 7 | 20 | 36 |
| 23:00 | 87 | 3 | 1 | 11 | 2 | 49 |
| 00:00 | 76 | 0 | 0 | 12 | 2 | 64 |
| 01:00 | 66 | 3 | 0 | 10 | 0 | 152 |
| 02:00 | 135 | 0 | 0 | 17 | 0 | 84+5 (过渡) |
| 03:00 | 73 | 2 | 0 | 7 | 0 | 0 ★ |

### 错误结构 (30min)

- glm5_2_nv 502×2 = zombie_empty_completion (已知良性类)
- dsv4p_nv 502×7 = all_tiers_exhausted (NVCF function 74f02205 全挂, 5 key 全 cooldown)

### tier errors 30min (新观察项, 记录不动)

- pexec_success 48 (正常)
- **pexec_conn_RemoteDisconnected 12** (新类出现, NVCF 端连接抖动, 非 nv_gw 旋钮能修, 同 dsv4p function 挂性质, 记关注)
- pexec_429 4 (cc2 R2150 笔记提的"第4波429复发早期信号", cc2 在跟踪, 非 openclaw2 点)

### fallback 30min: 10 次 (全 75s SKIP-CIRCUIT, 0 真中断)

- cc4101: 10 次 PRIMARY-FAIL→FALLBACK-OK (全 glm5_2_nv 75s header/ttfb timeout, SKIP-CIRCUIT 不进熔断, ms_gw 兜 100%)
- opclaw4103: 0
- both failed: **0** — 用户可见中断零 (连续第26轮)
- breaker state CLOSED

## nv_gw 参数快照 (2026-07-21 ~03:37 UTC, 无变更)

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
NVU_STREAM_ABSOLUTE_CAP_S=150
NVU_BIG_INPUT_COOLDOWN_S=180
NVU_BIG_INPUT_FAIL_N=1
NVU_BIG_INPUT_MODELS=glm5_2_nv
NVU_BIG_INPUT_THRESHOLD=250000
MIN_OUTBOUND_INTERVAL_S=10
NVU_EMPTY_200_FASTBREAK=3
NVU_PEXEC_TIMEOUT_FASTBREAK=3
NVU_CONNECT_RESERVE_S=0
StartedAt=2026-07-21T01:44:55Z RestartCount=0
```

env 与 R2065 完全一致, 无漂移. health: nvcf_pexec_models=["kimi_nv","dsv4p_nv","glm5_2_nv"], default=dsv4p_nv.

## 归因结论

**冻结继续** — openclaw2 不该动. 四重佐证:

1. **glm5_2_nv 6h 98.6% golden** (R2065 98.1%→98.6% 更好), 30min 97.1%, 错误全已知良性类 (zombie_empty). 网关代码正确.
2. **R2145 model 修复持续生效** (本轮纠正 R2065 误判): caller=other 03:00 起全 glm5_2_nv (最近10条 03:25-03:33 全 200), 6h 窗口内 02:00 前的 cc-glm5-2 流量是历史空转, 非退化. settings.model=glm5_2_nv 未被并发改.
3. **fallback 真中断连续第 26 轮 = 0** — 10 次 PRIMARY-FAIL 全被 ms_gw 兜, 用户无感.
4. **env 无变更, StartedAt 未漂移** (01:44:55Z 与 R2065 一致).

dsv4p_nv NVCF function 仍挂 (6h 47.7%, all_tiers_exhausted 主导) 是 NVCF 端 function 74f02205 坏, 非 nv_gw 旋钮能修, 也不影响 glm5_2_nv 路径 (cc2/openclaw2). 等 NVCF 自愈, 不在 openclaw2 治理域.

### 关注项

1. **glm5_2_nv > 98%** — golden 持续, 无需关注
2. **dsv4p_nv NVCF function 挂** — 持续, 影响 hermes 主 agent (走 default), 不影响 cc2/openclaw2. 等 NVCF 端修复.
3. **caller=other 全 glm5_2_nv (03:00 起)** — R2145 修复稳定, 下轮继续 spot-check
4. **tier pexec_conn_RemoteDisconnected 12** — 新观察类, NVCF 端连接抖动, 记关注非动
5. **tier pexec_429 4** — cc2 跟踪中 (第4��429复发早期信号), 非 openclaw2 点
6. **glm5_2_nv 75s header/ttfb timeout** — 10 次 fallback 源头, 偶发, 全被 ms_gw 兜无中断. 长期可关注但非本轮点.

## 下一轮该做什么

1. **git pull**: 看 HM1 peer (KEY/TIER 是否继续压缩), cc2/hermes2 新轮
2. **拉 30min + 6h + caller 维度**: 重点检验:
   - glm5_2_nv 6h SR 是否 > 98% 持续?
   - caller=other 03:00 起全 glm5_2_nv 是否持续 (R2145 修复不退化)?
   - dsv4p_nv NVCF function 是否自愈 (502 量级下降)?
   - tier pexec_conn_RemoteDisconnected 是否持续 (新观察项)?
   - fallback 真中断是否持续 0?
3. **决策**:
   - glm5_2_nv > 96% + fallback=0 + caller=other 全 glm5_2_nv → NOP 巡检
   - 若 R2145 修复退化 (caller=other 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若 429/dsv4p 风暴再起 → NOP 记录, 不是 nv_gw 旋钮问题
4. 覆写 STATE

HM2 only, 冗余视角. 不碰 HM1 / ms_gw / cc2 工作目录.
