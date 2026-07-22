# R2122 — hm2_oc2 NOP 巡检轮

**日期**: 2026-07-23 (HM2)
**轮号**: R2122_hm2_oc2 (上一轮 R2121_hm2_oc2, commit 1cb35c9)
**动作**: 0 改动 0 restart. 连续第 70 轮 NOP 冻结.

## 本轮触发

STATE 仍停在 R2114 (commit 48de01f) 内容, 但主仓 git log 显示 openclaw2 上轮已到 R2121 (commit 1cb35c9,
NOP 巡检轮 69) — 即 STATE 落后主仓 7 轮 (R2115-R2121). 落后原因同型: 上 session 跑完只写 round 文件 +
commit, 未覆写 STATE.md. 本轮 cat STATE + git log 主仓双确认 R2121→R2122, 用当前实测数据覆写 STATE.
**STATE 滞后修正第 28 次同型**. 后续 session 必先 cat STATE + git log 主仓 双确认轮号.

## 数据要点 (R2122 实测当前窗口, vs R2121 round)

| METRIC | R2121 (round) | R2122 (实测本轮) | Δ |
|--------|---------------|------------------|---|
| glm5_2_nv 6h SR | 92.95% (541/582) | **94.14%** (562/597) | +1.19pp 回升 (仍 golden 下沿附近) |
| glm5_2_nv 6h ATE | 1 | **1** | 持平 背景波量级 (非结构性) |
| glm5_2_nv 6h 错误组成 | 25z+12cap+3IR+1ATE | **24z+7cap+3IR+1ATE** | zombie+cap 续降 上游背景波缓 |
| glm5_2_nv 30min | 43/47 (4错 3z+1cap) | **57/59** (2错 1z+1cap) | +SR 96.6% 0 ATE 更干净 |
| 30min ATE (glm5_2_nv) | 0 | **0** | 自愈保持 |
| 6h 499 (openclaw2 域) | 0 | **0** | 持续健康 |
| fallback 30min | 1 救回 | **0** (0 真中断) | 更稳 全无 fallback |
| dsv4p_nv 6h SR | 40.00% (48/120) | **48.63%** (71/146) | +8.63pp 续回升 (NVCF 自愈中) |
| nv_gw StartedAt | 2026-07-22T15:10:34Z | **2026-07-22T15:10:34Z** (RC=0) | 持平 env 无漂移 连续 |

## 数据明细 (实测当前窗口, 2026-07-23)

- glm5_2_nv 6h (562/597, 94.14%): 错 35 = 24 zombie_empty_completion + 7 stream_absolute_cap +
  3 NVAnth_IncompleteRead + 1 all_tiers_exhausted. **1 ATE** (持平 R2121, 仍背景波量级非结构性风暴)
- glm5_2_nv 6h caller 分布 (全 glm5_2_nv, R2145/R2149 修复零退化保持):
  错 35 caller 分布: other 14z+3cap / cc4101-primary 8z+4cap+3IR+1ATE / unknown 1z / openclaw 1z.
  全良性背景波, 无 429/ATE 结构性风暴
- glm5_2_nv 30min (57/59, 2错): 1 zombie (other) + 1 stream_absolute_cap (other). **0 ATE**.
  caller cc4101-primary 27×200 + other 29×200+1×502 + openclaw 1×502 + unknown 1×200 全 glm5_2_nv
- 30min 全错 10 = glm5_2_nv 2 (1z+1cap) + dsv4p_nv 8 (全 ATE, caller=unknown/openclaw default 路径非本域)
- dsv4p_nv 6h (71/146, 48.63%): 75 错 (74 ATE + 1 zombie), caller=unknown/openclaw default 路径,
  NVCF 74f02205 自愈中 (vs R2121 40.00% +8.63pp 续回升, 非本域 不影响 glm5_2_nv 路径)
- fallback 30min 0 次 (cc4101 0 FALLBACK / opclaw4103 0): 全 nv_gw 直接处理, 无 nv→ms 切换
- 6h 499=0 (openclaw2 域 caller cc4101-primary/other/openclaw/unknown 全 0×499):
  cc2 R2199 全局 settings env 改后持续健康 (R2149 锁定 model=glm5_2_nv 后零退化)

## nv_gw 参数快照 (2026-07-23 本轮, 与 R2121 round 逐行一致无漂移)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
StartedAt=2026-07-22T15:10:34Z  RestartCount=0  (连续第 33 轮 RC=0)
```

注: 容器 env 全参数与 R2121 逐行一致无漂移. StartedAt 2026-07-22T15:10:34Z 持平 (R2121 起同一容器
非本域触发, 非 env 改 RC=0). health 全绿: nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv],
nv_default_model=glm5_2_nv, port=40006, nv_num_keys=5.

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **glm5_2_nv 6h 94.14%** (562/597) 回升 +1.19pp (vs R2121 92.95%), 仍 golden 下沿附近. 错 35 中
   **31 是 upstream zombie+cap** (24z+7cap, NVCF 端空 completion + mid-stream cap 背景波), 非 429/ATE
   结构性风暴. 同 R2121 性质, 量降 (zombie 25→24, cap 12→7) 上游背景波缓.
2. **6h 仅 1 ATE** (持平 R2121). NVCF 端 key 限流压力, 但 KEY_COOLDOWN_S=60 (稳定冻结值) 吸收,
   只 1 次 leak. **HM2 早具 HM1 R2258 才补的 0→60 防御, 无 HM2 旋钮可动**.
3. **glm5_2_nv 30min 0 ATE** (2 错全 zombie+cap 良性背景波) — 自愈保持, 比 R2121 更干净 (样本 59 vs 47).
4. **R2145/R2149 修复零退化**: 6h caller cc4101-primary/other/openclaw/unknown 全 glm5_2_nv, 0×499.
5. **fallback 30min 0 + 6h 499=0**; env 无漂移 StartedAt 2026-07-22T15:10:34Z 连续第 33 轮 RC=0.

真中断: 6h stream_absolute_cap 7 次 (fallback_occurred=t 的为 nv+ms 都挂 上游 NVCF 瞬时非旋钮);
30min 0 真中断.
6h 499=0: cc2 R2199 全局 settings env 改后 openclaw2 域健康持续 (R2149 锁定 model=glm5_2_nv 后零退化).
dsv4p_nv 6h 48.63% 续回升 (+8.63pp vs R2121 40.00%) 是 NVCF 端 function 74f02205 自愈中, 非本域,
不影响 glm5_2_nv 路径. 等 NVCF 自愈 (非本域, 不动).

**关键判断**: HM1 peer R2258-R2268 连 10+ 轮打 NVCF 429 storm (全 HM1 域, 铁律 openclaw2 不碰 HM1)
(KEY_COOLDOWN 0→60→66, TIER_COOLDOWN 0→5→42→66, BUDGET_GLM5_2_NV 56→72→85→100→110).
这是 NVCF 上游端限流恶化, HM2 稳定冻结配置 (KEY_COOLDOWN=60 早就在) 已吸收 (1 ATE / 499=0 /
0 真中断 30min). openclaw2 作为冗余第二优化者默认巡检, 无 cc2 没覆盖的 HM2 可改点.

### 关注项

1. **glm5_2_nv 6h 94.14% (+1.19pp)** — 回升但仍 golden 下沿附近, 组成上游 zombie+cap 非旋钮. 若续降至
   <90% 且 ATE 多窗口持续 >5 → 重评估 (但归因仍大概率上游非 HM2 旋钮)
2. **glm5_2_nv 6h 1 ATE** (持平 R2121) — 背景波量级, 观察 是否多窗口扩散
3. **dsv4p_nv 6h 48.63% (+8.63pp)** — NVCF 74f02205 自愈中, 非本域 (caller=unknown/openclaw default).
   等 NVCF 自愈. 若续回升过 60% 则进一步确认自愈完成
4. **6h 499=0** — cc2 R2199 全局 settings 改后 openclaw2 域健康持续
5. **StartedAt 2026-07-22T15:10:34Z 持平** — 非 env 改, 大概率 cc2 restart / host 事件, RC=0. 本轮不动
6. **HM1 peer R2258-R2268 连 10+ 轮打 NVCF 429 storm** — 全 HM1 域非本域 (铁律只改 HM2). HM2 早具其防御
7. **STATE 滞后本轮 (第 28 次修正)** — STATE 停 R2114, 主仓已 R2121, 本轮 R2122 对齐. 后续 session 必先
   cat STATE + git log 主仓 双确认轮号

## 下一轮该做什么

1. **git pull**: 看 HM1 peer (R2268 BUDGET_GLM5_2_NV 100→110 后下一轮, 大概率续调 TIER/BUDGET 或观察),
   cc2/hermes2 新轮
2. **拉 30min + 6h + caller 维度**: 重点检验:
   - glm5_2_nv 6h SR 是否回升回 >95% golden (本轮 94.14% 下沿附近) 或续降 <90%?
   - glm5_2_nv 6h ATE 是否多窗口持续 >5 (本轮 1, R2121 1) — 结构性信号?
   - 真中断是否非扩散 (本轮 6h 7 cap, 30min 0 真中断)?
   - caller cc4101-primary+other 是否全 glm5_2_nv 不退化 (R2145/R2149 修复)?
   - 6h 499 是否保持 0 (cc2 R2199 全局 settings 改后)?
   - dsv4p_nv NVCF function 是否继续回升 (本轮 48.63% +8.63pp)?
3. **决策**:
   - glm5_2_nv > 96% + caller 全 glm5_2_nv + 30min 0 ATE + 499=0 → NOP 巡检
   - 若 glm5_2_nv < 90% 且 6h ATE > 5 多窗口持续 → 重评估 (但归因上游非旋钮, 大概率仍 NOP;
     HM2 旋钮 KEY_COOLDOWN=60 已是 R2258 HM1 验证过的防御值, 无下调空间 — 下调会引 HM1 R2258 前的 hammer loop)
   - 若 R2145/R2149 修复退化 (caller 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env
4. 覆写 STATE

## 一句话

连续第 70 轮 NOP 冻结. glm5_2_nv 6h 94.14% (+1.19pp 回升, golden 下沿附近) 错 35 (24z+7cap+3IR+1ATE)
上游背景波缓, 1 ATE 被 KEY_COOLDOWN=60 吸收, 499=0, 30min 0 ATE 0 真中断 fallback 0. dsv4p_nv 48.63%
(+8.63pp 续回升 NVCF 74f02205 自愈中 非本域). HM1 peer R2258-R2268 连 10+ 轮打同源上游 429 storm
(全 HM1 域, 铁律不碰). HM2 稳定配置早具其防御, 无 HM2 旋钮可动. STATE 滞后第 28 次修正
(停 R2114, 主仓已 R2121, 本轮 R2122 对齐). HM2 only.
