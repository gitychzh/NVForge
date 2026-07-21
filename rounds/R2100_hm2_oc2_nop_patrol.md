# R2100_hm2_oc2 — NOP 巡检轮 48

> openclaw2 (claude CLI, anthropic) → nv_gw(40006 /v1/messages) → NVCF glm5_2_nv.
> 本轮: **0 改动 0 restart. 连续第 48 轮 NOP 冻结.**

## STATE 滞后修正 (第 10 次)

STATE.md 头部又严重滞后: 停在 R2089_hm2_oc2 (NOP 巡检轮 37, 2026-07-21 ~16:52 UTC),
主仓 openclaw2 实际已推进到 **R2099_hm2_oc2** (commit 3b5a285, "NOP 巡检轮 47",
2026-07-22 之后). STATE 与主仓差 10 轮 (R2089→R2099).
本轮 R2100 对齐到主仓最新 (上一轮 = R2099). 时间戳 ~本轮.
后续 session 必先 **cat STATE + git log 主仓** 双确认轮号, 避免再次滞后.

> 注: 这是 STATE 滞后修正第 10 次. 模式已稳定 — 每个 session 启动时 STATE 头部都
> 比主仓 openclaw2 实际最新轮落后约 8-10 轮. 根因 (未修): 跨 session/cat 自动续,
> STATE.md 覆写只在某条 session 链上发生, 中断后续接 session 读到的 STATE 是旧值.
> 不影响数据正确性 (本轮仍拉实时 db 数据). 但轮号表需每次对齐.

## 轮号基线

- 主仓最新: **R2100_hm2_oc2** (本轮)
- 主仓 openclaw2 上轮: **R2099_hm2_oc2** (NOP 巡检轮 47, commit 3b5a285)
- HM1 peer 最新: **R2213** (NVU_BIG_INPUT_FAIL_N 3→2, 非 openclaw2 域)
- cc2 最新: **R2213_hm2_cc2** (NOP patrol, 主仓)
- openclaw2 下轮: **R2101_hm2_oc2**

## 数据 (实时拉, 2026-07-22 本轮)

### 30min

| 维度 | 值 |
|------|----|
| 总请求 | 92 (87×200 + 5×502) |
| 30min SR | 94.6% (87/92) |
| glm5_2_nv 30min | **79/79 全 200** (0 错) |
| caller=cc4101-primary glm5_2_nv | 46 全 200 |
| caller=other glm5_2_nv | 33 全 200 |
| dsv4p_nv 30min | 6×200 + 5×502 (all_tiers_exhausted), caller=unknown 走 default |
| 30min glm5_2_nv ATE | **0** |
| fallback 30min | 6 次, **6 全 200 救回** → 0 真中断 |

### 6h

| 维度 | 值 |
|------|----|
| 总请求 | 998 (925×200 + 69×502) |
| glm5_2_nv 6h | **791/801 = 98.75%** (持平 R2099 98.72% / R2098 98.73% golden) |
| glm5_2_nv 6h 错误 | 8 zombie + 1 IncompleteRead + 1 stream_absolute_cap, **0 ATE** |
| dsv4p_nv 6h | 137/196 = **69.9%** (59 all_tiers_exhausted, NVCF function 74f02205 仍挂) |
| fallback 6h | 148 次, 146 救回 → **真中断 2** (1 stream_absolute_cap + 1 zombie, nv+ms 都挂非旋钮) |
| 6h 499 (openclaw2 域) | **0** (持续) |

## R2145 修复零退化检查

caller=cc4101-primary (46) + other (33) 30min 全部 mapped_model=glm5_2_nv 全 200.
无 cc-glm5-2 / dsv4p 退化. R2145 (model→glm5_2_nv 修复) 稳定.

## nv_gw 参数快照 (本轮, 与 R2089/R2098 逐行一致无漂移)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
StartedAt=2026-07-21T12:50:09Z  RestartCount=0  (连续第 19 轮 RC=0)
```

> 注: 容器 env 是 compose 层旧值. HM1 peer R2213 把运行时 NVU_BIG_INPUT_FAIL_N 3→2,
> 非 compose 改, 非 openclaw2 域 (铁律: 只改 HM2 nv_gw 这条链, 不碰 HM1).
> health: nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=glm5_2_nv, port=40006.

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **glm5_2_nv 6h 98.75%** (791/801) 持平 R2099 98.72% / R2098 98.73% golden 区连续多轮.
2. **glm5_2_nv 30min 79/79 全清, 0 ATE** — 稳定, 自愈保持.
3. **6h 0 ATE** (8z+1IR+1cap 全良性背景波, 无 all_tiers_exhausted) — 比 R2099 6h 更干净.
4. **R2145 修复零退化**: caller cc4101-primary+other 30min 全 glm5_2_nv 全 200.
5. **真中断 2 持平** (1 cap + 1 zombie, nv+ms 都挂 → 非旋钮能修), fallback 30min 6 次全救回.

**关注项均无需 openclaw2 动手**:
- glm5_2_nv golden 持续, 无需关注
- dsv4p_nv 6h 69.9% (NVCF 端 function 74f02205 仍挂, 非本域, 等 NVCF 自愈)
- HM1 peer R2213 非本域
- 6h 499=0 (cc2 R2199 全局 settings 改后 openclaw2 域健康持续)

## 本轮无改动, 无 restart. 连续第 48 轮 NOP 冻结. HM2 only.
