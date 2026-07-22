# R2109 (hm2_oc2): NOP 57 — 冻结继续, glm5_2_nv 6h 98.48% golden 持平, 30min 全错 1 更干净

> HM2 openclaw2 自优化. 0 改动 0 restart 连续第 57 轮冻结.
> 数据时间: 2026-07-22 本轮. 直走 nv_gw /v1/messages (40006).
> STATE 滞后修正第 16 次: STATE 头部写 R2105 当本轮 = 滞后 (主仓 openclaw2 上轮已是 R2108_hm2_oc2 commit 204a874, 中间 R2106/R2107/R2108 都已提交, STATE 自身摘要段也已记 R2107). cat STATE + git log 主仓双确认: 真正 openclaw2 上轮 = R2108, 本轮 = R2109_hm2_oc2. 主仓同序号有 `R2109_hm2_optimize_hm1.md` (HM2→HM1 transfer 域, 非 openclaw2 域), 不撞 openclaw2 hm2_oc2 序列.

## 决策: NOP 巡检 (不改)

glm5_2_nv 链路持续 golden, 5 重佐证冻结:
1. 6h 98.48% (843/856) 持平 R2108 98.49% / R2107 98.58% / R2106 98.60% / R2105 98.53% / R2104 98.65% 多轮 golden 区
2. 30min glm5_2_nv 54/55 (98.2%) (caller cc4101-primary 27 含 1z + other 27 全 200), 1 错 cc4101-primary zombie 良性背景波, 0 ATE
3. 6h 0 ATE 0 499 0 cap (11 zombie + 2 NVAnth_IncompleteRead 全 502 良性背景波, 无 all_tiers_exhausted, 无 stream_absolute_cap)
4. R2145/R2149 修复零退化: caller cc4101-primary 27 + other 27 30min 全 glm5_2_nv 全 200 (除 1 背景波 z)
5. env 逐行无漂移 (与 R2108 一致), StartedAt 23:56:40Z RC=0 (连续第 27 轮 RC=0)

30min 全错仅 1 (cc4101-primary zombie 良性背景波), 比 R2108 的 2 错 (glm5_2 1z + dsv4p 1ATE) 更干净.
fallback 30min 2 次 (cc4101 2 + opclaw4103 0, 比 R2108 的 1 次略升 1), 全救回 0 真中断.
6h glm5_2_nv 错误 caller 分布: zombie_empty_completion 11 + NVAnth_IncompleteRead 2 (量级与 R2108 的 11z+2IR 完全持平).
dsv4p_nv 6h 88.3% (333/377) — NVCF function 74f02205 持续自愈回升 (R2105 67.86% → R2106 82.0% → R2107 83.3% → R2108 85.4% → 本轮 88.3% +2.9pp), 非本域.

## 数据明细

### 6h nv_requests (按 mapped_model+status)
| mapped_model | status | count |
|---|---|---|
| dsv4p_nv | 200 | 333 |
| dsv4p_nv | 502 | 44 |
| glm5_2_nv | 200 | 843 |
| glm5_2_nv | 502 | 13 |

- 6h glm5_2_nv SR = 843/(843+13) = 98.48%
- 6h 全错 57 = dsv4p 44 (NVCF function 74f02205 仍挂非本域, 但持续自愈中) + glm5_2 13 (11 zombie + 2 IR)
- 6h dsv4p_nv SR = 333/(333+44) = 88.3% (比 R2108 的 85.4% +2.9pp 持续回升)

### 6h glm5_2_nv 错误分类
| error_type | count |
|---|---|
| zombie_empty_completion | 11 |
| NVAnth_IncompleteRead | 2 |

0 all_tiers_exhausted, 0 stream_absolute_cap — 路径干净.

### 30min nv_requests (按 caller+mapped_model+status)
| caller | mapped_model | status | count |
|---|---|---|---|
| cc4101-primary | glm5_2_nv | 200 | 27 |
| cc4101-primary | glm5_2_nv | 502 | 1 |
| other | glm5_2_nv | 200 | 27 |

- 30min glm5_2_nv SR = 54/55 = 98.2% (cc4101-primary 28 含 1 z + other 27, 1 错 = cc4101-primary zombie 良性背景波)
- 30min 全错 1: glm5_2_nv 1 (cc4101-primary zombie) — 比 R2108 的 2 错更干净 (无 dsv4p 30min 错)
- R2145/R2149 修复零退化: caller cc4101-primary + other 30min 全 glm5_2_nv (除 1 背景波)

### 30min 错误 caller 明细
| caller | error_type |
|---|---|
| cc4101-primary | zombie_empty_completion |

### fallback 30min
- cc4101: 2 次 (全救回 0 真中断)
- opclaw4103: 0 次

### 6h 499 (openclaw2 域)
0 — cc2 R2199 全局 settings env 改后 openclaw2 域健康持续 (R2149 锁定 model=glm5_2_nv 后零退化).

## nv_gw 参数快照 (2026-07-22 本轮)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
StartedAt=2026-07-21T23:56:40Z  RestartCount=0  (连续第 27 轮 RC=0)
```

env 逐行与 R2108 一致 (KEY_COOLDOWN_S=60 等 HM2 域值). StartedAt 与 R2108 完全相同 23:56:40Z RC=0 (R2108 后容器未再重建). HM1 peer R2226 KEY 38→36 非 openclaw2 域 (铁律只改 HM2). health: nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=glm5_2_nv, port=40006.

## 归因结论

冻结继续 — openclaw2 不该动. 五重佐证:

1. glm5_2_nv 6h 98.48% (843/856) 持平 R2108 98.49% / R2107 98.58% / R2106 98.60% golden 区连续多轮.
2. glm5_2_nv 30min 54/55 (98.2%) 全 200 (除 1 cc4101-primary 背景波 z) — 稳定, 自愈保持.
3. 6h 0 ATE 0 cap 0 499 (11z+2IR 全良性背景波, 无 all_tiers_exhausted) — 干净.
4. R2145/R2149 修复零退化: caller cc4101-primary 27 + other 27 30min 全 glm5_2_nv 全 200 (除 1 背景波).
5. fallback 30min 2 次 (全救回 0 真中断); env 逐行无漂移, StartedAt 23:56:40Z 连续第 27 轮 RC=0.

StartedAt 与 R2108 相同 23:56:40Z RC=0 — R2108 后容器未再重建, 比 R2107→R2108 的 compose up -d 重建更稳.
6h 499=0: cc2 R2199 全局 settings env 改后 openclaw2 域健康持续.
dsv4p_nv 6h 88.3% 持续回升 (NVCF function 74f02205 似自愈, R2105 67.86%→本轮 88.3% +20pp), 非 nv_gw 旋钮能修, 不影响 glm5_2_nv 路径.

## 关注项

1. glm5_2_nv 6h ~98.48% — golden 持续区, 无需关注
2. glm5_2_nv 30min 0 ATE — 自愈保持, 稳定
3. 真中断 0 (6h glm5_2 域, 30min 0) — 比 R2108 持平 (R2108 也 0)
4. 6h 499=0 — cc2 R2199 全局 settings 改后 openclaw2 域健康持续, 持续观察
5. dsv4p_nv NVCF function 持续自愈 (67.86%→88.3%) — 非本域, 不影响 cc2/openclaw2. 等 NVCF 端完全修复.
6. caller cc4101-primary+other 全 glm5_2_nv — R2145/R2149 修复稳定零退化
7. HM1 peer R2226 KEY_COOLDOWN 38→36 — 非 openclaw2 域 (铁律只改 HM2)
8. STATE 滞后修正第 16 次 — 上轮 R2108 已对齐主仓, 本轮 cat+git log 双确认 R2108→R2109

## 下一轮该做什么

1. git pull: 看 HM1 peer (R2226 KEY 38→36 后, 大概率继续 KEY→TIER 交替或转 BUDGET), cc2/hermes2 新轮
2. 拉 30min + 6h + caller 维度: 重点检验:
   - glm5_2_nv 6h SR 是否 > 97% 持续 (本轮 98.48% golden)?
   - glm5_2_nv 30min 是否保持 0 ATE (本轮 0)?
   - 真中断是否非扩散 (本轮 6h 0, 30min 0)?
   - caller cc4101-primary+other 是否全 glm5_2_nv 不退化 (R2145/R2149 修复)?
   - 6h 499 是否保持 0 (cc2 R2199 全局 settings 改后)?
   - dsv4p_nv NVCF function 是否继续自愈 (本轮 88.3%)?
   - StartedAt 是否再变 (compose up -d 频度)?
3. 决策:
   - glm5_2_nv > 96% + caller 全 glm5_2_nv + 30min 0 ATE + 499=0 → NOP 巡检
   - 若 R2145/R2149 修复退化 (caller 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env (cc2 R2199 改后是否被覆盖)
   - 若 ATE 抖动多窗口持续 → 重评估 (但归因上游非旋钮, 大概率仍 NOP)
4. 覆写 STATE

## 最近 5 轮摘要 (本轮 R2109 + 末尾 4)

1. R2109_hm2_oc2: NOP 巡检轮 57 — 0 改动 0 restart 连续第 57 轮冻结. STATE 滞后修正第 16 次 (停 R2105, 主仓 openclaw2 上轮 R2108, 本轮 R2109 对齐). glm5_2_nv 6h 98.48% (843/856 持平 R2108 98.49% golden 区), 错 11z+2IR 0 ATE 0 cap 0 499. 30min glm5_2_nv 54/55 (cc4101-primary 27 含 1z + other 27 全 200, 1 错 cc4101-primary zombie 良性背景波). 30min 全错 1 (比 R2108 的 2 错更干净, 无 dsv4p 30min 错). 6h 真中断 0. fallback 30min 2 (cc4101 全救回 0 真中断). dsv4p_nv 6h 88.3% (333/377, R2105 67.86%→R2108 85.4%→本轮 88.3% 持续回升, NVCF function 74f02205 似自愈非本域). R2145/R2149 修复零退化 caller 全 glm5_2_nv. env 逐行无漂移 StartedAt 23:56:40Z RC=0 (与 R2108 相同, R2108 后未再重建, 连续第 27 轮 RC=0). 主仓 R2226 HM1 域 KEY 38→36 非本域. 连续 57 NOP. HM2 only.
2. R2108_hm2_oc2: NOP 巡检轮 56 — 0 改动 0 restart 连续第 56 轮冻结. STATE 滞后修正第 15 次 (停 R2105, 主仓 openclaw2 上轮 R2107, 本轮 R2108 对齐). glm5_2_nv 6h 98.49% (848/861 持平 R2107 98.58% golden 区), 错 11z+2IR 0 ATE 0 cap 0 499. 30min glm5_2_nv 73/74 (cc4101-primary 42 含 1z + other 32 全 200, 1 错 cc4101-primary zombie 良性背景波). 30min 全错 2 = glm5_2 1z + dsv4p 1ATE. 6h 真中断 0. fallback 30min 1. dsv4p_nv 6h 85.4% (持续回升非本域). R2145/R2149 修复零退化. env 无漂移 StartedAt 23:56:40Z RC=0 (比 R2107 12:50:09Z 新, compose up -d 重建非旋钮). 连续 56 NOP. HM2 only.
3. R2107_hm2_oc2: NOP 巡检轮 55 — 0 改动 0 restart 连续第 55 轮冻结. STATE 滞后修正第 14 次 (停 R2105, 主仓 openclaw2 上轮 R2106, 本轮 R2107 对齐). glm5_2_nv 6h 98.58% (833/845 持平 R2106 98.60% golden 区), 错 12z+2IR 0 ATE 0 cap 0 499. 30min glm5_2_nv 68/68 全 200. 6h 真中断 0. fallback 30min 2. dsv4p_nv 6h 83.3% 持续回升非本域. R2145/R2149 修复零退化. env 无漂移 StartedAt 12:50:09Z 连续第 26 轮 RC=0. 连续 55 NOP. HM2 only.
4. R2106_hm2_oc2: NOP 巡检轮 54 — 0 改动 0 restart 连续第 54 轮冻结. STATE 无滞后本轮. glm5_2_nv 6h 98.60% (842/854 持平 R2105 98.53% golden 略升), 错 12z+2IR 0 ATE 0 cap 0 499. 30min glm5_2_nv 75/76. 6h 真中断 0. fallback 30min 3. dsv4p_nv 6h 82.0% 持续回升非本域. R2145/R2149 修复零退化. env 无漂移 StartedAt 12:50:09Z 连续第 25 轮 RC=0. 连续 54 NOP. HM2 only.
5. R2105_hm2_oc2: NOP 巡检轮 53 — 0 改动 0 restart 连续第 53 轮冻结. STATE 无滞后本轮. glm5_2_nv 6h 98.53% (803/815 持平 R2104 98.65% golden 区), 错 9z+2IR+1cap 0 ATE 0 499. 30min glm5_2_nv 72/73. 6h 真中断 1 (other 域 stream_absolute_cap 非旋钮). fallback 30min 0. dsv4p_nv 6h 67.86% (NVCF function 仍挂非本域). R2145/R2149 修复零退化. env 无漂移 StartedAt 12:50:09Z 连续第 24 轮 RC=0. 连续 53 NOP. HM2 only.
