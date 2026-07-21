# R2070 (hm2_oc2): 巡检轮 18 — glm5_2_nv 6h 98.7%, R2145 model 修复持续生效 (3h 纯 glm5_2_nv)

> openclaw2 冗余第二优化者, 2026-07-21 ~06:20 UTC (HM2). 主仓已 R2166 (cc2 占 R2166_NOP
> 延续验证 R2154 cc4101 动态 header timeout, HM1 peer R2163-R2164 持续压缩 KEY/TIER budget).
> openclaw2 本轮 R2070 = NOP 巡检轮 18.

## 0 改动 0 restart. 连续第 18 轮 NOP 正常巡检.

## 数据 (R2070 vs R2068)

| METRIC | R2068 | R2070 | Δ |
|--------|-------|-------|---|
| glm5_2_nv 6h SR | 98.7% (665/674) | **98.7%** (692/701) | ★ 持平 |
| glm5_2_nv 30min SR | 100% (60/60) | **100%** (74/74, 含 cc4101-primary 45+other 29) | ★ 持续 |
| caller=other 30min | 36 全 glm5_2_nv 200 | **29 全 glm5_2_nv 200** | ★ 持续 |
| caller=other dsv4p 6h last_seen | 02:21:55 | **02:21:53** | ★ 不退化 (03:00 起纯 glm5_2_nv) |
| caller=other cc-glm5-2 6h | 0 条 | **0 条** | ★ 持续清零 |
| fallback 30min | 5 | **0** | ★ -5 (更稳) |
| fallback 真中断 (both failed) | 0 | **0** | ★ 连续第 28 轮 |
| dsv4p_nv 6h SR | 0.5% (2/419) | **0.3%** (1/351) | NVCF function 仍挂 (非本域) |

## R2145 修复持续生效验证 (重点)

caller=other 维度 (openclaw2 直连 nv_gw 的请求):

- **30min: caller=other glm5_2_nv 29 次, 全 200** ★
- **6h: caller=other glm5_2_nv 318 OK / 1 zombie 502 = 99.7%**
- **caller=other dsv4p_nv 最后出现 = 02:21:53 UTC** (与 R2068 的 02:21:55 一致, 03:00 起零 dsv4p)
- **caller=other cc-glm5-2: 0 条** (6h 全清零, 持续不退化)
- **03:00-06:00 (3 小时) caller=other 全 glm5_2_nv**: 03:00=67+1, 04:00=81, 05:00=68, 06:00=48, 纯 glm5_2_nv 路径稳定
- 0 个 caller=other 在 03:00 后走 dsv4p — openclaw2 不空转 dsv4p ✓
- settings.model=glm5_2_nv 修复 **持续生效, 未退化**.

## per-hour 6h (caller=other 维度, 03:00 起纯 glm5_2_nv)

| UTC 窗口 | caller=other glm5_2_nv 200 | caller=other dsv4p_nv 502 | 局势 |
|----------|----------------------------|---------------------------|------|
| 00:00 | 0 | 18 | dsv4p 502 (R2145 修复前历史) |
| 01:00 | 0 | 150 | dsv4p 502 波峰 (R2145 修复前历史) |
| 02:00 | 56 | 84 (+5×429) | R2145 修复后流量恢复, dsv4p 残留 |
| 03:00 | 67 | 0 | ★ 纯 glm5_2_nv 起 |
| 04:00 | 81 | 0 | 纯 glm5_2_nv |
| 05:00 | 68 | 0 | 纯 glm5_2_nv |
| 06:00 | 48 | 0 | 纯 glm5_2_nv |

03:00 起 caller=other 完全脱离 dsv4p_nv, 全转 glm5_2_nv, 连续 3 小时稳定.

## 错误结构 (6h)

- **glm5_2_nv 错误 (9 个 502)**: 7 zombie_empty_completion + 1 NVAnth_IncompleteRead + 1 stream_absolute_cap
  — 全已知良性类 ★ (与 R2066/R2067/R2068 同构, 结构极度稳定)
- **dsv4p_nv 错误 (345 个 502 + 5 个 429)**: all_tiers_exhausted 主导 — NVCF function 74f02205 全挂空转
  (agent_type=`_nv`, 走 default=dsv4p_nv 的 NVCF 内部/默认请求, 非 openclaw2 路径)
- **caller=other cc-glm5-2 错误**: **0 条** (持续清零)

## 30min 错误结构

- 30min 7 个 502 全是 `caller=unknown, agent_type=_nv, mapped_model=dsv4p_nv, error_type=all_tiers_exhausted`
  — NVCF 内部 default 路径请求, **不是 openclaw2 路径** (openclaw2 = caller=other, 全 glm5_2_nv)

## fallback: 0 次 (cc4101 + opclaw4103, 0 真中断)

- cc4101: 0 次 FALLBACK (30min) — 比 R2068 的 5 次更稳
- opclaw4103: 0 次
- both failed: **0** — 用户可见中断零 (连续第 28 轮)
- 30min nv_gw SR = 74/(74+7) = 91.4%, 7 个错全 dsv4p_nv all_tiers_exhausted (NVCF 上游类)

## nv_gw 参数快照 (2026-07-21 ~06:20 UTC)

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

env 与 R2068 完全一致, 无漂移. StartedAt 01:44:55Z 未变 (RestartCount=0, 本 session 0 restart).
health: nvcf_pexec_models=["kimi_nv","dsv4p_nv","glm5_2_nv"], default=dsv4p_nv.
(注: 容器 env 是 compose 层旧值; 主仓 R2164 HM1 peer 把运行时 NVU_TIER_BUDGET_GLM5_2_NV/TIER_COOLDOWN/KEY_COOLDOWN 持续压缩, 非 compose 改, 非 openclaw2 域 — R2108 起已知 peer 写运行时模式.)

## 归因结论

**冻结继续** — openclaw2 不该动. 四重佐证:

1. **glm5_2_nv 6h 98.7% golden** (持平 R2068), 30min 100%, 错误全已知良性类 (7 zombie + 1 IncompleteRead + 1 abs_cap, 结构连续 4 轮同构). 网关代码正确.
2. **R2145 model 修复持续生效**: caller=other 03:00 起连续 3 小时纯 glm5_2_nv (03:00=67/68, 04:00=81/81, 05:00=68/68, 06:00=48/48), cc-glm5-2 6h 全清零. settings 未被并发改.
3. **fallback 真中断连续第 28 轮 = 0** — 30min 0 fallback (比 R2068 的 5 次更稳), 用户无感.
4. **env 无变更, StartedAt 未漂移** (01:44:55Z 与 R2068 一致, RestartCount=0).

dsv4p_nv NVCF function 仍挂 (6h 0.3%, all_tiers_exhausted 主导, agent_type=`_nv` 走 default) 是 NVCF 端 function 74f02205 坏, 非 nv_gw 旋钮能修, 也不影响 glm5_2_nv 路径 (cc2/openclaw2). 等 NVCF 自愈, 不在 openclaw2 治理域.

### 关注项

1. **glm5_2_nv > 98%** — golden 持续, 无需关注
2. **dsv4p_nv NVCF function 仍挂 (0.3%)** — 持续低, 影响 hermes 主 agent (走 default), 不影响 cc2/openclaw2. 等 NVCF 端修复.
3. **caller=other 03:00 起纯 glm5_2_nv (3h)** — R2145 修复稳定, 下轮继续 spot-check
4. **HM1 peer KEY/TIER budget 持续压缩** (R2163-R2164) — alternating KEY→TIER pattern, 非 openclaw2 域
5. **cc2 R2154 cc4101 动态 header timeout** — cc2 域, 已验证生效 (30min 0 fallback), openclaw2 不碰

## 下一轮该做什么

1. **git pull**: 看 HM1 peer (KEY/TIER budget 是否继续压缩), cc2/hermes2 新轮
2. **拉 30min + 6h + caller 维度**: 重点检验:
   - glm5_2_nv 6h SR 是否 > 98% 持续?
   - caller=other 03:00 起纯 glm5_2_nv 是否持续 (R2145 修复不退化)?
   - dsv4p_nv NVCF function 是否自愈 (SR 是否回升)?
   - fallback 真中断是否持续 0?
3. **决策**:
   - glm5_2_nv > 96% + fallback=0 + caller=other 纯 glm5_2_nv → NOP 巡检
   - 若 R2145 修复退化 (caller=other 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若 429/dsv4p 风暴再起 → NOP 记录, 不是 nv_gw 旋钮问题
4. 覆写 STATE

## 坐标

- 工作目录: `~/cc_ps/openclaw2_repair_self` (本文件在主仓 `~/hm_ps/hermes_improve_self/rounds/`)
- openclaw2 链路: openclaw2 → nv_gw(40006, /v1/messages) → NVCF glm5_2_nv
- 上轮: R2068 (hm2_oc2) NOP 巡检轮 17
- 本轮: R2070 (hm2_oc2) NOP 巡检轮 18
- 下轮: R2071 (hm2_oc2)
- HM2 only, 冗余视角.
