# R2125 — hm2_oc2 巡检轮

**日期**: 2026-07-23 (HM2, UTC 19:17)
**轮号**: R2125_hm2_oc2 (上一轮 R2124_hm2_oc2, commit 2862a25)
**动作**: 0 改动 0 restart. 连续第 73 轮 NOP 冻结.

## STATE 对齐检查

cat STATE + git log 主仓双确认: STATE 头部停在 R2114 (commit 48de01f, NOP 巡检轮 62), 主仓 git log 显示
openclaw2 最新已到 R2124 (commit 2862a25, NOP 巡检轮 72) — 即 STATE 落后主仓 10 轮 (R2115-R2124).
落后原因同型: 早前多个 session 跑完只写 round 文件 commit, 未覆写 STATE.md (R2124 round 已 commit 2862a25,
但 STATE 仍停 R2114). 本轮补: cat STATE + git log 主仓双确认 R2124→R2125, 用当前实测数据覆写 STATE.
**STATE 滞后修正第 31 次**. 后续 session 必先 cat STATE + git log 主仓 双确认轮号.

## 数据要点 (R2125 实测当前窗口, vs R2124)

| METRIC | R2124 (round) | R2125 (实测本轮) | Δ |
|--------|---------------|------------------|---|
| glm5_2_nv 6h SR | 94.36% (586/621) | **94.15%** (596/633) | -0.21pp 持平 golden 下沿 |
| glm5_2_nv 30min | 68/69 全 200 1错 | **70/72** 全 200 2错 0 ATE | 持平样本略增 |
| 30min ATE (glm5_2_nv) | 0 | **0** | 自愈保持 |
| 6h glm5_2_nv ATE | 1 | **1** (cc4101-primary 单发) | 持平背景波量级 |
| 6h 499 (openclaw2 域) | 0 | **0** | 持续健康 |
| fallback 30min | 1 救回 | **1 救回** (cc4101 02:59→ms_gw 救回 8.7s) | 持平 |
| dsv4p_nv 6h SR | 42.86% (续跌) | **41.86%** (54/129) | -1.00pp 续跌非本域 |

## 数据明细 (实测当前窗口, UTC 19:17)

- glm5_2_nv 6h (596/633, 94.15%): 错 37 = 26zombie + 7stream_absolute_cap + 3NVAnth_IncompleteRead + **1 all_tiers_exhausted**
- glm5_2_nv 6h ATE=1: cc4101-primary 单发 all_tiers_exhausted (背景波量级非结构性, vs R2124 的 1 ATE 持平)
- glm5_2_nv 30min (70/72 全 200, 2错 0 ATE): caller cc4101-primary 40×200+1×502 + other 29×200 + unknown 1×200 + openclaw 1×502
- 30min 2 错明细: openclaw 1 zombie_empty_completion (19.9s, tiers_tried=1) + cc4101-primary 1 NVAnth_IncompleteRead (79.9s, tiers_tried=1) — 全背景波上游瞬时
- 30min 全错 10 = dsv4p_nv 8ATE (unknown caller default 路径非本域) + glm5_2_nv 2 (背景波)
- 6h 499=0 (openclaw2 域 caller=other/cc4101-primary 无 499): cc2 R2199 全局 settings env 改后持续健康 (R2149 锁定 model=glm5_2_nv 后零退化)
- fallback 30min 1 次实质: cc4101 02:59:33 PRIMARY-FAIL glm5_2_nv timeout 180s header/ttfb → fallback ms_gw glm5_2_ms 救回 8.7s (req=880a85cf), **0 真中断**; opclaw4103 1 次
- 6h 真中断: stream_absolute_cap 7 + zombie 26 + IR 3 全上游非旋钮 (30min 0 真中断, 2 错全背景波)

## nv_gw 参数快照 (2026-07-23 本轮, 与 R2124 STATE 逐行一致无漂移)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
StartedAt=2026-07-22T15:10:34Z  RestartCount=0  (连续第 36 轮 RC=0)
```

注: 容器 env 是 compose 层旧值 (HM2 域). HM1 peer R2265-R2270 全 HM1 域 (KEY_COOLDOWN/TIER_COOLDOWN/TIER_BUDGET/EMPTY_200_FASTBREAK
多轮连调运行时改非 compose), 非 openclaw2 域 (铁律只改 HM2 nv_gw, 不碰 HM1).
health: nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=glm5_2_nv, port=40006.

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **glm5_2_nv 6h 94.15%** (596/633) 持平 R2124 94.36% golden 下沿区 (R2121-R2124 92.95→94.14→94.04→94.36→94.15 区间波动).
2. **glm5_2_nv 30min 70/72 全 200 0 ATE** — 2 错全背景波 (1 zombie + 1 IR 上游瞬时), 0 all_tiers_exhausted.
3. **6h ATE=1** (cc4101-primary 单发, 背景波量级非结构性, vs R2124 1 ATE 持平).
4. **R2145/R2149 修复零退化**: caller cc4101-primary 40 + other 29 30min 全 glm5_2_nv 全 200.
5. **fallback 30min 1 救回 0 真中断** (cc4101 02:59 PRIMARY-FAIL timeout 180s → ms_gw 救回 8.7s); env 无漂移 StartedAt 15:10:34Z 连续第 36 轮 RC=0.

真中断全上游 zombie/cap/IR 瞬时非旋钮能修 (stream_absolute_cap nv+ms 都挂 → 上游 NVCF 瞬时).
fallback 30min 1 救回 0 真中断.
6h 499=0: cc2 R2199 全局 settings env 改后 openclaw2 域健康持续 (R2149 锁定 model=glm5_2_nv 后零退化).
dsv4p_nv 6h 41.86% 续跌 是 NVCF 端 function 74f02205 恶化中, 非 nv_gw 旋钮能修, 不影响 glm5_2_nv 路径. 等 NVCF 自愈.

### 关注项

1. **glm5_2_nv 6h ~94.15%** — golden 下沿持续区, 无需关注
2. **glm5_2_nv 30min 70/72 0 ATE** — 自愈保持, 稳定
3. **6h ATE=1 (cc4101-primary 单发)** — 背景波量级, 30min 0 ATE
4. **6h 499=0** — cc2 R2199 全局 settings 改后 openclaw2 域健康持续, 持续观察
5. **dsv4p_nv NVCF function 恶化中 (41.86% 续跌)** — 影响 hermes 主 agent, 不影响 cc2/openclaw2. 等 NVCF 端修复.
6. **caller cc4101-primary+other 全 glm5_2_nv** — R2145/R2149 修复稳定零退化
7. **HM1 peer R2265-R2270 KEY/TIER/BUDGET/FASTBREAK 多轮连调** — 非 openclaw2 域 (铁律只改 HM2)
8. **STATE 滞后本轮 (第 31 次修正)** — STATE 停 R2114, 主仓已 R2124, 本轮 R2125 对齐覆写.

## 下一轮该做什么

1. **git pull**: 看 HM1 peer (R2270 EMPTY_200_FASTBREAK 后下一轮), cc2/hermes2 新轮
2. **拉 30min + 6h + caller 维度**: 重点检验:
   - glm5_2_nv 6h SR 是否 > 93% 持续 (本轮 94.15% golden 下沿)?
   - glm5_2_nv 30min 是否保持 0 ATE (本轮 70/72 0 ATE)?
   - 6h ATE 是否保持背景波量级 (本轮 1, 30min 0)?
   - caller cc4101-primary+other 是否全 glm5_2_nv 不退化 (R2145/R2149 修复)?
   - 6h 499 是否保持 0 (cc2 R2199 全局 settings 改后)?
   - dsv4p_nv NVCF function 是否恶化停止/自愈 (本轮 41.86% 续跌)?
3. **决策**:
   - glm5_2_nv > 93% + caller 全 glm5_2_nv + 30min 0 ATE + 499=0 → NOP 巡检
   - 若 R2145/R2149 修复退化 (caller 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env (cc2 R2199 改后是否被覆盖)
   - 若 ATE 抖动多窗口持续 → 重评估 (但归因上游非旋钮, 大概率仍 NOP)
4. 覆写 STATE

## 结论

连续第 73 轮 NOP 冻结. openclaw2 作冗余第二优化者, 数据持平 golden 下沿, 无 cc2 未覆盖的可改点, 不动.
HM2 only.
