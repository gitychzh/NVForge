# R2128 — hm2_oc2 轮

**日期**: 2026-07-23 (HM2, UTC 04:16)
**轮号**: R2128_hm2_oc2 (上一轮 R2127_hm2_oc2, commit 11a4b1d)
**动作**: 0 改动 0 restart. 连续第 76 轮 NOP 冻结.

## STATE 对齐检查

cat STATE + git log 主仓双确认: STATE 头部 = R2125 (commit be54525, NOP 巡检轮 73), 但主仓 git log
显示 openclaw2 最新已到 R2127 (commit 11a4b1d, NOP 巡检轮 75) — 即 STATE 落后主仓 2 轮 (R2126-R2127).
落后原因同型: 早前 session 跑完只写 round 文件 commit, 未覆写 STATE.md (R2126/R2127 round 已 commit,
但 STATE 仍停 R2125). 本轮补: cat STATE + git log 主仓双确认 R2127→R2128, 用当前实测数据覆写 STATE.
**STATE 滞后修正第 32 次**. **后续 session 必先 cat STATE + git log 主仓 双确认轮号**, 避免再次滞后.

## 数据要点 (R2128 实测当前窗口, vs R2127)

| METRIC | R2127 (round) | R2128 (实测本轮) | Δ |
|--------|---------------|------------------|---|
| glm5_2_nv 6h SR | 95.07% (617/649) | **95.46%** (631/661) | +0.39pp 企稳 golden 上沿 |
| glm5_2_nv 30min | 68/68 全 200 0错 | **69/69** 全 200 0 错 0 ATE | 持平最干净窗口 |
| 30min ATE (glm5_2_nv) | 0 | **0** | 自愈保持 |
| 6h glm5_2_nv ATE | 1 | **1** | 持平背景波量级 |
| 6h 499 (openclaw2 域) | 0 | **0** | 持续健康 |
| fallback 30min | 1 救回 | **1 救回** (cc4101 03:58 → ms_gw) | 持平 0 真中断 |
| dsv4p_nv 6h SR | 41.86% (54/129) | **41.86%** (54/129) | 持平逐点 (恶化暂止 非本域) |

## 数据明细 (实测当前窗口, UTC 04:16)

- glm5_2_nv 6h (631/661, 95.46%): 错 30 = 20zombie + 6stream_absolute_cap + 3NVAnth_IncompleteRead + **1 all_tiers_exhausted**
- glm5_2_nv 6h ATE=1: 单发 all_tiers_exhausted (背景波量级非结构性, vs R2127 的 1 ATE 持平)
- glm5_2_nv 30min (69/69 全 200, 0 错 0 ATE): caller cc4101-primary 38×200 + other 31×200 全 glm5_2_nv 全 200, 零错误最干净窗口
- 30min 全错 6 = **dsv4p_nv 6 ATE** (caller=unknown default 路径非本域, all_tiers_exhausted/all_tiers_failed_in_mapped_tier, NVCF function 74f02205 恶化延续)
- glm5_2_nv 6h caller: cc4101-primary 357×200+13×502 + other 265×200+14×502 — 全 glm5_2_nv 无 cc-glm5-2/dsv4p 串入 (R2145/R2149 修复零退化)
- 6h 499=0 (openclaw2 域): cc2 R2199 全局 settings env 改后持续健康 (R2149 锁定 model=glm5_2_nv 后零退化)
- fallback 30min 1 次实质: cc4101 03:58:22 PRIMARY-FAIL glm5_2_nv timeout 180s header/ttfb → fallback ms_gw glm5_2_ms 救回 4.5s (req=fff720f3), **0 真中断**
- 6h 真中断: zombie 20 + stream_absolute_cap 6 + IR 3 全上游非旋钮 (30min 0 真中断, 全错皆 dsv4p ATE 非本域)

## nv_gw 参数快照 (2026-07-23 本轮, 与 R2127 STATE 逐行一致无漂移)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180  NVU_BIG_INPUT_THRESHOLD=250000
NVU_EMPTY_200_FASTBREAK=3 (compose R824 旧值, R2127 STATE 已列, 非漂移)
StartedAt=2026-07-22T15:10:34Z  RestartCount=0  (连续第 38 轮 RC=0)
```

注: HM1 peer R2271 把全局 TIER_TIMEOUT_BUDGET_S 192→222, 但 commit message 明示 "iron law: only HM1",
HM2 容器 env 仍是 180 (铁律只改 HM2 nv_gw, 不碰 HM1). HM1 peer R2270 NVU_EMPTY_200_FASTBREAK 1→2 是 HM1 域,
HM2 容器 NVU_EMPTY_200_FASTBREAK=3 (compose R824) 两者不同 env 不同域. health: nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv],
nv_default_model=glm5_2_nv, port=40006, proxy_role=passthrough, nv_num_keys=5.

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **glm5_2_nv 6h 95.46%** (631/661) vs R2127 95.07% +0.39pp 企稳 golden 上沿 (R2121-R2127 92.95→94.14→94.04→94.36→94.15→94.39→95.07→95.46 回升轨迹稳).
2. **glm5_2_nv 30min 69/69 全 200 0 ATE 0 错** — 最干净窗口, caller cc4101-primary+other 全 glm5_2_nv 全 200, R2145/R2149 修复零退化.
3. **6h ATE=1** (单发, 背景波量级非结构性, vs R2127 1 ATE 持平).
4. **R2145/R2149 修复零退化**: glm5_2_nv 6h caller cc4101-primary+other 全 glm5_2_nv 无 cc-glm5-2/dsv4p 串入.
5. **fallback 30min 1 救回 0 真中断** (cc4101 03:58 PRIMARY-FAIL timeout 180s → ms_gw 救回 4.5s); env 无漂移 StartedAt 15:10:34Z 连续第 38 轮 RC=0.

真中断全上游 zombie/cap/IR 瞬时非旋钮能修 (stream_absolute_cap nv+ms 都挂 → 上游 NVCF 瞬时).
fallback 30min 1 救回 0 真中断.
6h 499=0: cc2 R2199 全局 settings env 改后 openclaw2 域健康持续 (R2149 锁定 model=glm5_2_nv 后零退化).
dsv4p_nv 6h 41.86% 持平 是 NVCF 端 function 74f02205 恶化暂止, 非 nv_gw 旋钮能修, 不影响 glm5_2_nv 路径. 等 NVCF 自愈.

### 关注项

1. **glm5_2_nv 6h ~95.46%** — golden 上沿持续区, 无需关注
2. **glm5_2_nv 30min 69/69 0 ATE** — 自愈保持, 稳定
3. **6h ATE=1 (单发)** — 背景波量级, 30min 0 ATE
4. **6h 499=0** — cc2 R2199 全局 settings 改后 openclaw2 域健康持续, 持续观察
5. **dsv4p_nv NVCF function 恶化暂止 (41.86% 持平)** — 影响 hermes 主 agent, 不影响 cc2/openclaw2. 等 NVCF 端修复.
6. **caller cc4101-primary+other 全 glm5_2_nv** — R2145/R2149 修复稳定零退化
7. **HM1 peer R2270/R2271 EMPTY_200_FASTBREAK/TIER_TIMEOUT_BUDGET 多轮连调** — 非 openclaw2 域 (铁律只改 HM2)
8. **STATE 滞后本轮 (第 32 次修正)** — STATE 停 R2125, 主仓已 R2127, 本轮 R2128 对齐覆写.

## 下一轮该做什么

1. **git pull**: 看 HM1 peer (R2271 TIER_TIMEOUT_BUDGET_S 222 后下一轮), cc2/hermes2 新轮
2. **拉 30min + 6h + caller 维度**: 重点检验:
   - glm5_2_nv 6h SR 是否 > 93% 持续 (本轮 95.46% golden 上沿)?
   - glm5_2_nv 30min 是否保持 0 ATE (本轮 69/69 0 ATE)?
   - 6h ATE 是否保持背景波量级 (本轮 1, 30min 0)?
   - caller cc4101-primary+other 是否全 glm5_2_nv 不退化 (R2145/R2149 修复)?
   - 6h 499 是否保持 0 (cc2 R2199 全局 settings 改后)?
   - dsv4p_nv NVCF function 是否恶化停止/自愈 (本轮 41.86% 持平)?
3. **决策**:
   - glm5_2_nv > 93% + caller 全 glm5_2_nv + 30min 0 ATE + 499=0 → NOP 巡检
   - 若 R2145/R2149 修复退化 (caller 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env (cc2 R2199 改后是否被覆盖)
   - 若 ATE 抖动多窗口持续 → 重评估 (但归因上游非旋钮, 大概率仍 NOP)
4. 覆写 STATE

## 最近 5 轮摘要

1. **R2128_hm2_oc2**: NOP 巡检轮 76 — STATE 滞后修正第 32 次同型 (STATE 停 R2125, 主仓 openclaw2 上轮 R2127, 本轮 R2128 对齐). glm5_2_nv 6h 95.46% (631/661 +0.39pp vs R2127 95.07% 企稳 golden 上沿), 错 20z+6cap+3IR+1ATE 1 ATE 0 499. 30min glm5_2_nv 69/69 全 200 0 错 0 ATE 最干净窗口 (cc4101-primary 38+other 31 全 glm5_2_nv). 30min 全错 6 = dsv4p_nv 6ATE (unknown default 非本域). 6h 真中断全上游非旋钮 (zombie20+cap6+IR3, 30min 0 真中断). fallback 30min 1 (cc4101 03:58 PRIMARY-FAIL glm5_2_nv timeout 180s → FALLBACK-OK ms_gw 救回 4.5s 0 真中断). dsv4p_nv 6h 41.86% (54/129 逐点持平 R2127, 恶化暂止 非本域). glm5_2_nv 6h caller cc4101-primary+other 全 glm5_2_nv 无 cc-glm5-2/dsv4p 串入 (R2145/R2149 修复零退化). env 无漂移 StartedAt 15:10:34Z RC=0 连续第 38 轮. HM1 peer R2270/R2271 EMPTY_200_FASTBREAK/TIER_TIMEOUT_BUDGET 多轮连调非本域 (铁律只改 HM2). 连续 76 NOP. HM2 only.
2. **R2127_hm2_oc2**: NOP 巡检轮 75 — STATE 已对齐无滞后. glm5_2_nv 6h 95.07% (617/649 +0.68pp vs R2126 94.39% 回升破 golden 下沿), 错 21z+7cap+3IR+1ATE 1 ATE 0 499. 30min glm5_2_nv 68/68 全 200 0 错 0 ATE 最干净窗口 (全 passthrough caller glm5_2_nv 全 200). 30min 全错 6 = dsv4p_nv 6ATE (passthrough caller default 非本域). 6h 真中断全上游非旋钮 (zombie21+cap7+IR3, 30min 0 ���中断). fallback 30min 1 (cc4101 03:58 PRIMARY-FAIL glm5_2_nv timeout 180s → FALLBACK-OK ms_gw 救回 4.5s 0 真中断). dsv4p_nv 6h 41.86% (54/129 逐点持平 R2126, 恶化暂止 非本域). env 无漂移 StartedAt 15:10:34Z RC=0 连续第 37 轮. 连续 75 NOP. HM2 only.
3. **R2126_hm2_oc2**: NOP 巡检轮 74 — STATE 滞后修正第 31 次同型. glm5_2_nv 6h 94.39% (606/642 +0.24pp vs R2125 94.15% 持平 golden 下沿), 错 25z+7cap+3IR+1ATE 1 ATE 0 499. 30min glm5_2_nv 71/73 全 200 2错 0 ATE (cc4101-primary 41+1错+other 29+unknown 1+openclaw 1错 全 glm5_2_nv). 30min 全错 9 = glm5_2_nv 2 (1z+1IR 背景波) + dsv4p 7ATE (unknown default 非本域). 6h 真中断全上游非旋钮 (zombie25+cap7+IR3, 30min 0 真中断). fallback 30min 2 (cc4101 03:22 PRIMARY-FAIL glm5_2_nv timeout 180s → FALLBACK-OK ms_gw 救回 5.2s; 03:24 PRIMARY-FAIL RemoteDisconnected 35.6s → 救回 10.1s 0 真中断). dsv4p_nv 6h 41.86% (54/129 逐点持平 R2125, 恶化暂止 非本域). R2145/R2149 修复零退化. env 无漂移 StartedAt 15:10:34Z RC=0 连续第 37 轮. 连续 74 NOP. HM2 only.
4. **R2125_hm2_oc2**: NOP 巡检轮 73 — STATE 滞后修正第 31 次同型. glm5_2_nv 6h 94.15% (596/633 持平 R2124 94.36% golden 下沿), 错 26z+7cap+3IR+1ATE 1 ATE 0 499. 30min glm5_2_nv 70/72 全 200 2错 0 ATE (cc4101-primary 40+1错+other 29+unknown 1+openclaw 1错 全 glm5_2_nv). 30min 全错 10 = glm5_2_nv 2 (1z+1IR 背景波) + dsv4p 8ATE (unknown default 非本域). 6h 真中断全上游非旋钮 (zombie26+cap7+IR3, 30min 0 真中断). fallback 30min 1 (cc4101 02:59 PRIMARY-FAIL glm5_2_nv timeout 180s → FALLBACK-OK ms_gw 救回 8.7s 0 真中断). dsv4p_nv 6h 41.86% 续跌 (NVCF 74f02205 恶化中 非本域). R2145/R2149 修复零退化. env 无漂移 StartedAt 15:10:34Z RC=0 连续第 36 轮. 连续 73 NOP. HM2 only.
5. **R2124_hm2_oc2**: NOP 巡检轮 72 — STATE 滞后修正第 30 次同型. glm5_2_nv 6h 94.36% (586/621 持平 R2123 94.04% golden 下沿), 错 25z+7cap+2IR+1ATE 1 ATE 0 499. 30min glm5_2_nv 68/69 全 200 1 错 0 ATE (cc4101-primary 43+other 29 全 glm5_2_nv). 30min 全错 9 = glm5_2_nv 1zombie + dsv4p 8ATE (unknown default 非本域). 6h 真中断 7 (4z+2IR+1ATE 全上游非旋钮). fallback 30min 1 (cc4101 02:59 PRIMARY-FAIL glm5_2_nv 180s → FALLBACK-OK ms_gw 救回 8.8s 0 真中断). dsv4p_nv 6h 42.86% 续跌 (NVCF 74f02205 恶化中 非本域). R2145/R2149 修复零退化. env 无漂移 StartedAt 15:10:34Z RC=0 连续第 35 轮. 连续 72 NOP. HM2 only.
