# R2106 (hm2_oc2): NOP 巡检 54 — 冻结继续, glm5_2_nv 6h 98.60% golden 持平, dsv4p 自愈回升 +14pp

> HM2 openclaw2 自优化. 0 改动 0 restart 连续第 54 轮冻结.
> 数据时间: 2026-07-22 本轮. 直走 nv_gw /v1/messages (40006).
> STATE 无滞后本轮 (上轮 R2105 已对齐主仓, cat+git log 双确认一致).

## 决策: NOP 巡检 (不改)

glm5_2_nv 链路持续 golden, 5 重佐证冻结:
1. 6h 98.60% (842/854) 持平 R2105 98.53% / R2104 98.65% / R2103 98.54% / R2102 98.55% 多轮 golden 区 (略升)
2. 30min glm5_2_nv 75/76 全 200 (caller cc4101-primary 40 + other 35 全 glm5_2_nv), 1 错 (unknown caller zombie 良性背景波), 0 ATE
3. 6h 0 ATE 0 499 (12zombie+2IR 全良性背景波, 无 all_tiers_exhausted, 无 cap)
4. R2145/R2149 修复零退化: caller cc4101-primary 40 + other 35 30min 全 glm5_2_nv 全 200
5. env 无漂移 StartedAt 12:50:09Z 连续第 25 轮 RC=0

fallback 30min 3 次 (cc4101 1 + opclaw4103 2), 全救回 0 真中断 (6h cc4101 fallback 9 次背景).
6h glm5_2_nv 错误 caller 分布: zombie_empty_completion 10 (unknown 5 + cc4101-primary 3 + other 2) + NVAnth_IncompleteRead 2 (cc4101-primary).
dsv4p_nv 6h 82.0% (250/305) — NVCF function 74f02205 似自愈回升 (R2105 67.86% → +14pp), 非本域.

## 数据明细

### nv_requests 30min

| 维度 | 值 |
|------|-----|
| 总 SR | 138/140 = 98.6% (全错 2 = dsv4p ATE 1 default 路径 + glm5_2 zombie 1) |
| glm5_2_nv 30min SR | **75/76 = 98.7%** (cc4101-primary 40 + other 35 全 200; 1 错 unknown caller zombie) |
| 30min 错误 | all_tiers_exhausted 1 (dsv4p default 路径) + zombie_empty_completion 1 (glm5_2) |
| 30min glm5_2_nv ATE | **0** |
| 30min 真中断 | 0 (fallback 3 次全救回) |
| fallback 30min | **3** (cc4101 1 + opclaw4103 2), 全救回 |

### nv_requests 6h

| 维度 | 值 |
|------|-----|
| glm5_2_nv 6h SR | **842/854 = 98.60%** (持平 R2105 98.53% golden 略升) |
| glm5_2_nv 6h 错 12 | zombie 10 (unknown 5 + cc4101-primary 3 + other 2) + NVAnth_IncompleteRead 2 (cc4101-primary) |
| glm5_2_nv 6h ATE | **0** (无 all_tiers_exhausted) |
| glm5_2_nv 6h cap | **0** (无 stream_absolute_cap, 比 R2105 1cap 干净) |
| glm5_2_nv 6h 499 | **0** |
| dsv4p_nv 6h SR | 250/305 = 82.0% (R2105 67.86% → +14pp 自愈回升) |
| 6h fallback (cc4101) | 9 次 (背景波, 无扩散) |

## nv_gw 参数快照 (2026-07-22 本轮)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
StartedAt=2026-07-21T12:50:09Z  RestartCount=0  (连续第 25 轮 RC=0)
```

注: 容器 env 是 compose 层旧值 (HM2 域). HM1 peer R2221/R2220/R2219/R2218 全 HM1 域
(KEY_COOLDOWN 52→50→48→46 连续 -2s 交替 KEY→TIER→KEY), 非 openclaw2 域 (铁律只改 HM2 nv_gw, 不碰 HM1).
health: nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=glm5_2_nv, port=40006.

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **glm5_2_nv 6h 98.60%** (842/854) 持平 R2105 98.53% / R2104 98.65% golden 区连续多轮 (略升趋势).
2. **glm5_2_nv 30min 75/76 全 200, 0 ATE** — 稳定, 自愈保持.
3. **6h 0 ATE 0 cap 0 499** (12zombie+2IR 全良性背景波, 无 all_tiers_exhausted, 无 stream_absolute_cap) — 比 R2105 (1cap) 更干净.
4. **R2145/R2149 修复零退化**: caller cc4101-primary 40 + other 35 30min 全 glm5_2_nv 全 200.
5. **fallback 30min 3 次全救回 0 真中断**; env 无漂移 StartedAt 12:50:09Z 连续第 25 轮 RC=0.

6h 499=0: cc2 R2199 全局 settings env 改后 openclaw2 域健康持续 (R2149 锁定 model=glm5_2_nv 后零退化).
dsv4p_nv 6h 82.0% (R2105 67.86% → +14pp) — NVCF function 74f02205 似自愈回升, 非本域旋钮能修, 不影响 glm5_2_nv 路径. 持续观察回升趋势.

### 关注项

1. **glm5_2_nv 6h ~98.60%** — golden 持续区 (略升趋势), 无需关注
2. **glm5_2_nv 30min 0 ATE / 全清** — 自愈保持, 稳定
3. **真中断 0 (6h)** — R2105 6h 1 cap → 本轮 0 cap, 比 R2105 更干净; 30min 0 真中断
4. **6h 499=0** — cc2 R2199 全局 settings 改后 openclaw2 域健康持续, 持续观察
5. **dsv4p_nv NVCF function 似自愈 (67.86%→82.0% +14pp)** — 回升趋势, 影响 hermes 主 agent, 不影响 cc2/openclaw2. 持续观察是否持续回升.
6. **caller cc4101-primary+other 全 glm5_2_nv** — R2145/R2149 修复稳定零退化
7. **HM1 peer R2221 KEY_COOLDOWN 48→46** — 非 openclaw2 域 (铁律只改 HM2)
8. **STATE 无滞后本轮** — 上轮 R2105 已对齐主仓, 本轮 cat+git log 双确认一致

## 下一轮该做什么

1. **git pull**: 看 HM1 peer (R2221 KEY 48→46 后下一轮, 大概率交替 TIER/BUDGET), cc2/hermes2 新轮
2. **拉 30min + 6h + caller 维度**: 重点检验:
   - glm5_2_nv 6h SR 是否 > 97% 持续 (本轮 98.60% golden)?
   - glm5_2_nv 30min 是否保持 0 ATE (本轮 0)?
   - 真中断是否非扩散 (本轮 6h 0, 30min 0)?
   - caller cc4101-primary+other 是否全 glm5_2_nv 不退化 (R2145/R2149 修复)?
   - 6h 499 是否保持 0 (cc2 R2199 全局 settings 改后)?
   - dsv4p_nv NVCF function 是否持续自愈 (SR 回升趋势)?
3. **决策**:
   - glm5_2_nv > 96% + caller 全 glm5_2_nv + 30min 0 ATE + 499=0 → NOP 巡检
   - 若 R2145/R2149 修复退化 (caller 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env (cc2 R2199 改后是否被覆盖)
   - 若 dsv4p_nv 持续回升至 > 90% → 可标注 NVCF function 自愈确认
   - 若 ATE 抖动多窗口持续 → 重评估 (但归因上游非旋钮, 大概率仍 NOP)
4. 覆写 STATE
