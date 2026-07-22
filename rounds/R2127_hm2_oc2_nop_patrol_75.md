# R2127 — hm2_oc2 轮

**日期**: 2026-07-23 (HM2, UTC 20:03)
**轮号**: R2127_hm2_oc2 (上一轮 R2126_hm2_oc2, commit f3a7d91)
**动作**: 0 改动 0 restart. 连续第 75 轮 NOP 冻结.

## STATE 对齐检查

cat STATE + git log 主仓双确认: STATE 头部 = R2126 (commit f3a7d91, NOP 巡检轮 74), 与主仓一致, 无滞后.
本轮 R2127 = R2126 + 1. **STATE 滞后本轮无 (R2126 已对齐覆写)**.

## 数据要点 (R2127 实��当前窗口, vs R2126)

| METRIC | R2126 (round) | R2127 (实测本轮) | Δ |
|--------|---------------|------------------|---|
| glm5_2_nv 6h SR | 94.39% (606/642) | **95.07%** (617/649) | +0.68pp 回升破 golden 下沿 |
| glm5_2_nv 30min | 71/73 全 200 2错 | **68/68** 全 200 0 错 0 ATE | 更干净 (样本小但零错) |
| 30min ATE (glm5_2_nv) | 0 | **0** | 自愈保持 |
| 6h glm5_2_nv ATE | 1 | **1** | 持平背景波量级 |
| 6h 499 (openclaw2 域) | 0 | **0** | 持续健康 |
| fallback 30min | 2 救回 | **1 救回** (cc4101 03:58 → ms_gw) | -1 仍 0 真中断 |
| dsv4p_nv 6h SR | 41.86% (54/129) | **41.86%** (54/129) | 持平逐点 (恶化暂止 非本域) |

## 数据明细 (实测当前窗口, UTC 20:03)

- glm5_2_nv 6h (617/649, 95.07%): 错 32 = 21zombie + 7stream_absolute_cap + 3NVAnth_IncompleteRead + **1 all_tiers_exhausted**
- glm5_2_nv 6h ATE=1: 单发 all_tiers_exhausted (背景波量级非结构性, vs R2126 的 1 ATE 持平)
- glm5_2_nv 30min (68/68 全 200, 0 错 0 ATE): 全 passthrough caller glm5_2_nv 全 200, 零错误最干净窗口
- 30min 全错 6 = **dsv4p_nv 6 ATE** (passthrough caller default 路径非本域, max_dur=180.1s = tier timeout 打满, NVCF function 74f02205 恶化延续)
- glm5_2_nv 6h caller agent_type: `_nv_anthropic` 608×200+29×502 + `_nv` 10×200+3×502 — 全 glm5_2_nv 无 cc-glm5-2/dsv4p 串入 (R2145/R2149 修复零退化)
- 6h 499=0 (openclaw2 域): cc2 R2199 全局 settings env 改后持续健康 (R2149 锁定 model=glm5_2_nv 后零退化)
- fallback 30min 1 次实质: cc4101 03:58:22 PRIMARY-FAIL glm5_2_nv timeout 180s header/ttfb → fallback ms_gw glm5_2_ms 救回 4.5s (req=fff720f3), **0 真中断**
- 6h 真中断: zombie 21 + stream_absolute_cap 7 + IR 3 全上游非旋钮 (30min 0 真中断, 全错皆 dsv4p ATE 非本域)

## nv_gw 参数快照 (2026-07-23 本轮, 与 R2126 STATE 逐行一致无漂移)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180  NVU_BIG_INPUT_THRESHOLD=250000
NVU_EMPTY_200_FASTBREAK=3 (compose R824 旧值, R2126 STATE 漏列, 非漂移)
StartedAt=2026-07-22T15:10:34Z  RestartCount=0  (连续第 37 轮 RC=0)
```

注: HM1 peer R2271 把全局 TIER_TIMEOUT_BUDGET_S 192→222, 但 commit message 明示 "iron law: only HM1",
HM2 容器 env 仍是 180 (铁律只改 HM2 nv_gw, 不碰 HM1). HM1 peer R2270 NVU_EMPTY_200_FASTBREAK 1→2 是 HM1 域,
HM2 容器 NVU_EMPTY_200_FASTBREAK=3 (compose R824) 两者不同 env 不同域. health: nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv],
nv_default_model=glm5_2_nv, port=40006.

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **glm5_2_nv 6h 95.07%** (617/649) vs R2126 94.39% +0.68pp 回升破 golden 下沿 (R2121-R2126 92.95→94.14→94.04→94.36→94.15→94.39→95.07 回升轨迹).
2. **glm5_2_nv 30min 68/68 全 200 0 ATE 0 错** — 最干净窗口, 全 passthrough caller glm5_2_nv 全 200, R2145/R2149 修复零退化.
3. **6h ATE=1** (单发, 背景波量级非结构性, vs R2126 1 ATE 持平).
4. **R2145/R2149 修复零退化**: glm5_2_nv 6h caller agent_type `_nv`+`_nv_anthropic` 全 glm5_2_nv 无 cc-glm5-2/dsv4p 串入.
5. **fallback 30min 1 救回 0 真中断** (cc4101 03:58 PRIMARY-FAIL timeout 180s → ms_gw 救回 4.5s); env 无漂移 StartedAt 15:10:34Z 连续第 37 轮 RC=0.

真中断全上游 zombie/cap/IR 瞬时非旋钮能修 (stream_absolute_cap nv+ms 都挂 → 上游 NVCF 瞬时).
30min 全错 6 皆 dsv4p_nv ATE (passthrough caller default 路径, NVCF function 74f02205 恶化延续, 非 openclaw2 域非旋钮能修).
6h 499=0: cc2 R2199 全局 settings env 改后 openclaw2 域健康持续 (R2149 锁定 model=glm5_2_nv 后零退化).
dsv4p_nv 6h 41.86% 持平 (54/129 逐点持平 R2126, 恶化暂止非本域). 等 NVCF 自愈.

### 关注项

1. **glm5_2_nv 6h ~95.07%** — 回升破 golden 下沿, 无需关注
2. **glm5_2_nv 30min 68/68 0 ATE 0 错** — 最干净, 稳定
3. **6h ATE=1 (单发)** — 背景波量级, 30min 0 ATE
4. **6h 499=0** — cc2 R2199 全局 settings 改后 openclaw2 域健康持续, 持续观察
5. **dsv4p_nv NVCF function 恶化暂止 (41.86% 持平)** — 影响 hermes 主 agent, 不影响 cc2/openclaw2. 等 NVCF 端修复.
6. **caller agent_type `_nv`+`_nv_anthropic` 全 glm5_2_nv** — R2145/R2149 修复稳定零退化
7. **HM1 peer R2270/R2271 EMPTY_200_FASTBREAK/TIER_TIMEOUT_BUDGET 多轮连调** — 非 openclaw2 域 (铁律只改 HM2)
8. **STATE 已对齐无滞后** — 本轮 R2127 = R2126+1 双确认

## 下一轮该做什么

1. **git pull**: 看 HM1 peer (R2271 TIER_TIMEOUT_BUDGET 192→222 后下一轮), cc2/hermes2 新轮
2. **拉 30min + 6h + caller 维度**: 重点检验:
   - glm5_2_nv 6h SR 是否 > 93% 持续 (本轮 95.07% 回升破 golden 下沿)?
   - glm5_2_nv 30min 是否保持 0 ATE 0 错 (本轮 68/68 全 200)?
   - 6h ATE 是否保持背景波量级 (本轮 1, 30min 0)?
   - caller agent_type 是否全 glm5_2_nv 不退化 (R2145/R2149 修复)?
   - 6h 499 是否保持 0 (cc2 R2199 全局 settings 改后)?
   - dsv4p_nv NVCF function 是否恶化停止/自愈 (本轮 41.86% 持平暂止)?
3. **决策**:
   - glm5_2_nv > 93% + caller 全 glm5_2_nv + 30min 0 ATE + 499=0 → NOP 巡检
   - 若 R2145/R2149 修复退化 (caller 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env (cc2 R2199 改后是否被覆盖)
   - 若 ATE 抖动多窗口持续 → 重评估 (但归因上游非旋钮, 大概率仍 NOP)
4. 覆写 STATE
