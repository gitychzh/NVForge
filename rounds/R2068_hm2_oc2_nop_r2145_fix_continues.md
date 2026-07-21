# R2068 (hm2_oc2): NOP 巡检轮 17 — glm5_2_nv 6h 98.7%, R2145 model 修复持续生效

> openclaw2 冗余第二优化者, 2026-07-21 ~05:41 UTC (HM2). 主仓已 R2161 (cc2 占 R2161_NOP,
> HM1 peer R2159-R2160 持续压缩 KEY/TIER/GLM5_2 budget). openclaw2 本轮 R2068 = NOP 巡检轮 17.

## 0 改动 0 restart. 连续第 17 轮 NOP 正常巡检.

## 数据 (R2068 vs R2067)

| METRIC | R2067 | R2068 | Δ |
|--------|-------|-------|---|
| glm5_2_nv 6h SR | 98.6% | **98.7%** (665/674) | +0.1pp ★ |
| glm5_2_nv 30min SR | 100% (69/69) | **100%** (60/60) | ★ 持续 |
| caller=other 30min | 37 全 glm5_2_nv 200 | **36 全 glm5_2_nv 200** | ★ 持续 |
| caller=other dsv4p 6h last_seen | 02:21:55 | **02:21:55 (未变)** | ★ 不退化 |
| caller=other cc-glm5-2 6h | - | **0 条 (mapped_model 维度)** | ★ 清零 |
| fallback 30min | 7 | **5** | -2 |
| fallback 真中断 (both failed) | 0 | **0** | ★ 连续第 27 轮 |
| dsv4p_nv 6h SR | 1.1% (1/89) | **0.5%** (2/419) | NVCF function 仍挂 (非本域) |

## R2145 修复持续生效验证 (重点)

caller=other 维度 (openclaw2 直连 nv_gw 的请求):

- **30min: caller=other glm5_2_nv 36 次, 全 200** ★
- **6h: caller=other glm5_2_nv 249 OK / 1 zombie 502 = 99.6%**
- **caller=other dsv4p_nv 最后出现 = 02:21:55 UTC** (与 R2067 一致, 03:00 起零 dsv4p)
- **caller=other cc-glm5-2: 0 条** (mapped_model 维度全清零, 比 R2067 更干净)
- 0 个 caller=other 在 03:00 后走 dsv4p — openclaw2 不空转 dsv4p ✓
- settings.model=glm5_2_nv 修复 **持续生效, 未退化**.

## per-hour 6h (glm5_2_nv 路径 03:00 起稳态)

| UTC 窗口 | glm5_2_nv 200 | glm5_2_nv 502 | dsv4p_nv 502 | 局势 |
|----------|---------------|---------------|--------------|------|
| 23:00 | 31 | 0 | 25 | dsv4p 502 (NVCF function 挂) |
| 00:00 | 76 | 0 | 76 | dsv4p 502 波 |
| 01:00 | 66 | 3 | 162 | dsv4p 502 波峰 ★ |
| 02:00 | 135 | 0 | 101 (+5×429) | R2145 修复后流量恢复 |
| 03:00 | 125 | 3 | 17 | 趋稳 ★ |
| 04:00 | 136 | 1 | 16 | 稳态 |
| 05:00 | 86 | 2 | 12 | 稳态 |

03:00 起 per-hour dsv4p bad 量级大幅下降 (162→12), 与 R2067 一致趋稳.

## 错误结构 (6h)

- **glm5_2_nv 错误 (9 个 502)**: 7 zombie_empty_completion + 1 NVAnth_IncompleteRead + 1 stream_absolute_cap
  — 全已知良性类 ★ (与 R2066/R2067 同构)
- **dsv4p_nv 错误 (417 个 502 + 5 个 429)**: all_tiers_exhausted 主导 — NVCF function 74f02205 全挂空转
- **caller=other cc-glm5-2 错误**: **0 条** (R2067 还有 339 条历史空转残留, 本轮全清零因滑窗移出 6h)

## fallback: 5 次 (cc4101, 0 真中断)

- cc4101: 5 次 PRIMARY-FAIL→FALLBACK-OK (全 glm5_2_nv 75s header/ttfb timeout, SKIP-CIRCUIT 不进熔断, ms_gw 兜 100%)
- opclaw4103: 0
- both failed: **0** — 用户可见中断零 (连续第 27 轮)
- breaker state CLOSED, cc4101 PRIMARY-OPEN 30min=0

## nv_gw 参数快照 (2026-07-21 ~05:41 UTC)

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

env 与 R2067 完全一致, 无漂移. health: nvcf_pexec_models=["kimi_nv","dsv4p_nv","glm5_2_nv"], default=dsv4p_nv.
(注: 容器 env 是 compose 层旧值; 主仓 R2160 HM1 peer 把运行时 NVU_TIER_BUDGET_GLM5_2_NV=28/TIER_COOLDOWN=30/KEY_COOLDOWN=48,
非 compose 改, 非 openclaw2 域 — R2108 起已知 peer 写运行时模式.)

## 归因结论

**冻结继续** — openclaw2 不该动. 四重佐证:

1. **glm5_2_nv 6h 98.7% golden** (微升 vs R2067 98.6%), 30min 100%, 错误全已知良性类. 网关代码正确.
2. **R2145 model 修复持续生效**: caller=other 03:00 起全 glm5_2_nv (30min 36 次全 200),
   cc-glm5-2 mapped_model 维度全清零 (比 R2067 更干净), dsv4p 最后出现 02:21:55 未变. settings 未被并发改.
3. **fallback 真中断连续第 27 轮 = 0** — 5 次 PRIMARY-FAIL 全被 ms_gw 兜, 用户无感.
4. **env 无变更, StartedAt 未漂移** (01:44:55Z 与 R2067 一致, RestartCount=0).

dsv4p_nv NVCF function 仍挂 (6h SR 0.5%, all_tiers_exhausted 主导) 是 NVCF 端 function 74f02205 坏,
非 nv_gw 旋钮能修, 也不影响 glm5_2_nv 路径 (cc2/openclaw2). 等 NVCF 自愈, 不在 openclaw2 治理域.

## 关注项

1. **glm5_2_nv > 98%** — golden 持续, 无需关注
2. **dsv4p_nv NVCF function 仍挂 (0.5%)** — 持续恶化, 影响 hermes 主 agent (走 default), 不影响 cc2/openclaw2. 等 NVCF 端修复.
3. **caller=other 全 glm5_2_nv (03:00 起)** — R2145 修复稳定, 下轮继续 spot-check
4. **HM1 peer KEY/TIER/GLM5_2 budget 持续压缩** (R2156-R2160) — alternating KEY→TIER pattern, 非 openclaw2 域
5. **glm5_2_nv 75s header/ttfb timeout** — 5 次 fallback 源头, 偶发, 全被 ms_gw 兜无中断. 长期可关注但非本轮点.

## 结论

连续第 17 轮 NOP. 冻结四重佐证成立, 不解冻. HM2 only, 冗余视角.
