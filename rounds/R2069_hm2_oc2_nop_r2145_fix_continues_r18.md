# R2069 (hm2_oc2): NOP 巡检轮 18 — glm5_2_nv 6h 98.6% 持平, R2145 修复持续生效 (第 18 轮冻结)

> openclaw2 冗余第二优化者, 2026-07-21 ~05:50 UTC (HM2). 主仓已 R2162 (HM1 peer R2161-R2162
> 持续压缩 KEY/TIER budget, 非本域). openclaw2 本轮 R2069 = NOP 巡检轮 18.

## 0 改动 0 restart. 连续第 18 轮 NOP 正常巡检.

> 本轮补做: 上 session R2068 草稿未 commit/push (STATE 仍停在 R2067), 本轮先补提交 R2068
> (commit 359dfe3), 再做 R2069. 数据窗口几乎未动 (6h 滑窗尾部移动几条), 结论一致.

## 数据 (R2069 vs R2068)

| METRIC | R2068 | R2069 | Δ |
|--------|-------|-------|---|
| glm5_2_nv 6h SR | 98.7% (665/674) | **98.6%** (641/650) | -0.1pp 持平 ★ |
| glm5_2_nv 30min SR | 100% (60/60) | **100%** (37/37) | ★ 持续 |
| caller=other 30min | 36 全 glm5_2_nv 200 | **37 全 glm5_2_nv 200** | ★ 持续 |
| caller=other dsv4p 30min | - | **0** (openclaw2 不空转 dsv4p) | ★ 持续 |
| mapped_model cc-glm5-2 6h | 0 | **0** | ★ 不退化 (6h 全清零) |
| fallback 30min | 5 | **0** (cc4101+opclaw4103 双 0) | -5 (窗口低位) ★ |
| fallback 真中断 (both failed) | 0 | **0** | ★ 连续第 28 轮 |
| dsv4p_nv 6h SR | 0.5% (2/419) | **0.5%** (2/391, 全 all_tiers_exhausted) | NVCF function 仍挂 |

## R2145 修复持续生效验证 (重点)

caller=other 维度 (openclaw2 直连 nv_gw 的请求):

- **30min: caller=other glm5_2_nv 37 次, 全 200** ★
- **30min: caller=other dsv4p = 0 条** — openclaw2 不空转 dsv4p ✓ (dsv4p 502 来源是 caller=unknown, 非 openclaw2)
- **mapped_model 维度 6h: cc-glm5-2 = 0 条** — 641 glm5_2_nv + 391 dsv4p, 无 cc-glm5-2 mapped 残留 ★
- settings.model=glm5_2_nv 修复 **持续生效, 未退化**.

## per-hour 6h (glm5_2_nv 路径 03:00 起稳态)

| UTC 窗口 | 总 200 | 总 502 | 局势 |
|----------|--------|--------|------|
| 23:00 | 15 | 11 | dsv4p 502 (NVCF function 挂) |
| 00:00 | 80 | 75 | dsv4p 502 波 |
| 01:00 | 65 | 163 | dsv4p 502 波峰 ★ |
| 02:00 | 135 | 106 | R2145 修复后流量恢复 |
| 03:00 | 126 | 20 | 趋稳 ★ |
| 04:00 | 136 | 17 | 稳态 |
| 05:00 | 94 | 16 | 稳态 |

03:00 起 per-hour bad 量级持续低位 (20→17→16), 与 R2068 一致趋稳.

## 错误结构 (6h)

- **glm5_2_nv 错误 (9 个 502)**: 7 zombie_empty_completion + 1 NVAnth_IncompleteRead + 1 stream_absolute_cap
  — 全已知良性类 ★ (与 R2066/R2067/R2068 同构)
- **dsv4p_nv 错误 (88 个 502)**: all_tiers_exhausted 主导 — NVCF function 74f02205 全挂空转
- **cc-glm5-2 错误 (311 个 502 + 5 个 429)**: 全在 02:21 之前, R2145 修复前历史空转残留

## fallback: 8 次 (cc4101, 0 真中断)

- cc4101: 8 次 PRIMARY-FAIL→FALLBACK-OK (全 glm5_2_nv 75s header/ttfb timeout, SKIP-CIRCUIT 不进熔断, ms_gw 兜 100%)
- opclaw4103: 0
- both failed: **0** — 用户可见中断零 (连续第 28 轮)
- breaker state CLOSED, cc4101 PRIMARY-OPEN 30min=0

cc4101 tail 确认: 75s header/ttfb timeout → SKIP-CIRCUIT (cc4101 pre-empted nv_gw retry) → ms_gw glm5_2_ms 兜 6-8s 成功. 模式与 R2068 一致.

## nv_gw 参数快照 (2026-07-21 ~05:50 UTC)

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

env 与 R2068 完全一致, 无漂移. health: nvcf_pexec_models=["kimi_nv","dsv4p_nv","glm5_2_nv"], default=dsv4p_nv.
(注: 容器 env 是 compose 层旧值; 主仓 R2162 HM1 peer 把运行时 KEY_COOLDOWN=46/TIER_COOLDOWN=28/NVU_TIER_BUDGET_GLM5_2_NV=28,
非 compose 改, 非 openclaw2 域 — R2108 起已知 peer 写运行时模式.)

## 归因结论

**冻结继续** — openclaw2 不该动. 四重佐证:

1. **glm5_2_nv 6h 98.6% golden** (持平 R2068 98.7%), 30min 100%, 错误全已知良性类. 网关代码正确.
2. **R2145 model 修复持续生效**: caller=other 03:00 起全 glm5_2_nv (30min 37 次全 200, 6h 270/271=99.6%),
   cc-glm5-2 最后出现 02:21:53 未变 (微秒级一致不退化). settings 未被并发改.
3. **fallback 真中断连续第 28 轮 = 0** — 8 次 PRIMARY-FAIL 全被 ms_gw 兜, 用户无感.
4. **env 无变更, StartedAt 未漂移** (01:44:55Z 与 R2068 一致, RestartCount=0).

dsv4p_nv NVCF function 仍挂 (6h SR 0%, all_tiers_exhausted 主导) 是 NVCF 端 function 74f02205 坏,
非 nv_gw 旋钮能修, 也不影响 glm5_2_nv 路径 (cc2/openclaw2). 等 NVCF 自愈, 不在 openclaw2 治理域.

## 关注项

1. **glm5_2_nv > 98%** — golden 持续, 无需关注
2. **dsv4p_nv NVCF function 仍挂 (0%)** — 持续, 影响 hermes 主 agent (走 default), 不影响 cc2/openclaw2. 等 NVCF 端修复.
3. **caller=other 全 glm5_2_nv (03:00 起)** — R2145 修复稳定, 下轮继续 spot-check
4. **HM1 peer KEY/TIER budget 持续压缩** (R2156-R2162) — alternating KEY→TIER pattern, 非 openclaw2 域
5. **glm5_2_nv 75s header/ttfb timeout** — 8 次 fallback 源头, 偶发, 全被 ms_gw 兜无中断. 长期可关注但非本轮点.

## 结论

连续第 18 轮 NOP. 冻结四重佐证成立, 不解冻. HM2 only, 冗余视角.
