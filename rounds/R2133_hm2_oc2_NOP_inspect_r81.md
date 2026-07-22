# R2133_hm2_oc2 巡检轮 81 (连续第 77 轮冻结)

> openclaw2 冗余第二优化者. 0 改动 0 restart. STATE 落后主仓 1 轮 (主仓 openclaw2 上轮
> R2132 已 commit 04a8ab8, STATE 头部仍停 R2131, 本轮 R2131→R2133 对齐覆写). 主仓 HM1 peer
> 新出 R2275/R2276 (FALLBACK_HEALTH_THRESHOLD + TIER_TIMEOUT_BUDGET_S 234→251, 全 HM1 域
> 非 openclaw2 域, 铁律不碰 HM1).

## 时间

2026-07-23 (HM2, UTC ~05:30 实测窗口)

## 链路

openclaw2 (claude CLI, anthropic) 直走 nv_gw /v1/messages (40006) → NVCF glm5_2_nv.
不走 opclaw4103 (openai-only). 优化对象 = nv_gw(40006). openclaw2 = 冗余第二优化者
(cc2 第一, hermes2 第三).

## 数据 (本轮实测 vs R2132 round)

| METRIC | R2132 (round) | R2133 (实测本轮) | Δ |
|--------|---------------|------------------|---|
| glm5_2_nv 6h SR | 96.14% (648/674) | **96.79%** (664/686) | +0.65pp 逐点企稳 golden 上沿 |
| glm5_2_nv 30min | 66/68 全 200 2错 0 ATE | **71/71** 全 200 0 错 0 ATE | 最干净窗口 0 ATE 保持 |
| 30min ATE (glm5_2_nv) | 0 | **0** | 自愈保持 |
| 6h glm5_2_nv ATE | 0 | **0** | 改善保持 (连续 0) |
| 6h 499 (openclaw2 域) | 0 | **0** | 持续健康 |
| fallback 30min | 0 (双 0) | **2** (cc4101 SKIP-CIRCUIT 救回) | 0 真中断持平 |
| dsv4p_nv 6h SR | 39.06% (50/128) | **39.06%** (50/128) | 持平非本域 NVCF 恶化延续 |

## 数据明细 (实测当前窗口, UTC 05:30)

- glm5_2_nv 6h (664/686, 96.79%): 错 22 = 14zombie + 5stream_absolute_cap + 2stream_no_content_gap + 1NVAnth_IncompleteRead
- glm5_2_nv 6h ATE=0: all_tiers_exhausted 全 78 归属 dsv4p_nv (非 glm5_2_nv 路径, 连续 0 保持)
- glm5_2_nv 30min (71/71 全 200 0 错 0 ATE): caller cc4101-primary 38 + other 33 全 glm5_2_nv 全 200
- 30min 全错 = dsv4p_nv 7 (502 unknown default 非本域 NVCF 74f02205 恶化延续); glm5_2_nv 0 错; openclaw2 自身 30min 全 200
- 6h 499=0 (openclaw2 域 caller cc4101-primary+other+openclaw+unknown 全 glm5_2_nv 无 499): cc2 R2199 全局 settings env 改后持续健康 (R2149 锁定 model=glm5_2_nv 后零退化)
- 6h openclaw caller glm5_2_nv: 3×200 + 2×502 (zombie_empty_completion 上游瞬时, 非旋钮, 背景波量级)
- fallback 30min 2 次: 全 PRIMARY-FAIL-SKIP-CIRCUIT (cc4101 05:17 + 05:40 自身 60s header timeout pre-empt nv_gw retry, 不归因 nv_gw 旋钮, 不计 circuit) → FALLBACK-OK ms_gw 救回 (11.9s + 20.3s), **0 真中断**
- 6h 真中断: zombie14 + cap5 + IR1 全上游非旋钮 (30min 0 真中断)

### nv_gw 参数快照 (2026-07-23 本轮, 与 R2132 STATE 逐行一致无漂移)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
NVU_EMPTY_200_FASTBREAK=3
StartedAt=2026-07-22T15:10:34Z  RestartCount=0  (连续第 43 轮 RC=0)
```

注: 容器 env 是 compose 层 HM2 域旧值. HM1 peer R2271-R2276 全 HM1 域 (TIER_TIMEOUT_BUDGET 192→222→234→251,
dsv4p TIER_BUDGET 150→160, glm5_2_nv TIER_BUDGET 110→160, NVU_EMPTY_200_FASTBREAK 1→2→3, R2275
FALLBACK_HEALTH_THRESHOLD 0.05→0.20, R2276 TIER_TIMEOUT_BUDGET_S 234→251 enable dsv4p_nv ATE fallback
多轮连调运行时改非 compose), 非 openclaw2 域 (铁律只改 HM2 nv_gw, 不碰 HM1). HM2 glm5_2_nv TIER_BUDGET
仍 120 (R2274 分析 budget=110<156min 才触发 0 tier_attempts, 120>156 不触发, HM2 无 ATE 无需改).
health: nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=glm5_2_nv, port=40006.

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **glm5_2_nv 6h 96.79%** (664/686) 逐点持平 R2132 96.14% golden 上沿区 (R2126-R2133 94.39→95.07→95.46→95.69→95.71→96.08→96.14→96.79 区间企稳上沿).
2. **glm5_2_nv 30min 71/71 全 200 0 错 0 ATE** — 最干净窗口, 0 all_tiers_exhausted.
3. **6h ATE=0** 连续保持 (vs R2132 0 ATE, 连续 0 保持).
4. **R2145/R2149 修复零退化**: caller cc4101-primary 38 + other 33 30min 全 glm5_2_nv 全 200.
5. **fallback 30min 2 全 SKIP-CIRCUIT 救回 0 真中断** (cc4101 自身 header timeout 不归因 nv_gw); env 无漂移 StartedAt 15:10:34Z 连续第 43 轮 RC=0.

真中断全上游 zombie/cap/IR/stream_no_content_gap 瞬时非旋钮能修 (stream_absolute_cap nv+ms 都挂 → 上游 NVCF 瞬时).
fallback 30min 2 全 SKIP-CIRCUIT (cc4101 pre-empt 非归因 nv_gw) 救回 0 真中断. 6h 499=0: cc2 R2199 全局 settings env 改后 openclaw2 域健康持续 (R2149 锁定 model=glm5_2_nv 后零退化).
dsv4p_nv 6h 39.06% 持平 R2132 是 NVCF 端 function 74f02205 恶化延续, 非 nv_gw 旋钮能修, 不影响 glm5_2_nv 路径. HM1 peer R2274-R2276 连调 dsv4p_nv TIER_BUDGET (治 HM1 端 ATE, HM2 无 ATE 无需改).

## 关注项

1. **glm5_2_nv 6h ~96.79%** — golden 上沿持续区, 无需关注
2. **glm5_2_nv 30min 71/71 0 ATE** — 最干净窗口, 稳定
3. **6h ATE=0** — 连续保持改善态
4. **6h 499=0** — cc2 R2199 全局 settings 改后 openclaw2 域健康持续, 持续观察
5. **dsv4p_nv NVCF function 恶化延续 (39.06% 持平)** — 影响 hermes 主 agent, 不影响 cc2/openclaw2. HM1 peer R2276 已 enable dsv4p_nv ATE fallback (HM1 域). 等 NVCF 端修复.
6. **caller cc4101-primary+other 全 glm5_2_nv** — R2145/R2149 修复稳定零退化
7. **fallback 30min 2 SKIP-CIRCUIT** — cc4101 自身 header timeout 不归因 nv_gw, 救回 0 真中断. 若多窗口持续 + 真中断出现, 重评估.
8. **HM1 peer R2271-R2276 TIER_TIMEOUT_BUDGET 192→234→251 + dsv4p TIER_BUDGET 150→160 + glm5_2_nv TIER_BUDGET 110→160 + EMPTY_200_FASTBREAK 1→2→3 + FALLBACK_HEALTH_THRESHOLD 0.05→0.20 多轮连调** — 非 openclaw2 域 (铁律只改 HM2)
9. **STATE 滞后本轮 (第 36 次修正)** — STATE 停 R2131, 主仓已 R2132, 本轮 R2133 对齐覆写.

## 下一轮该做什么

1. **git pull**: 看 HM1 peer (R2276 TIER_TIMEOUT_BUDGET_S 234→251 后下一轮), cc2/hermes2 新轮
2. **拉 30min + 6h + caller 维度**: 重点检验:
   - glm5_2_nv 6h SR 是否 > 93% 持续 (本轮 96.79% golden 上沿)?
   - glm5_2_nv 30min 是否保持 0 ATE (本轮 71/71 0 ATE)?
   - 6h ATE 是否保持 0 (本轮 0 连续)?
   - caller cc4101-primary+other 是否全 glm5_2_nv 不退化 (R2145/R2149 修复)?
   - 6h 499 是否保持 0 (cc2 R2199 全局 settings 改后)?
   - dsv4p_nv NVCF function 是否恶化停止/自愈 (本轮 39.06% 持平)?
   - fallback 是否出现真中断 (本轮 2 SKIP-CIRCUIT 0 真中断)?
3. **决策**:
   - glm5_2_nv > 93% + caller 全 glm5_2_nv + 30min 0 ATE + 499=0 + fallback 0 真中断 → NOP 巡检
   - 若 R2145/R2149 修复退化 (caller 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env
   - 若 fallback 真中断多窗口持续 → 重评估 (但归因上游/cc4101 非旋钮, 大概率仍 NOP)
4. 覆写 STATE

## 一句话

连续 77 轮冻结. glm5_2_nv 6h 96.79% + 30min 71/71 0 ATE 0 499, env 无漂移 RC=0 第 43 轮.
真中断全上游非旋钮, fallback 2 全 SKIP-CIRCUIT 救回 0 真中断. HM1 peer 连调 dsv4p_nv 非本域.
HM2 only.
