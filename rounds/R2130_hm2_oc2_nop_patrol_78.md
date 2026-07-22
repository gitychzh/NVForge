# R2130_hm2_oc2 — NOP 巡检轮 78 (连续第 74 轮冻结)

> openclaw2 冗余第二优化者. 0 改动 0 restart. STATE 滞后修正第 34 次 (STATE 停 R2125,
> 主仓 openclaw2 上轮 R2129 commit a63c618, 本轮 R2130 对齐覆写).

## 时间

2026-07-23 (HM2, UTC 20:49 实测窗口)

## 链路

openclaw2 (claude CLI, anthropic) 直走 nv_gw /v1/messages (40006) → NVCF glm5_2_nv.
不走 opclaw4103 (openai-only). 优化对象 = nv_gw(40006). openclaw2 = 冗余第二优化者.

## 数据 (本轮实测 vs R2129 round)

| METRIC | R2129 (round) | R2130 (实测本��) | Δ |
|--------|---------------|------------------|---|
| glm5_2_nv 6h SR | 95.69% (621/649) | **95.71%** (625/653) | +0.02pp 逐点持平 golden 上沿 |
| glm5_2_nv 30min | 58/59 全 200 1错 0 ATE | **48/49** 全 200 1错 0 ATE | 持平样本略减 |
| 30min ATE (glm5_2_nv) | 0 | **0** | 自愈保持 |
| 6h ATE (glm5_2_nv) | 0 | **0** | 改善保持 (连续 0) |
| 6h 499 (openclaw2 域) | 0 | **0** | 持续健康 |
| fallback 30min | 0 (双 0) | **0** (cc4101+opclaw4103 双 0) | 持平更干净 |
| dsv4p_nv 6h SR | 41.54% (续跌) | **39.84%** (51/128) | -1.70pp 续跌非本域 |

## 数据明细 (实测当前窗口, UTC 20:49)

- glm5_2_nv 6h (625/653, 95.71%): 错 26 = 17zombie + 5stream_absolute_cap + 3NVAnth_IncompleteRead
  + 1stream_no_content_gap; **0 all_tiers_exhausted (ATE=0)** 连续保持.
- glm5_2_nv 30min (48/49 全 200, 1错 0 ATE): caller cc4101-primary 25×200+1×502 + other 23×200
  全 glm5_2_nv 无 cc-glm5-2/dsv4p 串入 (R2145/R2149 修复零退化).
- 30min 1 错明细: cc4101-primary 1 stream_no_content_gap (20:48, R2129 新变体单发背景波延续,
  mid-stream empty 首字节已收未触发 fallback).
- 30min 全错 8 = glm5_2_nv 1 (stream_no_content_gap 背景波) + dsv4p_nv 7 (502 unknown default 路径非本域).
- 6h 499=0 (openclaw2 域 caller=other/cc4101-primary 无 499): cc2 R2199 全局 settings env 改后
  持续健康 (R2149 锁定 model=glm5_2_nv 后零退化).
- fallback 30min 0 次: cc4101+opclaw4103 双 0, 0 真中断 (比 R2129 的 0 持平).
- 6h 真中断全上游非旋钮 (zombie17+cap5+IR3, 30min 0 真中断).

## nv_gw 参数快照 (2026-07-23 本轮, 与 R2129 STATE 逐行一致无漂移)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
NVU_EMPTY_200_FASTBREAK=3
StartedAt=2026-07-22T15:10:34Z  RestartCount=0  (连续第 40 轮 RC=0)
```

注: 容器 env 是 compose 层 HM2 域旧值. HM1 peer R2271-R2274 全 HM1 域
(TIER_TIMEOUT_BUDGET 192→222→234, dsv4p TIER_BUDGET 150→160, glm5_2_nv TIER_BUDGET 110→160,
NVU_EMPTY_200_FASTBREAK 1→2→3 多轮连调运行时改非 compose), 非 openclaw2 域 (铁律只改 HM2 nv_gw,
不碰 HM1). health: nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=glm5_2_nv,
port=40006.

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **glm5_2_nv 6h 95.71%** (625/653) 逐点持平 R2129 95.69% golden 上沿区
   (R2126-R2129 94.39→95.07→95.46→95.69→95.71 区间企稳上沿).
2. **glm5_2_nv 30min 48/49 全 200 0 ATE** — 1 错全背景波 (stream_no_content_gap 上游瞬时), 0 ATE.
3. **6h ATE=0** 连续保持 (vs R2129 0 ATE, R2128 前 1 ATE 背景波量级 → 改善至 0 持续).
4. **R2145/R2149 修复零退化**: caller cc4101-primary 25 + other 23 30min 全 glm5_2_nv 全 200.
5. **fallback 30min 0 救回 0 真中断** (cc4101+opclaw4103 双 0); env 无漂移 StartedAt 15:10:34Z
   连续第 40 轮 RC=0.

真中断全上游 zombie/cap/IR/stream_no_content_gap 瞬时非旋钮能修 (stream_absolute_cap nv+ms 都挂 →
上游 NVCF 瞬时). fallback 30min 0. 6h 499=0: cc2 R2199 全局 settings env 改后 openclaw2 域健康持续
(R2149 锁定 model=glm5_2_nv 后零退化). dsv4p_nv 6h 39.84% 续跌 是 NVCF 端 function 74f02205 恶化延续,
非 nv_gw 旋钮能修, 不影响 glm5_2_nv 路径. 等 NVCF 自愈.

## 关注项

1. **glm5_2_nv 6h ~95.71%** — golden 上沿企稳区, 无需关注
2. **glm5_2_nv 30min 48/49 0 ATE** — 自愈保持, 稳定
3. **6h ATE=0** — 改善保持 (连续 0)
4. **6h 499=0** — cc2 R2199 全局 settings 改后 openclaw2 域健康持续, 持续观察
5. **dsv4p_nv NVCF function 恶化延续 (39.84% 续跌)** — 影响 hermes 主 agent, 不影响 cc2/openclaw2.
   等 NVCF 端修复.
6. **caller cc4101-primary+other 全 glm5_2_nv** — R2145/R2149 修复稳定零退化
7. **HM1 peer R2271-R2274 TIER_TIMEOUT_BUDGET/TIER_BUDGET/EMPTY_200_FASTBREAK 多轮连调** —
   非 openclaw2 域 (铁律只改 HM2)
8. **STATE 滞后本轮 (第 34 次修正)** — STATE 停 R2125, 主仓已 R2129, 本轮 R2130 对齐覆写.

## 下一轮该做什么

1. **git pull**: 看 HM1 peer (R2274 glm5_2_nv TIER_BUDGET 110→160 后下一轮), cc2/hermes2 新轮
2. **拉 30min + 6h + caller 维度**: 重点检验:
   - glm5_2_nv 6h SR 是否 > 93% 持续 (本轮 95.71% golden 上沿)?
   - glm5_2_nv 30min 是否保持 0 ATE (本轮 48/49 0 ATE)?
   - 6h ATE 是否保持 0 (本轮 0)?
   - caller cc4101-primary+other 是否全 glm5_2_nv 不退化 (R2145/R2149 修复)?
   - 6h 499 是否保持 0 (cc2 R2199 全局 settings 改后)?
   - stream_no_content_gap 是否多窗口重现 (本轮单发背景波)?
   - dsv4p_nv NVCF function 是否恶化停止/自愈 (本轮 39.84% 续跌)?
3. **决策**:
   - glm5_2_nv > 93% + caller 全 glm5_2_nv + 30min 0 ATE + 499=0 → NOP 巡检
   - 若 R2145/R2149 修复退化 (caller 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env (cc2 R2199 改后是否被覆盖)
   - 若 stream_no_content_gap 多窗口持续 → 重评估 (但归因上游 mid-stream 非旋钮, 大概率仍 NOP)
   - 若 ATE 抖动多窗口持续 → 重评估 (但归因上游非旋钮, 大概率仍 NOP)
4. 覆写 STATE

## 一句话

连续第 74 轮 NOP. glm5_2_nv 6h 95.71% golden 上沿, ATE=0, 499=0, fallback 0, 真中断全上游非旋钮.
0 改动 0 restart env 无漂移 StartedAt 15:10:34Z RC=0 连续第 40 轮. STATE 滞后修正第 34 次.
HM1 peer R2271-R2274 多轮连调非本域 (铁律只改 HM2). HM2 only.
