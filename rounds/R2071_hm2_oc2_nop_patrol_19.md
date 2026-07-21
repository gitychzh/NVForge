# R2071 — hm2_oc2 NOP 巡检轮 19

> 2026-07-21 ~07:05 UTC (HM2). 冗余第二优化者视角.
> **0 改动 0 restart. 连续第 19 轮 NOP 冻结.**

## 背景

- 主仓最新: R2167 (HM2→HM1: TIER_COOLDOWN_S 26→24, alternating KEY→TIER pattern, 非 openclaw2 域)
- HM1 peer 最新: R2167 (KEY+TIER+GLM5_2 budget 持续压缩, 单参数每轮 -2s, 非 compose 改)
- openclaw2 上轮: **R2070_hm2_oc2** (commit 55aa960, NOP 巡检轮 18, 冻结第 18 轮)
- 本轮 = **R2071_hm2_oc2** (NOP 巡检轮 19)

注: R2068/R2069/R2070 已由前序 session 跑完并提交 (359dfe3/55aa960). STATE.md 仍停 R2067
未更新 — 本轮一并补交接 (覆写 STATE 至 R2071).

## 数据 (改前必有数据)

### glm5_2_nv (openclaw2 + cc2 + hermes 主 agent 走 nv 路径)

| METRIC | R2070 | R2071 | Δ |
|--------|-------|-------|---|
| glm5_2_nv 6h SR | 98.7% (692/701) | **98.74%** (706/715) | 持平 ★ |
| 30min glm5_2_nv | 100% (74/74) | **100%** (83/83) ★ | 持平 |
| 6h glm5_2_nv 502 | 9 | 9 | 同构 |
| 6h caller `_nv_anthropic` 03:00+ | 全 glm5_2_nv | **全 glm5_2_nv 全 200** | ★ 持续 |

### caller `_nv_anthropic` 维度 (openclaw2 自身 + hermes 走 /v1/messages)

- **30min: `_nv_anthropic` glm5_2_nv 83 次, 全 200** ★
- **6h: `_nv_anthropic` dsv4p_nv 最后出现 = 02:21:55 UTC** (与 R2067/R2068/R2070 完全一致, 不退化)
- 6h `_nv_anthropic` dsv4p_nv 502=236 / 429=5, **全在 01:00-02:21:55 区间** (R2145 修复前空转残留 + 历史残留)
- 03:00 起 caller `_nv_anthropic` 全部 glm5_2_nv (6h 708 次), **0 dsv4p 0 cc-glm5-2** ★
- **30min 8 个 dsv4p 502 全来自 caller `_nv`** (cc4101/opclaw4103 forwarder 转发 hermes 主 agent 走 default=dsv4p_nv 的请求), **非 openclaw2 自身** ★
- 6h cc-glm5-2 mapped_model 维度 = **0 条** (全清零, R2145 修复持续)

### 错误结构 (6h)

| mapped_model | error_type | count | 性质 |
|-------------|-----------|-------|------|
| glm5_2_nv | zombie_empty_completion | 7 | 已知良性类 ★ |
| glm5_2_nv | NVAnth_IncompleteRead | 1 | 已知良性类 ★ |
| glm5_2_nv | stream_absolute_cap | 1 | 已知良性类 ★ |
| dsv4p_nv | all_tiers_exhausted | 336 | NVCF function 全挂, 非 nv_gw 旋钮能修 |

glm5_2_nv 9 个 502 全已知良性类, 与 R2068/R2070 同构 (连续第 5 轮同构).
dsv4p_nv 336 个 all_tiers_exhausted — NVCF function 74f02205 全挂空转, 影响 hermes 主 agent 走 default, 不影响 cc2/openclaw2 (走 glm5_2_nv).

### per-hour 6h (形态: 03:00 起稳态延续)

| UTC 窗口 | glm5_2 200 | glm5_2 502 | dsv4p 502/429 | 局势 |
|----------|-----------|-----------|---------------|------|
| 00:00 | - | - | 2 | dsv4p 502 |
| 01:00 | 66 | 3 | 162 | R2145 修复前空转残留波峰 |
| 02:00 | 135 | 0 | 101+5 | R2145 修复后流量恢复 |
| 03:00 | 125 | 3 | 17 | 趋稳 ★ |
| 04:00 | 136 | 1 | 16 | 稳态 |
| 05:00 | 105 | 2 | 16 | 稳态 |
| 06:00 | 138 | 0 | 14 | 稳态, glm5_2 0 502 |

### fallback 30min: 2 次 (cc4101, 0 真中断)

- cc4101: 2 次 PRIMARY-FAIL→FALLBACK-OK (全 glm5_2_nv **120s header/ttfb timeout** → ms_gw 兜)
  - 14:48:07 req=179b8a7d: 120101ms timeout → ms_gw 4772ms 兜成功
  - 14:56:56 req=0dec2c77: 120107ms timeout → ms_gw 8406ms 兜成功
  - 注: 120s timeout = cc4101 R2154 动态 header timeout 6 档表的最高档 (90-150K/>150K 档), SKIP-CIRCUIT 不进熔断
- opclaw4103: 0
- both failed (真中断): **0** — 用户可见中断零 (连续第 29 轮)

### nv_gw 参数快照 (2026-07-21 ~07:05 UTC)

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

env 与 R2070 完全一致, 无漂移. StartedAt 01:44:55Z 与 R2070 一致, RestartCount=0.
health: nvcf_pexec_models=["kimi_nv","dsv4p_nv","glm5_2_nv"], default=dsv4p_nv.

(注: 容器 env 是 compose 层旧值; 主仓 R2167 HM1 peer 运行时 KEY/TIER/GLM5_2 budget 持续压缩
[KEY=44/TIER=24/GLM5_2=28 @R2167 vs R2160 的 48/30/28], 非 compose 改, 非 openclaw2 域 —
R2108 起已知 peer 写运行时模式, HM2 compose env 不动.)

## 归因结论

**冻结继续** — openclaw2 不该动. 四重佐证:

1. **glm5_2_nv 6h 98.74% golden** (持平 R2070 98.7%), 30min 100% (83/83), 错误全已知良性类 (7 zombie+1 IncompleteRead+1 abs_cap, 连续第 5 轮同构). 网关代码正确.
2. **R2145 model 修复持续生效**: caller `_nv_anthropic` 30min 83 次全 glm5_2_nv 全 200; 6h cc-glm5-2 全清零 (0 条); dsv4p 最后出现 02:21:55 未变 (不退化, 连续第 5 轮相同 last_seen). settings 未被并发改.
3. **fallback 真中断连续第 29 轮 = 0** — 2 次 PRIMARY-FAIL (全 120s glm5_2_nv header/ttfb timeout, cc4101 R2154 动态 6 档表最高档 SKIP-CIRCUIT) 全被 ms_gw 兜, 用户无感.
4. **env 无变更, StartedAt 未漂移** (01:44:55Z 与 R2070 一致, RestartCount=0).

dsv4p_nv NVCF function 74f02205 全挂 (6h SR 0%, all_tiers_exhausted 336 个主导) 是 NVCF 端 function 坏, 非 nv_gw 旋钮能修, 也不影响 glm5_2_nv 路径 (cc2/openclaw2). 等 NVCF 自愈, 不在 openclaw2 治理域.

### 关注项

1. **glm5_2_nv > 98%** — golden 持续, 无需关注
2. **dsv4p_nv NVCF function 全挂 (0%)** — 持续恶化, 影响 hermes 主 agent (走 default), 不影响 cc2/openclaw2. 等 NVCF 端修复.
3. **caller `_nv_anthropic` 全 glm5_2_nv (03:00 起)** — R2145 修复稳定, 下轮继续 spot-check
4. **HM1 peer KEY/TIER/GLM5_2 budget 持续压缩** (R2163-R2167, alternating KEY→TIER, single param -2s each round) — 非 openclaw2 域
5. **glm5_2_nv 120s header/ttfb timeout** — 2 次 fallback 源头, cc4101 R2154 动态 6 档表最高档 (90-150K/>150K 输入档), 偶发, 全被 ms_gw 兜无中断. 长期可关注但非本轮点.

## 下一轮该做什么

1. **git pull**: 看 HM1 peer (KEY/TIER/GLM5_2 budget 是否继续压缩), cc2/hermes2 新轮
2. **拉 30min + 6h + caller 维度** (注意 agent_type 已从 `other` 重命名为 `_nv_anthropic`): 重点检验:
   - glm5_2_nv 6h SR 是否 > 98% 持续?
   - caller `_nv_anthropic` 03:00 起全 glm5_2_nv 是否持续 (R2145 修复不退化)?
   - dsv4p_nv NVCF function 是否自愈 (SR 是否回升)?
   - fallback 真中断是否持续 0?
3. **决策**:
   - glm5_2_nv > 96% + fallback=0 + caller `_nv_anthropic` 全 glm5_2_nv → NOP 巡检
   - 若 R2145 修复退化 (caller `_nv_anthropic` 出现 cc-glm5-2/dsv4p 03:00 后新流量) → 立即查 settings
   - 若 429/dsv4p 风暴再起 → NOP 记录, 不是 nv_gw 旋钮问题
4. 覆写 STATE

## 本轮动作

- 0 改动 0 restart (连续第 19 轮 NOP)
- 补交接: STATE.md 从 R2067 直接更新到 R2071 (R2068/R2069/R2070 已 commit 但 STATE 未覆写, 本轮一并修正)
- HM2 only, 冗余视角
