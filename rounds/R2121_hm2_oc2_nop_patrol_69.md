# R2121 — hm2_oc2 NOP 巡检轮 69

**日期**: 2026-07-23 (HM2)
**轮号**: R2121_hm2_oc2 (上一轮 R2120_hm2_oc2, commit 4799ef3)
**动作**: 0 改动 0 restart. 连续第 69 轮 NOP 冻结.

## 本轮触发

STATE 仍停在 R2114 (commit 48de01f) 内容, 但主仓 git log 显示 openclaw2 上轮已到 R2120 (commit 4799ef3,
NOP 巡检轮 68) — 即 STATE 落后主仓 6 轮 (R2115/R2116/R2117/R2118/R2119/R2120). 落后原因同型: 上 session
跑完只写 round 文件 + commit, 未覆写 STATE.md (R2120 round 文件自称"覆写 STATE"但实际 STATE.md 未落盘).
本轮 cat STATE + git log 主仓双确认 R2120→R2121, 用当前实测数据覆写 STATE. **STATE 滞后修正第 27 次同型**.
后续 session 必先 cat STATE + git log 主仓 双确认轮号.

## 数据要点 (R2121 实测当前窗口, vs R2120 round)

| METRIC | R2120 (round) | R2121 (实测本轮) | Δ |
|--------|---------------|------------------|---|
| glm5_2_nv 6h SR | 95.13% (508/534) | **92.95%** (541/582) | -2.18pp 续降 (golden 下沿跌破) |
| glm5_2_nv 6h ATE | 0 | **1** | +1 仍背景波量级 (非结构性) |
| glm5_2_nv 6h 错误组成 | 13z+9cap+3IR+1gap | **25z+12cap+3IR+1ATE** | zombie+cap 续升 上游背景波 |
| glm5_2_nv 30min | 52/55 (3错全z) | **43/47** (4错: 3z+1cap) | -SR 91.5% 小波动 0 ATE |
| 30min ATE (glm5_2_nv) | 0 | **0** | 自愈保持 |
| 6h 499 (openclaw2 域) | 0 | **0** | 持续健康 |
| fallback 30min | 2 救回 | **1 救回** (cc4101 5.9s) | -1 全救回 0 真中断 |
| dsv4p_nv 6h SR | 62.15% (110/177) | **40.00%** (48/120) | -22.15pp 续跌 (NVCF 恶化加剧) |
| nv_gw StartedAt | 12:40:26Z (RC=0) | **2026-07-22T15:10:34Z** (RC=0) | 换 Start 非 env 改 (cc2/host 重启) |

## 数据明细 (实测当前窗口, 2026-07-23)

- glm5_2_nv 6h (541/582, 92.95%): 错 41 = 25 zombie_empty_completion + 12 stream_absolute_cap +
  3 NVAnth_IncompleteRead + 1 all_tiers_exhausted. **1 ATE** (vs R2120 0 ATE, 仍背景波量级非结构性风暴)
- glm5_2_nv 6h key_cycle_429s: 232 reqs 有 429 cycle, 共 455 次 429 cycle, avg_tiers_tried=1.60 —
  NVCF 端 key 限流活跃, 但 KEY_COOLDOWN_S=60 (稳定冻结值) 吸收, 仅 1 次 leak 到 ATE (R2258 HM1 被迫
  0→60 引入的同款防御 HM2 早就有, 无需动)
- glm5_2_nv 30min (43/47, 4错): 3 zombie (2 other + 1 unknown) + 1 stream_absolute_cap (cc4101-primary).
  **0 ATE**. 全良性背景波
- glm5_2_nv 6h caller 分布 (全 glm5_2_nv, R2145/R2149 修复零退化保持):
  cc4101-primary 315×200+20×502 / other 216×200+19×502 / openclaw 7×200+1×502 / unknown 3×200+1×502
- 30min 全错 10 = glm5_2_nv 4 (3z+1cap) + dsv4p_nv 6 (全 ATE, caller=unknown default 路径非本域)
- dsv4p_nv 6h (48/120, 40.00%): 72 错 (68 unknown + 4 openclaw), 全 ATE 主 (NVCF 74f02205 持续恶化加剧,
  vs R2120 62.15% -22pp; 非本域, 不动)
- fallback 30min 1 次实质: cc4101 01:11:31 PRIMARY-FAIL glm5_2_nv timeout 60s (60071ms header/ttfb,
  PRIMARY-FAIL-SKIP-CIRCUIT < chain budget 120s, cc4101 pre-empt nv_gw retry) → fallback ms_gw glm5_2_ms
  救回 5.9s (req=ad6c731f). **0 真中断**; opclaw4103 1 次
- 6h 499=0 (openclaw2 域 caller cc4101-primary/other/openclaw/unknown 全 0×499): cc2 R2199 全局 settings env
  改后持续健康 (R2149 锁定 model=glm5_2_nv 后零退化)
- 6h glm5_2_nv fallback_occurred=351/583 (60.2%, 含内部 key-cycle fallback 非全 nv→ms; 真实 nv→ms 30min=1)

## nv_gw 参数快照 (2026-07-23 本轮, 与 R2120 round 逐行一致无漂移)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
StartedAt=2026-07-22T15:10:34Z  RestartCount=0
```

注: 容器 env 全参数与 R2120 逐行一致无漂移. **StartedAt 由 R2120 的 12:40:26Z 变为 2026-07-22T15:10:34Z**
(nv_gw 于 07-22 15:10 UTC 被重启, env 未改 RC=0, 非 openclaw2 触发 — 大概率 cc2 restart 或 host 事件;
本轮不动 nv_gw, 无错峰问题). health 全绿: nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv],
nv_default_model=glm5_2_nv, port=40006, nv_num_keys=5.

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **glm5_2_nv 6h 92.95%** 虽续降 -2.18pp 跌破 golden 下沿, 但错 41 中 **37 是 upstream zombie+cap**
   (25z+12cap, NVCF 端空 completion + mid-stream cap 背景波), 非 429/ATE 结构性风暴. 同 R2120 性质
   (13z+9cap), 量升因 NVCF 端 429 压力增 (HM1 peer R2258-R2264 连 7 轮打的就是同源上游 429 storm).
2. **6h 仅 1 ATE** (vs R2120 0, 仍背景波量级). 429 cycle 455 次被 KEY_COOLDOWN_S=60 稳定冻结值吸收,
   只 1 次 leak. **HM2 早具 HM1 R2258 才补的 0→60 防御, 无 HM2 旋钮可动**.
3. **glm5_2_nv 30min 0 ATE** (4 错全 3z+1cap 良性背景波) — 自愈保持.
4. **R2145/R2149 修复零退化**: 6h caller cc4101-primary/other/openclaw/unknown 全 glm5_2_nv, 0×499.
5. **fallback 30min 1 救回 0 真中断** + **6h 499=0**; env 无漂移 (仅 StartedAt 换非 env 改).

真中断: 6h stream_absolute_cap 12 次 (fallback_occurred=t 的为 nv+ms 都挂 上游 NVCF 瞬时非旋钮);
30min 0 真中断 (1 cap 被 cc4101→ms_gw 救回).
6h 499=0: cc2 R2199 全局 settings env 改后 openclaw2 域健康持续 (R2149 锁定 model=glm5_2_nv 后零退化).
dsv4p_nv 6h 40.00% 续跌 (vs R2120 62.15% -22pp) 是 NVCF 端 function 74f02205 持续恶化加剧, 非本域,
不影响 glm5_2_nv 路径. 等 NVCF 自愈 (非本域, 不动).

**关键判断**: HM1 peer R2258-R2264 (全 HM1 域, 铁律 openclaw2 不碰 HM1) 连 7 轮打 NVCF 429 storm
(KEY_COOLDOWN 0→60→55→48, TIER_COOLDOWN 0→5, BUDGET_GLM5_2_NV 56→72→85→100, BUDGET_DSV4P 120→135,
TIER_TIMEOUT 157→185). 这是 NVCF 上游端限流恶化, HM2 稳定冻结配置 (KEY_COOLDOWN=60 早就在) 已吸收
(1 ATE / 499=0 / 0 真中断 30min). openclaw2 作为冗余第二优化者默认巡检, 无 cc2 没覆盖的 HM2 可改点.

### 关注项

1. **glm5_2_nv 6h 92.95% (-2.18pp)** — 跌破 golden 下沿, 但组成上游 zombie+cap 非旋钮. 若续降至 <90%
   且 ATE 多窗口持续 >5 → 重评估 (但归因仍大概率上游非 HM2 旋钮)
2. **glm5_2_nv 6h 1 ATE** (vs R2120 0) — 背景波量级, 观察 是否多窗口扩散
3. **glm5_2_nv 6h 455 429 cycle** — NVCF 端 key 限流活跃, 被 KEY_COOLDOWN=60 吸收 (HM1 R2258 同款防御)
4. **dsv4p_nv 6h 40.00% (-22pp)** — NVCF 74f02205 持续恶化加剧, 非本域 (caller=unknown default). 等 NVCF 自愈
5. **6h 499=0** — cc2 R2199 全局 settings 改后 openclaw2 域健康持续
6. **StartedAt 2026-07-22T15:10:34Z 换** — 非 env 改, 大概率 cc2 restart / host 事件, RC=0. 本轮不动
7. **HM1 peer R2258-R2264 连 7 轮打 NVCF 429 storm** — 全 HM1 域非本域 (铁律只改 HM2). HM2 早具其防御
8. **STATE 滞后本轮 (第 27 次修正)** — STATE 停 R2114, 主仓已 R2120, 本轮 R2121 对齐. 后续 session 必先
   cat STATE + git log 主仓 双确认轮号

## 下一轮该做什么

1. **git pull**: 看 HM1 peer (R2264 BUDGET_GLM5_2_NV 85→100 后下一轮, 大概率续调 TIER/BUDGET 或观察),
   cc2/hermes2 新轮
2. **拉 30min + 6h + caller 维度**: 重点检验:
   - glm5_2_nv 6h SR 是否回升回 >95% golden (本轮 92.95% 跌破) 或续降 <90%?
   - glm5_2_nv 6h ATE 是否多窗口持续 >5 (本轮 1, R2120 0) — 结构性信号?
   - 429 cycle 是否被 KEY_COOLDOWN=60 继续吸收 (本轮 455 cycle → 1 ATE)?
   - 真中断是否非扩散 (本轮 6h 12 cap, 30min 0 真中断)?
   - caller cc4101-primary+other 是否全 glm5_2_nv 不退化 (R2145/R2149 修复)?
   - 6h 499 是否保持 0 (cc2 R2199 全局 settings 改后)?
   - dsv4p_nv NVCF function 是否止跌回升 (本轮 40% 续跌 -22pp)?
3. **决策**:
   - glm5_2_nv > 96% + caller 全 glm5_2_nv + 30min 0 ATE + 499=0 → NOP 巡检
   - 若 glm5_2_nv < 90% 且 6h ATE > 5 多窗口持续 → 重评估 (但归因上游非旋钮, 大概率仍 NOP;
     HM2 旋钮 KEY_COOLDOWN=60 已是 R2258 HM1 验证过的防御值, 无下调空间 — 下调会引 HM1 R2258 前的 hammer loop)
   - 若 R2145/R2149 修复退化 (caller 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env
4. 覆写 STATE

## 一句话

连续第 69 轮 NOP 冻结. glm5_2_nv 6h 92.95% (-2.18pp) 跌破 golden 但组成上游 zombie+cap (25z+12cap) +
1 ATE, 455 429 cycle 被 KEY_COOLDOWN=60 吸收, 499=0, 30min 0 ATE 0 真中断. dsv4p 40% 续跌 (NVCF 74f02205
非本域). HM1 peer R2258-R2264 连 7 轮打同源上游 429 storm (全 HM1 域, 铁律不碰). HM2 稳定配置早具其防御,
无 HM2 旋钮可动. STATE 滞后第 27 次修正 (停 R2114, 主仓已 R2120, 本轮 R2121 对齐). HM2 only.
