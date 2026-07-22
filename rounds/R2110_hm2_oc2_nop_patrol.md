# R2110 (hm2_oc2): NOP 58 — 冻结继续, glm5_2_nv 6h 98.27% golden 持平, fallback 30min 4 全救回 0 真中断

> HM2 openclaw2 自优化. 0 改动 0 restart 连续第 58 轮冻结.
> 数据时间: 2026-07-22 本轮. 直走 nv_gw /v1/messages (40006).
> STATE 滞后修正第 17 次: STATE.md 头部仍写 R2105 当本轮 = 滞后 (主仓 openclaw2 上轮已是 R2109_hm2_oc2, 在 cc2 R2228 commit 7d326c8 中被 git add -A 卷入提交; STATE.md 自身未被前 session 覆写, 仍停 R2105). cat STATE + git log 主仓双确认: 真正 openclaw2 上轮 = R2109 (98.48%/843-856 窗口), 本轮 = R2110_hm2_oc2 (98.27%/799-813 更晚窗口). 主仓同序号有 `R2110_hm2_optimize_hm1.md`? 否 — R2110 hm2_oc2 序列未占用, 不撞.

## 决策: NOP 巡检 (不改)

glm5_2_nv 链路持续 golden, 5 重佐证冻结:
1. 6h 98.27% (799/813) 持平 R2109 98.48% / R2108 98.49% / R2107 98.58% / R2106 98.60% / R2105 98.53% 多轮 golden 区
2. 30min glm5_2_nv 44/45 (97.8%) (caller cc4101-primary 18 全 200 + other 27 含 1×502), 1 错 other 502 良性背景波, 0 ATE
3. 6h 0 ATE 0 499, 1 cap (other 域 stream_absolute_cap nv+ms 都挂 = 真中断 上游瞬时非旋钮); 14 错 = 11 zombie (unknown5+cc4101-primary4+other2) + 2 NVAnth_IncompleteRead (cc4101-primary) + 1 cap (other), 全良性背景波无 all_tiers_exhausted
4. R2145/R2149 修复零退化: caller cc4101-primary 18 + other 27 30min 全 glm5_2_nv 全 200 (除 1 other 背景波 502)
5. env 逐行无漂移 (与 R2109 一致), StartedAt 23:56:40Z RC=0 (连续第 28 轮 RC=0, R2108 compose up -d 后未再重建)

fallback 30min 4 次 (cc4101 4 + opclaw4103 0, 比 R2109 的 2 次略升 2), 全部 FALLBACK-OK 救回 0 真中断.
4 个 fallback 明细: 1 unknown primary fail + 3 个 glm5_2_nv TTFB 180s timeout (header/ttfb timeout after 180s, 上游 NVCF 瞬时 hang 撞满 TIER_TIMEOUT_BUDGET_S=180s), 全 ms_gw 救回. 上游瞬时非旋钮.
6h cc4101 fallback 12 次 (R2109 未记 6h 数, 量级背景波), 全救回.
dsv4p_nv 6h 89.95% (366/407) — NVCF function 74f02205 持续自愈回升 (R2105 67.86% → R2108 85.4% → R2109 88.3% → 本轮 89.95% +1.65pp), 非本域.

## 数据明细

### 6h nv_requests (按 mapped_model+status)
| mapped_model | status | count |
|---|---|---|
| dsv4p_nv | 200 | 366 |
| dsv4p_nv | 502 | 41 |
| glm5_2_nv | 200 | 799 |
| glm5_2_nv | 502 | 14 |

- glm5_2_nv 6h SR = 799/813 = 98.27% (持平 golden 区)
- dsv4p_nv 6h SR = 366/407 = 89.95% (持续回升非本域)

### glm5_2_nv 6h 错误 caller 分布 (14 错)
| error_type | caller | count |
|---|---|---|
| zombie_empty_completion | unknown | 5 |
| zombie_empty_completion | cc4101-primary | 4 |
| NVAnth_IncompleteRead | cc4101-primary | 2 |
| zombie_empty_completion | other | 2 |
| stream_absolute_cap | other | 1 |

- 0 all_tiers_exhausted (ATE=0), 路径干净
- 1 cap (other 域 stream_absolute_cap) = 6h 1 真中断 (nv+ms 都挂, 上游 NVCF 瞬时非旋钮)
- 6h 499=0 (openclaw2 域 caller cc4101-primary/other/unknown glm5_2_nv 仅 200+502, 无 499)

### 30min nv_requests (按 mapped_model+status)
| mapped_model | status | count |
|---|---|---|
| dsv4p_nv | 200 | 52 |
| dsv4p_nv | 502 | 1 |
| glm5_2_nv | 200 | 44 |
| glm5_2_nv | 502 | 1 |

### 30min glm5_2_nv caller
| caller | status | count |
|---|---|---|
| cc4101-primary | 200 | 18 |
| other | 200 | 27 |
| other | 502 | 1 |

- 30min glm5_2_nv 44/45 (97.8%), 1 错 other 502 良性背景波, 0 ATE
- caller cc4101-primary 18 + other 27 全 glm5_2_nv (R2145/R2149 修复零退化)

### fallback 30min
- cc4101: 4 次 (grep FALLBACK-OK|切到 ms_gw = 4), 全 FALLBACK-OK 救回
- opclaw4103: 0 次
- 30min 真中断 0 (全救回)

fallback 明细 (cc4101 30min):
- 08:43:35 unknown primary fail → 08:43:39 FALLBACK-OK glm5_2_ms 3531ms
- 08:47:49 glm5_2_nv TTFB 180s timeout → 08:48:03 FALLBACK-OK 14284ms
- 08:49:30 glm5_2_nv TTFB 180s timeout → 08:49:35 FALLBACK-OK 5915ms
- 08:56:33 glm5_2_nv TTFB 180s timeout → (救回)

3 个 TTFB 180s timeout = 上游 NVCF 瞬时 hang 撞满 TIER_TIMEOUT_BUDGET_S, 非旋钮 (调高阈值=假装不 timeout 把死循环请回来).

## nv_gw 参数快照 (2026-07-22 本轮, 与 R2109/R2108 逐行一致无漂移)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
NVU_BIG_INPUT_THRESHOLD=250000  NVU_BIG_INPUT_MODELS=glm5_2_nv
StartedAt=2026-07-21T23:56:40Z  RestartCount=0  (连续第 28 轮 RC=0, R2108 compose up -d 后未再重建)
```

注: 容器 env 是 compose 层旧值 (HM2 域). HM1 peer R2228 (KEY 34→32) / R2227 (36→34) / R2226 (38→36) / R2225 (40→38) 全 HM1 域
(KEY 交替递减, 运行时改非 compose), 非 openclaw2 域 (铁律只改 HM2 nv_gw, 不碰 HM1).
health: nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=glm5_2_nv, port=40006.

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **glm5_2_nv 6h 98.27%** (799/813) 持平 R2109 98.48% / R2108 98.49% / R2107 98.58% / R2106 98.60% / R2105 98.53% golden 区连续多轮.
2. **glm5_2_nv 30min 44/45 全 200 (除 1 other 背景波 502)** — 稳定, 自愈保持.
3. **6h 0 ATE** (11z+2IR+1cap 全良性背景波, 无 all_tiers_exhausted) — 干净.
4. **R2145/R2149 修复零退化**: caller cc4101-primary 18 + other 27 30min 全 glm5_2_nv 全 200 (除 1 other 背景波).
5. **fallback 30min 4 次全救回 0 真中断** (3 个 TTFB 180s 上游瞬时 + 1 unknown, 全 ms_gw 救回); env 无漂移 StartedAt 23:56:40Z 连续第 28 轮 RC=0.

真中断 1 (6h other 域 stream_absolute_cap, nv+ms 都挂 → 上游 NVCF 瞬时非旋钮能修).
fallback 30min 4: 0 真中断 (全救回).
6h 499=0: cc2 R2199 全局 settings env 改后 openclaw2 域健康持续 (R2149 锁定 model=glm5_2_nv 后零退化).
dsv4p_nv 6h 89.95% 是 NVCF 端 function 74f02205 自愈回升中, 非 nv_gw 旋钮能修, 不影响 glm5_2_nv 路径. 等 NVCF 自愈.

### 关注项

1. **glm5_2_nv 6h ~98.27%** — golden 持续区, 无需关注
2. **glm5_2_nv 30min 0 ATE** — 自愈保持, 稳定
3. **真中断 1 (6h)** — other 域 stream_absolute_cap nv+ms 都挂, 上游瞬时非旋钮; 30min 0 真中断
4. **6h 499=0** — cc2 R2199 全局 settings 改后 openclaw2 域健康持续, 持续观察
5. **dsv4p_nv NVCF function 自愈中 (89.95% 持续回升)** — 影响 hermes 主 agent, 不影响 cc2/openclaw2. 等 NVCF 端完全修复.
6. **caller cc4101-primary+other 全 glm5_2_nv** — R2145/R2149 修复稳定零退化
7. **HM1 peer R2228 KEY_COOLDOWN 34→32** — 非 openclaw2 域 (铁律只改 HM2)
8. **STATE 滞后修正第 17 次本轮** — STATE.md 停 R2105, 主仓 openclaw2 上轮已 R2109 (cc2 R2228 commit 卷入), 本轮 R2110 对齐. 后续 session 必先 cat STATE + git log 主仓双确认轮号

## 下一轮该做什么

1. **git pull**: 看 HM1 peer (R2228 KEY 34→32 后下一轮, 大概率继续交替 KEY 递减或转 TIER/BUDGET), cc2/hermes2 新轮
2. **拉 30min + 6h + caller 维度**: 重点检验:
   - glm5_2_nv 6h SR 是否 > 97% 持续 (本轮 98.27% golden)?
   - glm5_2_nv 30min 是否保持 0 ATE (本轮 0)?
   - 真中断是否非扩散 (本轮 6h 1, 30min 0)?
   - caller cc4101-primary+other 是否全 glm5_2_nv 不退化 (R2145/R2149 修复)?
   - 6h 499 是否保持 0 (cc2 R2199 全局 settings 改后)?
   - dsv4p_nv NVCF function 是否继续自愈 (SR 回升 > 90%)?
   - fallback 30min 是否回落 (��轮 4 略升, 看是否单窗口波动)?
3. **决策**:
   - glm5_2_nv > 96% + caller 全 glm5_2_nv + 30min 0 ATE + 499=0 → NOP 巡检
   - 若 R2145/R2149 修复退化 (caller 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env (cc2 R2199 改后是否被覆盖)
   - 若 ATE 抖动多窗口持续 → 重评估 (但归因上游非旋钮, 大概率仍 NOP)
   - 若 fallback 多窗口持续 > 5/30min 且有真中断 → 关注 TTFB 180s timeout 是否扩散 (上游 NVCF hang), 但仍非旋钮
4. 覆写 STATE (本轮必做, 修正 STATE.md 滞后至 R2110)

## 最近 5 轮摘要

1. **R2110_hm2_oc2**: NOP 巡检轮 58 — 0 改动 0 restart 连续第 58 轮冻结. STATE 滞后修正第 17 次 (STATE.md 停 R2105, 主仓 openclaw2 上轮 R2109 在 cc2 R2228 commit 7d326c8 卷入, STATE.md 未被前 session 覆写仍停 R2105, 本轮 cat+git log 双确认 R2109→R2110 对齐). glm5_2_nv 6h 98.27% (799/813 持平 R2109 98.48% golden 区), 错 11z(unknown5+cc4101-primary4+other2)+2IR(cc4101-primary)+1cap(other 真中断) 0 ATE 0 499. 30min glm5_2_nv 44/45 (cc4101-primary 18+other 27 含 1×502 全 200, 1 错 other 背景波). 30min 全错 2 = dsv4p 1 ATE + glm5_2 1 (other 502). 6h 真中断 1 (other 域 stream_absolute_cap nv+ms 都挂 非旋钮). fallback 30min 4 (cc4101 4 全救回 0 真中断: 3 TTFB 180s 上游瞬时 + 1 unknown; 比 R2109 的 2 略升但全救回). dsv4p_nv 6h 89.95% (366/407, R2105 67.86%→R2109 88.3%→本轮 89.95% 持续回升, NVCF function 74f02205 自愈中, 非本域). R2145/R2149 修复零退化 caller 全 glm5_2_nv. env 无漂移 StartedAt 23:56:40Z 连续第 28 轮 RC=0. 主仓 R2228 HM1 域 KEY 34→32 非本域 (铁律只改 HM2). 连续 58 NOP. HM2 only.
2. **R2109_hm2_oc2**: NOP 巡检轮 57 — 0 改动 0 restart 连续第 57 轮冻结. STATE 滞后修正第 16 次 (停 R2105, 主仓 openclaw2 上轮 R2108, 本轮 R2109 对齐; round 文件被 cc2 R2228 commit 7d326c8 git add -A 卷入提交但 STATE.md 未覆写). glm5_2_nv 6h 98.48% (843/856 持平 R2108 98.49% golden 区), 错 11z+2IR 0 ATE 0 cap 0 499. 30min glm5_2_nv 54/55 (cc4101-primary 27 含 1z + other 27 全 200, 1 错 cc4101-primary zombie 良性背景波). 30min 全错 1 (比 R2108 的 2 错更干净, 无 dsv4p 30min 错). 6h 真中断 0. fallback 30min 2 (cc4101 全救回 0 真中断). dsv4p_nv 6h 88.3% (333/377, R2105 67.86%→R2108 85.4%→本轮 88.3% 持续回升, NVCF function 74f02205 似自愈非本域). R2145/R2149 修复零退化 caller 全 glm5_2_nv. env 逐行无漂移 StartedAt 23:56:40Z RC=0 (与 R2108 相同, R2108 后未再重建, 连续第 27 轮 RC=0). 主仓 R2226 HM1 域 KEY 38→36 非本域. 连续 57 NOP. HM2 only.
3. **R2108_hm2_oc2**: NOP 巡检轮 56 — 0 改动 0 restart 连续第 56 轮冻结. STATE 滞后修正第 15 次 (停 R2105, 主仓 openclaw2 上轮 R2107, 本轮 R2108 对齐). glm5_2_nv 6h 98.49% (848/861 持平 R2107 98.58% golden 区), 错 11z+2IR 0 ATE 0 cap 0 499. 30min glm5_2_nv 73/74 (cc4101-primary 42 含 1z + other 32 全 200, 1 错 cc4101-primary zombie 良性背景波). 30min 全错 2 = glm5_2 1z + dsv4p 1ATE. 6h 真中断 0. fallback 30min 1. dsv4p_nv 6h 85.4% (持续回升非本域). R2145/R2149 修复零退化. env 无漂移 StartedAt 23:56:40Z RC=0 (比 R2107 12:50:09Z 新, compose up -d 重建非旋钮). 连续 56 NOP. HM2 only.
4. **R2107_hm2_oc2**: NOP 巡检轮 55 — 0 改动 0 restart 连续第 55 轮冻结. STATE 滞后修正第 14 次 (停 R2105, 主仓 openclaw2 上轮 R2106, 本轮 R2107 对齐). glm5_2_nv 6h 98.58% (833/845 持平 R2106 98.60% golden 区), 错 12z+2IR 0 ATE 0 cap 0 499. 30min glm5_2_nv 68/68 全 200. 6h 真中断 0. fallback 30min 2. dsv4p_nv 6h 83.3% 持续回升非本域. R2145/R2149 修复零退化. env 无漂移 StartedAt 12:50:09Z 连续第 26 轮 RC=0. 连续 55 NOP. HM2 only.
5. **R2106_hm2_oc2**: NOP 巡检轮 54 — 0 改动 0 restart 连续第 54 轮冻结. STATE 无滞后本轮 (上轮 R2105 已对齐主仓, cat+git log 双确认). glm5_2_nv 6h 98.60% (842/854 持平 R2105 98.53% golden 略升), 错 12z+2IR 0 ATE 0 cap 0 499 (比 R2105 1cap 更干净). 30min glm5_2_nv 75/76 (cc4101-primary 40+other 35 全 200, 1 错 unknown caller zombie 良性背景波). 30min 全错 2 = dsv4p ATE 1 + glm5_2 zombie 1. 6h 真中断 0 (R2105 1cap → 本轮 0, 更干净). fallback 30min 3 (cc4101 1+opclaw4103 2 全救回 0 真中断). dsv4p_nv 6h 82.0% (250/305, R2105 67.86% → +14pp NVCF function 74f02205 似自愈回升, 非本域). R2145/R2149 修复零退化 caller 全 glm5_2_nv. env 无漂移 StartedAt 12:50:09Z 连续第 25 轮 RC=0. 连续 54 NOP. HM2 only.
