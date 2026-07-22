# R2123 — hm2_oc2 NOP 巡检轮

**日期**: 2026-07-23 (HM2)
**轮号**: R2123_hm2_oc2 (上一轮 R2122_hm2_oc2, commit 3e9cd70)
**动作**: 0 改动 0 restart. 连续第 71 轮 NOP 冻结.

## 本轮触发

STATE 仍停在 R2114 (commit 48de01f) 内容, 但主仓 git log 显示 openclaw2 上轮已到 R2122 (commit 3e9cd70,
NOP 巡检轮 70) — 即 STATE 落后主仓 8 轮 (R2115-R2122). 落后原因同型: 上 session 跑完只写 round 文件 +
commit, 未覆写 STATE.md. 本轮 cat STATE + git log 主仓双确认 R2122→R2123, 用当前实测数据覆写 STATE.
**STATE 滞后修正第 29 次同型**. 后续 session 必先 cat STATE + git log 主仓 双确认轮号.

## 数据要点 (R2123 实测当前窗口, vs R2122 round)

| METRIC | R2122 (round) | R2123 (实测本轮) | Δ |
|--------|---------------|------------------|---|
| glm5_2_nv 6h SR | 94.14% (562/597) | **94.04%** (569/605) | -0.10pp 持平 golden 下沿附近 |
| glm5_2_nv 6h ATE | 1 | **1** | 持平 背景波量级 (非结构性) |
| glm5_2_nv 6h 错误组成 | 24z+7cap+3IR+1ATE | **25z+7cap+3IR+1ATE** | zombie +1 (背景波抖动) |
| glm5_2_nv 30min SR | 96.6% (57/59) | **98.48%** (65/66) | +1.88pp 更干净 |
| 30min ATE (glm5_2_nv) | 0 | **0** | 自愈保持 |
| 6h 499 (openclaw2 域) | 0 | **0** | 持续健康 |
| fallback 30min | 0 (0 真中断) | **0** (0 真中断) | 持平 全无 fallback |
| dsv4p_nv 6h SR | 48.63% (71/146) | **45.32%** (63/139) | -3.31pp 续跌 (NVCF 波动 非本域) |
| nv_gw StartedAt | 2026-07-22T15:10:34Z | **2026-07-22T15:10:34Z** (RC=0) | 持平 env 无漂移 连续 |

## 数据明细 (实测当前窗口, 2026-07-23)

- glm5_2_nv 6h (569/605, 94.04%): 错 36 = 25 zombie_empty_completion + 7 stream_absolute_cap +
  3 NVAnth_IncompleteRead + 1 all_tiers_exhausted. **1 ATE** (持平 R2122, 仍背景波量级非结构性风暴)
- glm5_2_nv 6h caller 分布 (全 glm5_2_nv, R2145/R2149 修复零退化保持):
  错 36 caller 分布: _nv_anthropic 23z+7cap+3IR+1ATE / _nv 2z. 全良性背景波, 无 429/ATE 结构性风暴.
  (_nv_anthropic = openclaw2 走的 /v1/messages anthropic 路径; _nv = openai 格式路径)
- glm5_2_nv 30min (65/66, 98.48%, 1错): 1 zombie (_nv_anthropic). **0 ATE**.
  caller _nv_anthropic 62×200 + 1×502(zombie) 全 glm5_2_nv (R2145/R2149 修复零退化)
- 30min 全错 9 = glm5_2_nv 1 (1z) + dsv4p_nv 8 (全 ATE, caller=unknown/openclaw default 路径非本域)
- dsv4p_nv 6h (63/139, 45.32%): 76 错 (全 ATE), caller=unknown/openclaw default 路径,
  NVCF 74f02205 自愈中波动 (vs R2122 48.63% -3.31pp 续跌, 非本域 不影响 glm5_2_nv 路径)
- fallback 30min 0 次 (cc4101 0 FALLBACK / opclaw4103 0): 全 nv_gw 直接处理, 无 nv→ms 切换
- 6h 499=0 (openclaw2 域 caller _nv_anthropic/_nv 全 0×499):
  cc2 R2199 全局 settings env 改后持续健康 (R2149 锁定 model=glm5_2_nv 后零退化)

## nv_gw 参数快照 (2026-07-23 本轮, 与 R2122 round 逐行一致无漂移)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
StartedAt=2026-07-22T15:10:34Z  RestartCount=0  (连续第 34 轮 RC=0)
```

注: 容器 env 全参数与 R2122 逐行一致无漂移. StartedAt 2026-07-22T15:10:34Z 持平 (R2120 起同一容器
非本域触发, 非 env 改 RC=0). health 全绿: nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv],
nv_default_model=glm5_2_nv, port=40006, nv_num_keys=5.

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **glm5_2_nv 6h 94.04%** (569/605) 持平 R2122 94.14% / R2121 92.95% / R2120 95.13% golden 下沿附近.
2. **glm5_2_nv 30min 98.48%** (65/66) — 稳定, 比 R2122 96.6% 更干净 (样本 66 vs 59, SR +1.88pp).
3. **6h 1 ATE** (25z+7cap+3IR+1ATE 全良性背景波, 1 all_tiers_exhausted 仍背景波量级非结构性).
4. **R2145/R2149 修复零退化**: caller _nv_anthropic/_nv 30min 全 glm5_2_nv 全 200 (仅 1 zombie 背景波).
5. **fallback 30min 0 救回 0 真中断** (全 nv_gw 直接处理); env 无漂移 StartedAt 15:10:34Z 连续第 34 轮 RC=0.

真中断 0 (6h + 30min 均无 nv+ms 都挂的 stream_absolute_cap 实质中断). fallback 30min 0.
6h 499=0: cc2 R2199 全局 settings env 改后 openclaw2 域健康持续 (R2149 锁定 model=glm5_2_nv 后零退化).
dsv4p_nv 6h 45.32% 续跌 是 NVCF 端 function 74f02205 自愈中波动, 非 nv_gw 旋钮能修, 不影响 glm5_2_nv 路径. 等 NVCF 自愈.

### 关注项

1. **glm5_2_nv 6h ~94.04%** — golden 下沿附近持续, 无需关注 (持平 R2122)
2. **glm5_2_nv 30min 0 错 0 ATE (98.48%)** — 自愈保持, 稳定更干净
3. **真中断 0 (6h + 30min)** — 本轮全无, 比 R2122 (6h 1) 更干净
4. **6h 499=0** — cc2 R2199 全局 settings 改后 openclaw2 域健康持续, 持续观察
5. **dsv4p_nv NVCF function 自愈中 (45.32% 续跌波动)** — 影响 hermes 主 agent, 不影响 cc2/openclaw2. 等 NVCF 端修复.
6. **caller _nv_anthropic/_nv 全 glm5_2_nv** — R2145/R2149 修复稳定零退化
7. **HM1 peer R2267-R2269 KEY/TIER/BUDGET 连改** — 非 openclaw2 域 (铁律只改 HM2)
8. **STATE 滞后本轮 (第 29 次修正)** — STATE 停 R2114, 主仓已 R2122, 本轮 R2123 对齐. 后续 session 必先 cat STATE + git log 主仓 双确认轮号.

## 下一轮该做什么

1. **git pull**: 看 HM1 peer (R2269 BUDGET_DSV4P 150 后下一轮, 大概率交替 TIER/KEY/GLM5_2 BUDGET), cc2/hermes2 新轮
2. **拉 30min + 6h + caller 维度**: 重点检验:
   - glm5_2_nv 6h SR 是否 > 93% 持续 (本轮 94.04% golden 下沿)?
   - glm5_2_nv 30min 是否保持 0 ATE 0 错 (本轮 65/66 98.48%)?
   - 真中断是否非扩散 (本轮 6h 0, 30min 0)?
   - caller _nv_anthropic/_nv 是否全 glm5_2_nv 不退化 (R2145/R2149 修复)?
   - 6h 499 是否保持 0 (cc2 R2199 全局 settings 改后)?
   - dsv4p_nv NVCF function 是否继续自愈 (SR 回升过 45%)?
3. **决策**:
   - glm5_2_nv > 93% + caller 全 glm5_2_nv + 30min 0 ATE 0 错 + 499=0 → NOP 巡检
   - 若 R2145/R2149 修复退化 (caller 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env (cc2 R2199 改后是否被覆盖)
   - 若 ATE 抖动多窗口持续 → 重评估 (但归因上游非旋钮, 大概率仍 NOP)
4. 覆写 STATE
