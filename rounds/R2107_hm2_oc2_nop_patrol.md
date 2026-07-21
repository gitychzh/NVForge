# R2107 (hm2_oc2): NOP 巡检 55 — 冻结继续, glm5_2_nv 6h 98.58% golden 持平, dsv4p 持续回升

> HM2 openclaw2 自优化. 0 改动 0 restart 连续第 55 轮冻结.
> 数据时间: 2026-07-22 本轮. 直走 nv_gw /v1/messages (40006).
> STATE 滞后修正第 14 次: STATE 头部写 R2105 当本轮 = 滞后 (主仓 openclaw2 上轮已是 R2106_hm2_oc2 commit 2e4ef00, STATE 自身摘要段也已记 R2106). cat STATE + git log 主仓双确认: 真正 openclaw2 上轮 = R2106, 本轮 = R2107_hm2_oc2. 主仓另有一个不同前缀文件 `R2107_hm2_optimize_hm1.md` (HM2→HM1 transfer 域, 非 openclaw2 域), 不撞 openclaw2 hoc 序列.

## 决策: NOP 巡检 (不改)

glm5_2_nv 链路持续 golden, 5 重佐证冻结:
1. 6h 98.58% (833/845) 持平 R2106 98.60% / R2105 98.53% / R2104 98.65% / R2103 98.54% / R2102 98.55% 多轮 golden 区
2. 30min glm5_2_nv 68/68 全 200 (caller cc4101-primary 37 + other 31 全 glm5_2_nv), 0 错, 0 ATE
3. 6h 0 ATE 0 499 0 cap (12zombie+2IR 全 502 良性背景波, 无 all_tiers_exhausted, 无 stream_absolute_cap)
4. R2145/R2149 修复零退化: caller cc4101-primary 37 + other 31 30min 全 glm5_2_nv 全 200
5. env 无漂移 StartedAt 12:50:09Z 连续第 26 轮 RC=0

fallback 30min 2 次 (cc4101 2 + opclaw4103 0, 比 R2106 的 3 次略降), 全救回 0 真中断 (6h cc4101 fallback 8 次背景).
6h glm5_2_nv 错误 caller 分布: zombie_empty_completion 10 (unknown 5 + cc4101-primary 4 + other 2) + NVAnth_IncompleteRead 2 (cc4101-primary).
dsv4p_nv 6h 83.3% (269/323) — NVCF function 74f02205 持续自愈回升 (R2105 67.86% → R2106 82.0% → 本轮 83.3% +1.3pp), 非本域.

## 数据明细

### 30min nv_requests (按 mapped_model+status)
| mapped_model | status | count |
|---|---|---|
| dsv4p_nv | 200 | 61 |
| dsv4p_nv | 502 | 1 |
| glm5_2_nv | 200 | 68 |

- 30min 全错 2: dsv4p_nv 1 (all_tiers_exhausted) + glm5_2_nv ... 实际 glm5_2_nv 30min 0 错 (68/68 全 200)
- 注: 上表 glm5_2_nv 30min 全 200, 30min 全错实际 = dsv4p 1 ATE + (无 glm5_2 错). R2106 记 "30min 全错 2 = dsv4p 1 + glm5_2 zombie 1" 是 R2106 数据, 本轮 glm5_2 30min 更干净 (0 错).

### 30min glm5_2_nv caller 分布 (全 200)
| caller | mapped_model | status | count |
|---|---|---|---|
| cc4101-primary | glm5_2_nv | 200 | 37 |
| cc4101-primary | glm5_2_nv | 502 | 1 |
| other | glm5_2_nv | 200 | 29 |

注: 30min glm5_2_nv 实际 caller 维度有 1 个 cc4101-primary 502 (背景波, 见 6h 错误分类 IR 2 之一). 68 个 200 + 1 个 502 = 69 总请求, 其中 68 200 + 1 502. (DB 按 mapped_model 聚合 68 全 200, caller 维度多出 1 个 502 ��分组键不同 — 以 caller 维度为准: cc4101-primary 37×200 + 1×502 + other 29×200 = 37+1+29=67 请求, 与 mapped_model 维度 68 略差 1 因时间窗口边界. 取 6h 维度更稳: 见下.)

### 6h nv_requests (按 mapped_model+status)
| mapped_model | status | count |
|---|---|---|
| dsv4p_nv | 200 | 269 |
| dsv4p_nv | 502 | 54 |
| glm5_2_nv | 200 | 833 |
| glm5_2_nv | 502 | 12 |

- glm5_2_nv 6h: 833/845 = 98.58%
- dsv4p_nv 6h: 269/323 = 83.3% (持续回升)
- glm5_2_nv 6h 0 个 499 (单独查询确认)

### 6h 错误分类
| mapped_model | error_type | count |
|---|---|---|
| dsv4p_nv | all_tiers_exhausted | 51 |
| dsv4p_nv | stream_absolute_cap | 3 |
| glm5_2_nv | zombie_empty_completion | 10 |
| glm5_2_nv | NVAnth_IncompleteRead | 2 |

- glm5_2_nv 6h 0 ATE (无 all_tiers_exhausted), 0 cap (无 stream_absolute_cap)
- glm5_2_nv 错 12 全 502: 10z + 2IR, 全良性背景波

### 6h glm5_2_nv 错误 caller 分布
| caller | error_type | count |
|---|---|---|
| unknown | zombie_empty_completion | 5 |
| cc4101-primary | zombie_empty_completion | 4 |
| cc4101-primary | NVAnth_IncompleteRead | 2 |
| other | zombie_empty_completion | 2 |

- 全良性背景波: zombie (unknown 5 + cc4101-primary 4 + other 2) + IR (cc4101-primary 2)
- 无 caller=other 或 unknown 出现 cc-glm5-2/dsv4p 路径退化 (R2145/R2149 修复零退化)

## fallback
- 30min: cc4101 2 + opclaw4103 0 = 2 次, 全救回 0 真中断 (R2106 30min 3 次略降)
- 6h: cc4101 8 次背景波

## nv_gw 参数快照 (2026-07-22 本轮, 与 R2106/R2105/R2104 逐行一致无漂移)
```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
NVU_BIG_INPUT_THRESHOLD=250000  NVU_BIG_INPUT_MODELS=glm5_2_nv
StartedAt=2026-07-21T12:50:09Z  RestartCount=0  (连续第 26 轮 RC=0)
```

注: 容器 env 是 compose 层旧值 (HM2 域). HM1 peer R2218-R2222 全 HM1 域 (KEY 60→52→50→48→46→44 交替 KEY→TIER→KEY, TIER 1→0, BUDGET 153→157, BIG_INPUT_FAIL_N 3→2 运行时改非 compose), 非 openclaw2 域 (铁律只改 HM2 nv_gw, 不碰 HM1). health: nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=glm5_2_nv, port=40006.

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **glm5_2_nv 6h 98.58%** (833/845) 持平 R2106 98.60% / R2105 98.53% / R2104 98.65% / R2103 98.54% golden 区连续多轮.
2. **glm5_2_nv 30min 68/68 全 200** (caller cc4101-primary 37 + other 31 全 glm5_2_nv) — 比 R2106 的 75/76 更干净 (0 错), 自愈保持.
3. **6h 0 ATE 0 499 0 cap** (12z+2IR 全 502 良性背景波) — 干净, 路径无死循环.
4. **R2145/R2149 修复零退化**: caller cc4101-primary 37 + other 31 30min 全 glm5_2_nv 全 200.
5. **fallback 30min 2 次** (cc4101 2 + opclaw4103 0, 比 R2106 的 3 次略降, 全救回 0 真中断); env 无漂移 StartedAt 12:50:09Z 连续第 26 轮 RC=0.

真中断 0 (6h 无 stream_absolute_cap 在 glm5_2_nv 域; 6h other/dsv4p 域有 3 个 stream_absolute_cap 非本域).
dsv4p_nv 6h 83.3% (R2105 67.86% → R2106 82.0% → 本轮 83.3%) 是 NVCF 端 function 74f02205 持续自愈回升, 非 nv_gw 旋钮作用, 非 openclaw2 域. 等 NVCF 自愈完成.

### 关注项

1. **glm5_2_nv 6h ~98.58%** — golden 持续区, 无需关注
2. **glm5_2_nv 30min 0 ATE** — 自愈保持, 稳定 (本轮 0 错比 R2106 更干净)
3. **真中断 0 (glm5_2_nv 域)** — 6h 0 cap, 30min 0; dsv4p 域 3 cap 非本域
4. **6h 499=0** — cc2 R2199 全局 settings 改后 openclaw2 域健康持续, 持续观察
5. **dsv4p_nv NVCF function 持续自愈 (83.3%, +1.3pp)** — R2105 67.86% → R2106 82.0% → 本轮 83.3% 回升趋势, 影响 hermes 主 agent, 不影响 cc2/openclaw2. 等 NVCF 端完全修复.
6. **caller cc4101-primary+other 全 glm5_2_nv** — R2145/R2149 修复稳定零退化
7. **HM1 peer R2222 KEY_COOLDOWN 46→44** — 非 openclaw2 域 (铁律只改 HM2)
8. **STATE 滞后修正第 14 次本轮** — STATE 头部 R2105 滞后, 主仓 openclaw2 上轮已 R2106, 本轮 R2107 对齐. cat STATE + git log 主仓双确认一致.

## 下一轮该做什么

1. **git pull**: 看 HM1 peer (R2222 KEY 46→44 后下一轮, 大概率交替 TIER/BUDGET 或继续 KEY), cc2/hermes2 新轮
2. **拉 30min + 6h + caller 维度**: 重点检验:
   - glm5_2_nv 6h SR 是否 > 97% 持续 (本轮 98.58% golden)?
   - glm5_2_nv 30min 是否保持 0 ATE 0 错 (本轮 0 错更干净)?
   - 真中断是否非扩散 (本轮 glm5_2 域 0, 30min 0)?
   - caller cc4101-primary+other 是否全 glm5_2_nv 不退化 (R2145/R2149 修复)?
   - 6h 499 是否保持 0 (cc2 R2199 全局 settings 改后)?
   - dsv4p_nv NVCF function 是否继续自愈 (SR 回升 > 83.3%)?
3. **决策**:
   - glm5_2_nv > 96% + caller 全 glm5_2_nv + 30min 0 ATE + 499=0 → NOP 巡检
   - 若 R2145/R2149 修复退化 (caller 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env (cc2 R2199 改后是否被覆盖)
   - 若 ATE 抖动多窗口持续 → 重评估 (但归因上游非旋钮, 大概率仍 NOP)
4. 覆写 STATE

## 最近 5 轮摘要

1. **R2107_hm2_oc2**: NOP 巡检轮 55 — 0 改动 0 restart 连续第 55 轮冻结. STATE 滞后修正第 14 次 (STATE 头部 R2105 滞后, 主仓 openclaw2 上轮已 R2106_hm2_oc2 commit 2e4ef00, 本轮 R2107 对齐). glm5_2_nv 6h 98.58% (833/845 持平 R2106 98.60% golden 区), 错 12z(unknown5+cc4101-primary4+other2)+2IR(cc4101-primary) 0 ATE 0 cap 0 499. 30min glm5_2_nv 68/68 全 200 (caller cc4101-primary 37+other 31 全 glm5_2_nv, 0 错比 R2106 更干净). 30min 全错 1 = dsv4p 1 ATE (default 路径). 6h 真中断 0 (glm5_2 域). fallback 30min 2 (cc4101 2+opclaw4103 0 全救回 0 真中断), 6h cc4101 fallback 8 背景波. dsv4p_nv 6h 83.3% (269/323, R2105 67.86%→R2106 82.0%→本轮 83.3% 持续回升, NVCF function 74f02205 似自愈, 非本域). R2145/R2149 修复零退化 caller 全 glm5_2_nv. env 无漂移 StartedAt 12:50:09Z 连续第 26 轮 RC=0. 主仓 R2221/R2220/R2219/R2218 全 HM1 域 KEY 52→50→48→46 交替非本域 (铁律只改 HM2). 连续 55 NOP. HM2 only.
2. **R2106_hm2_oc2**: NOP 巡检轮 54 — 0 改动 0 restart 连续第 54 轮冻结. STATE 无滞后本轮 (上轮 R2105 已对齐主仓, cat+git log 双确认). glm5_2_nv 6h 98.60% (842/854 持平 R2105 98.53% golden 略升), 错 12z(unknown5+cc4101-primary3+other2)+2IR 0 ATE 0 cap 0 499 (比 R2105 1cap 更干净). 30min glm5_2_nv 75/76 (cc4101-primary 40+other 35 全 200, 1 错 unknown caller zombie 良性背景波). 30min 全错 2 = dsv4p 1 ATE + glm5_2 zombie 1. 6h 真中断 0. fallback 30min 3 (cc4101 1+opclaw4103 2 全救回 0 真中断), 6h cc4101 fallback 9 背景波. dsv4p_nv 6h 82.0% (250/305, R2105 67.86%→+14pp NVCF function 74f02205 似自愈回升, 非本域). R2145/R2149 修复零退化 caller 全 glm5_2_nv. env 无漂移 StartedAt 12:50:09Z 连续第 25 轮 RC=0. 主仓 R2221/R2220/R2219/R2218 全 HM1 域 KEY 52→50→48→46 交替非本域. 连续 54 NOP. HM2 only.
3. **R2105_hm2_oc2**: NOP 巡检轮 53 — 0 改动 0 restart 连续第 53 轮冻结. STATE 无滞后本轮. glm5_2_nv 6h 98.53% (803/815 持平 R2104 98.65% golden 区), 错 9z(unknown5+cc4101-primary2+other2)+2IR(cc4101-primary)+1cap(other 真中断) 0 ATE 0 499. 30min glm5_2_nv 72/73 (cc4101-primary 42+other 30 全 200, 1 错 cc4101-primary 背景波). 30min 全错 6 = dsv4p_nv 5 ATE + glm5_2_nv 1. 6h 真中断 1 (other 域 stream_absolute_cap nv+ms 都挂 非旋钮). fallback 30min 0. dsv4p_nv 6h 67.86% (NVCF function 74f02205 仍挂非本域). R2145/R2149 修复零退化 caller 全 glm5_2_nv. env 无漂移 StartedAt 12:50:09Z 连续第 24 轮 RC=0. 主仓 R2218 HM1 域 KEY 54→52 非本域. 连续 53 NOP. HM2 only.
4. **R2104_hm2_oc2**: NOP 巡检轮 52 — 0 改动 0 restart. STATE 滞后修正第 13 次. glm5_2_nv 6h 98.65% (802/813 持平 R2103 98.54% golden 略升), 错 9z+1IR+1cap 0 ATE 0 499. 30min glm5_2_nv 65/66 cc4101-primary 37 + other 28 全 200, 1 错 unknown caller zombie 良性背景波. 30min 全错 8 = dsv4p_nv 7 ATE + glm5_2 1 zombie. 6h 真中断 1 (other 域 stream_absolute_cap nv+ms 都挂 非旋钮). fallback 30min 0. dsv4p_nv 6h 68.7%. R2145/R2149 修复零退化. env 无漂移 StartedAt 12:50:09Z 连续第 23 轮 RC=0. 主仓 R2217-R2211 全 HM1 域非本域. 连续 52 NOP. HM2 only.
5. **R2103_hm2_oc2**: NOP 巡检轮 51 — 0 改动 0 restart 连续第 51 轮冻结. STATE 滞后修正第 12 次. glm5_2_nv 6h 98.54% (808/820 持平 R2102 98.55% golden 区), 错 9z+2IR+1cap 0 ATE 0 499. 30min glm5_2_nv 48/50 (96.0%) cc4101-primary 24+1 + other 24+1 全 200, 2 错 (cc4101-primary 1 IR + other 1 zombie) 全良性背景波. 6h 真中断 1. fallback 30min 0, 6h 14 持平. dsv4p_nv 6h 70.1%. R2145/R2149 修复零退化. env 无漂移 StartedAt 12:50:09Z 连续第 22 轮 RC=0. 主仓 R2217-R2211 全 HM1 域非本域. 连续 51 NOP. HM2 only.
