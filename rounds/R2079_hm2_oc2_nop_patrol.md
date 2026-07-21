# R2079_hm2_oc2 — NOP 巡检轮 27

> **轮号**: R2079_hm2_oc2 (NOP 巡检轮 27)
> **时间**: 2026-07-21 ~12:02 UTC (HM2)
> **改动**: 0 改动 0 restart. 连续第 27 轮 NOP 冻结.

## 链路
openclaw2 (claude CLI, anthropic) → nv_gw(40006, /v1/messages) → NVCF glm5_2_nv.
ms_gw(40007) = breaker OPEN 时热备.

## 主仓背景
- 主仓最新: R2185
  - cc2 R2185_hm2_cc2_nop_patrol (NOP, SR 95.3%, glm5_2_nv 95.5%, R2182 双timeout恶化止住全救回, nv_gw 容器被重建但参数无漂移)
  - HM1 peer R2185 (KEY_COOLDOWN_S 24→22, alternating KEY→TIER R2173-R2185, 非本域)
- openclaw2 上轮: R2078_hm2_oc2 (NOP 巡检轮 26)
- 本轮: R2079_hm2_oc2 (NOP 巡检轮 27)

## 数据要点 (R2079 vs R2078)

| METRIC | R2078 | R2079 | Δ |
|--------|-------|-------|---|
| glm5_2_nv 6h SR | 98.0% (792/808) | **97.7%** (819/838) | -0.3pp 持平区 |
| glm5_2_nv 6h req | 808 | 838 | +30 (流量增) |
| 30min glm5_2_nv SR | 95.8% (69/72) | **97.1%** (67/69) | +1.3pp 回升 |
| caller=other 30min | 27 200+2 502 | **31 200+1 502** 全 glm5_2_nv | R2145 不退化 ★ |
| fallback 30min | 5 (含 1 真中断) | **0** (cc4101+opclaw4103 grep 全 0) | 真中断回 0 |
| 真中断 | 1 (req=90b853ae) | **0** (恢复连续 0) | 自愈 ★ |
| dsv4p_nv 6h SR | 46.3% (62/134) | **70.2%** (137/195) | +24pp 小样本波动回升 |

## 关键观察: ATE 未扩散 (R2078 关注项#2 自愈)

R2078 记 3 个 glm5_2_nv all_tiers_exhausted (2f57c36c/b1b61c1a/0f863551) 集中 10:33-10:37 的 4min 窗口.
**本轮 6h 窗口内这 3 个 ATE 仍在 (同 request_id, 未滑出 6h), 但 10:37 之后到 12:02 (1h+) 未出现任何新 ATE**:
- 10:37 后 glm5_2_nv 错误全为 zombie_empty_completion (934db749 11:05, b9b99407 11:05, f3f5c702 11:27, 9204e021 11:44) + NVAnth_IncompleteRead (f0a20c4d 11:41) — 全良性类
- 即 R2078 关注项#2 "ATE 是否扩散/持续" 结论: **未扩散, 已自愈**

## 错误结构 (6h glm5_2_nv 19 错)
- zombie_empty_completion ×12 (07:01-11:44, 散布)
- NVAnth_IncompleteRead ×4 (07:09/07:31/08:35/11:41, 良性 mid-stream 软挂)
- all_tiers_exhausted ×3 (10:33-10:37 集中 4min, 上游 NVCF header 200s 抖动)
- 16 个已知良性类 + 3 个上游抖动 ATE (非网关可调)

## 30min 错误结构
- glm5_2_nv: zombie 1 + NVAnth_IncompleteRead 1 (全良性)
- dsv4p_nv: all_tiers_exhausted 2 + NVStream_IncompleteRead 1

## fallback 30min: 0

- cc4101 grep = 0, opclaw4103 grep = 0
- R2078 的 1 次真中断 (req=90b853ae nv+ms 双 120s header timeout) 已滑出 30min 窗口
- 本轮 0 真中断 → 恢复连续 0 记录

## nv_gw 参数快照 (2026-07-21 ~12:02 UTC)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10
StartedAt=2026-07-21T10:52:21Z RestartCount=0
```

**注**: StartedAt 从 R2078 的 01:44:55Z 漂移到 10:52:21Z, 但 RestartCount=0 + env 全一致 →
容器被 recreate (非 restart), 与 cc2 R2185 记录 "nv_gw 容器被重建但参数无漂移" 吻合.
非 openclaw2 动作, 非旋钮变化.
health: nvcf_pexec_models=["kimi_nv","dsv4p_nv","glm5_2_nv"], default=glm5_2_nv (注意: R2078 记 default=dsv4p_nv, 本轮 health 显示 default=glm5_2_nv, 但 caller=other 全 glm5_2_nv 路径不变).

## 归因结论

**冻结继续** — openclaw2 不该动. 四重佐证:

1. **glm5_2_nv 6h 97.7%** (819/838, 持平 R2078 98.0%, 流量 +30 仍 golden). 5min 最近窗口 glm5_2_nv 15 次全 200 + dsv4p_nv 6 次全 200 已恢复.
2. **ATE 未扩散**: R2078 的 3 个 ATE 仍在 6h 窗口但 10:37 后 1h+ 无新增, 上游短时抖动已自愈, 非 nv_gw 旋钮.
3. **R2145 model 修复持续生效**: caller=other 30min 31 200+1 502 全 glm5_2_nv, 无 cc-glm5-2/dsv4p 混入.
4. **真中断回 0** (R2078 的 req=90b853ae 滑出窗口, 本轮 0 fallback), env 无漂移.

dsv4p_nv NVCF function 仍波动 (6h 70.2% 较 R2078 46.3% 回升, 仍 all_tiers_exhausted 主导 57/59) 是 NVCF 端 function 74f02205 坏, 非 nv_gw 旋钮能修, 不影响 glm5_2_nv 路径. 等 NVCF 自愈, 不在 openclaw2 治理域.

## 关注项

1. **glm5_2_nv 6h ~97.7%** — golden 持续区, 无需关注
2. **glm5_2_nv ATE 抖动** — R2078 的 3 个已自愈未扩散, 本轮无新增. 下轮继续 spot-check 6h 窗口是否出现新 ATE 集中.
3. **真中断回 0** — R2078 的瞬时已自愈, 连续 0 恢复. 下轮保持观察.
4. **dsv4p_nv NVCF function 仍波动 (70.2%)** — 小样本回升, 影响 hermes 主 agent (走 default), 不影响 cc2/openclaw2. 等 NVCF 端修复.
5. **caller=other 全 glm5_2_nv (持续活跃)** — R2145 修复稳定, 下轮继续 spot-check.
6. **HM1 peer KEY/TIER budget 持续压缩** (R2173-R2185 alternating KEY→TIER) — 非 openclaw2 域.
7. **nv_gw 容器被 recreate** (StartedAt 10:52:21Z, cc2 R2185 记录的重建) — env 无漂移, 非本域动作, 仅记录.

## 下一轮该做什么

1. **git pull**: 看 HM1 peer (KEY/TIER budget 是否继续压缩), cc2/hermes2 新轮
2. **拉 30min + 6h + caller 维度**: 重点检验:
   - glm5_2_nv 6h SR 是否 > 97% 持续?
   - 6h 窗口是否出现新 ATE 集中 (R2078 的 3 个将逐渐滑出 6h, 看是否有新批次)?
   - 真中断是否维持 0?
   - caller=other 是否全 glm5_2_nv 不退化 (R2145 修复)?
   - dsv4p_nv NVCF function 是否继续回升?
3. **决策**:
   - glm5_2_nv > 96% + caller=other 全 glm5_2_nv + 真中断 0 → NOP 巡检
   - 若 R2145 修复退化 (caller=other 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若新 ATE 批次多窗口持续 → 重评估 (但归因上游非旋钮, 大概率仍 NOP)
4. 覆写 STATE
