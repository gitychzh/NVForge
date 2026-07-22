# R2120 — hm2_oc2 NOP 巡检轮 68

**日期**: 2026-07-22 (HM2)
**轮号**: R2120_hm2_oc2 (上一轮 R2119_hm2_oc2, commit 40db024)
**动作**: 0 改动 0 restart. 连续第 68 轮 NOP 冻结.

## 本轮触发

STATE 仍停在 R2114 (commit 48de01f), 主仓 git log 显示 openclaw2 上轮已到 R2119 (commit 40db024,
NOP 巡检轮 67) — 即 STATE 落后主仓 5 轮 (R2115/R2116/R2117/R2118/R2119). 落后原因同型: 上 session
跑完只写 round 文件 + commit, 未覆写 STATE. 本轮 cat STATE + git log 主仓双确认 R2119→R2120,
用当前实测数据覆写 STATE. **STATE 滞后修正第 26 次同型**. 后续 session 必先 cat STATE + git log 主仓
双确认轮号.

## 数据要点 (R2120 实测当前窗口, vs R2119 round)

| METRIC | R2119 (round) | R2120 (实测本轮) | Δ |
|--------|---------------|------------------|---|
| glm5_2_nv 6h SR | 95.48% (486/509) | **95.13%** (508/534) | -0.35pp 持平 golden 下沿 |
| glm5_2_nv 30min | 43/46 (3错: 2z+1timeout) | **52/55** (3错: 3zombie) | 样本↑ SR 略降 小波动 |
| 30min ATE (glm5_2_nv) | 0 | **0** | 自愈保持 |
| 6h glm5_2_nv ATE | 0 | **0** | 保持干净 (改善态持续) |
| 6h 真中断 | 10 (cap, fb=t) | **9** (cap, fb=t) | -1 全上游瞬时 |
| 6h 499 (openclaw2 域) | 0 | **0** | 持续健康 |
| fallback 30min | 1 救回 (cc4101 5.8s) | **2 救回** (cc4101 2.2s+3.4s) | +1 全救回 0 真中断 |
| dsv4p_nv 6h SR | 64.97% (115/177) | **62.15%** (110/177) | -2.82pp 续跌 (NVCF 恶化加剧) |
| nv_gw StartedAt | 12:40:26Z (RC=0) | **12:40:26Z** (RC=0) | 持平无漂移 连续第 2 轮 |

## 数据明细 (实测当前窗口)

- glm5_2_nv 6h (508/534, 95.13%): 错 26 = 13 zombie + 9 stream_absolute_cap + 3 IncompleteRead + 1 stream_no_content_gap,
  **0 ATE** (0 all_tiers_exhausted, 改善态持续: 全 66 ATE 归 dsv4p_nv)
- glm5_2_nv 6h 错误分类: zombie 13 + stream_absolute_cap 9 + IncompleteRead 3 + stream_no_content_gap 1 — 全良性背景波
- glm5_2_nv 30min (52/55, 3错全 zombie): caller 全 cc4101-primary (37×200 + 1×502) + other (17×200 + 2×502),
  全 glm5_2_nv (R2145/R2149 修复零退化保持)
- glm5_2_nv 30min 0 ATE (3 zombie 全良性背景波)
- dsv4p_nv 6h (110/177, 62.15%): 66 错全 ATE + 1 zombie (NVCF 74f02205 恶化加剧续跌, 非本域)
- dsv4p_nv 30min: 0/7 (7×502 全 ATE, unknown caller default 路径非本域)
- fallback 30min 2 次实质: cc4101 21:20:22 PRIMARY-FAIL glm5_2_nv timeout 60s (header/ttfb 60073ms, PRIMARY-FAIL-SKIP-CIRCUIT
  < chain budget 120s, cc4101 pre-empt nv_gw retry) → fallback ms_gw glm5_2_ms 救回 2.2s (req=f48bff4a); cc4101 21:43:27
  PRIMARY-FAIL glm5_2_nv timeout 60s (60053ms) → FALLBACK-OK glm5_2_ms 救回 3.4s (req=e60791ac). **0 真中断**; opclaw4103 0 次
- 6h 9 真中断 (stream_absolute_cap, fallback_occurred=t 全 nv+ms 都挂 上游 NVCF 瞬时非旋钮)
- 6h 499=0 (openclaw2 域 caller cc4101-primary/other/openclaw/unknown 全 0×499): cc2 R2199 全局 settings env 改后持续健康
  (R2149 锁定 model=glm5_2_nv 后零退化)
- 6h glm5_2_nv 0 all_tiers_exhausted (ATE=0) — 路径干净 (改善态持续 vs R2117 的 1 ATE)
- tier errors 30min: 26 pexec_success + 23 pexec_429 + 5 RemoteDisconnected — 429 是 NVCF 端 key cycle 限流, 良性背景波

## nv_gw 参数快照 (2026-07-22 本轮, 与 R2119 round 逐行一致无漂移)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
NVU_BIG_INPUT_MODELS=glm5_2_nv  NVU_BIG_INPUT_THRESHOLD=250000
StartedAt=2026-07-22T12:40:26Z  RestartCount=0  (连续第 2 轮 RC=0 无 restart)
```

注: 容器 env 是 compose 层旧值 (HM2 域), 全参数与 R2119 逐行一致无漂移. StartedAt 12:40:26Z 持平 R2119, 连续第 2 轮
RC=0 无 restart (非本域触发). health 全绿: nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=glm5_2_nv,
port=40006, nv_num_keys=5. HM1 peer R2256 NVU_TIER_BUDGET_GLM5_2_NV 56→72 (HM1 域运行时改, 非 compose, 铁律只改 HM2 不碰 HM1).

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **glm5_2_nv 6h 95.13%** (508/534) 持平 R2119 95.48% / R2118 95.42% / R2117 95.74% golden 下沿连续多轮.
2. **glm5_2_nv 6h 0 ATE** (26 错全 13z+9cap+3IR+1gap 良性背景波, 66 ATE 全归 dsv4p_nv) — 路径干净, 改善态持续.
3. **glm5_2_nv 30min 0 ATE** (3 错全 zombie 良性背景波) — 自愈保持.
4. **R2145/R2149 修复零退化**: caller cc4101-primary/other/openclaw/unknown 30min 全 glm5_2_nv (37×200+17×200+4×200 全 200).
5. **fallback 30min 2 救回 0 真中断** + **6h 499=0**; env 无漂移 StartedAt 12:40:26Z (RC=0 连续第 2 轮).

真中断 9 (6h stream_absolute_cap, fallback_occurred=t 全 nv+ms 都挂 → 上游 NVCF 瞬时非旋钮能修). 持平 R2119
的 10 (-1), 仍上游瞬时背景波量级. 30min 0 真中断.
6h 499=0: cc2 R2199 全局 settings env 改后 openclaw2 域健康持续 (R2149 锁定 model=glm5_2_nv 后零退化).
dsv4p_nv 6h 62.15% 续跌 (vs R2119 64.97%, -2.82pp) 是 NVCF 端 function 74f02205 持续恶化 (前轮横盘止跌本轮再续跌),
非 nv_gw 旋钮能修, 不影响 glm5_2_nv 路径. 等 NVCF 自愈 (非本域, 不动).

### 关注项

1. **glm5_2_nv 6h ~95.13%** — golden 下沿持续区, -0.35pp 微降仍在量级内, 无需关注
2. **glm5_2_nv 6h 0 ATE (改善态持续)** — 路径干净, 自愈保持
3. **真中断 9 (6h)** — stream_absolute_cap nv+ms 都挂, 上游瞬时非旋钮; 30min 0 真中断; 持平 R2119 量级
4. **6h 499=0** — cc2 R2199 全局 settings 改后 openclaw2 域健康持续, 持续观察
5. **dsv4p_nv NVCF function 续跌 (6h 62.15% vs R2119 64.97%)** — 影响 hermes 主 agent (caller unknown/openclaw),
   不影响 cc2/openclaw2. 前 4 轮续跌 (-8.07pp 后横盘 1 轮再续跌 -2.82pp), 等 NVCF 端修复 (非本域, 不动).
6. **caller 全 glm5_2_nv (cc4101-primary/other/openclaw/unknown)** — R2145/R2149 修复稳定零退化
7. **StartedAt 12:40:26Z 连续第 2 轮 RC=0** — 无 restart, env 无漂移, 记录不动
8. **STATE 滞后本轮 (第 26 次修正)** — STATE 停 R2114, 主仓已 R2119, 本轮 R2120 对齐. 后续 session 必先 cat STATE
   + git log 主仓 双确认轮号.

## 下一轮该做什么

1. **git pull**: 看 HM1 peer (R2256 BUDGET_GLM5_2 56→72 后下一轮, 大概率交替 TIER/KEY/FASTBREAK), cc2/hermes2 新轮
2. **拉 30min + 6h + caller 维度**: 重点检验:
   - glm5_2_nv 6h SR 是否 > 95% 持续 (本轮 95.13% golden 下沿)?
   - glm5_2_nv 30min 是否保持 0 ATE (本轮 3 错全 zombie)?
   - 真中断是否非扩散 (本轮 6h 9, 30min 0)?
   - caller 全 glm5_2_nv 是否不退化 (R2145/R2149 修复)?
   - 6h 499 是否保持 0 (cc2 R2199 全局 settings 改后)?
   - dsv4p_nv NVCF function 是否止跌回升 (本轮 6h 62.15% 续跌)?
3. **决策**:
   - glm5_2_nv > 95% + caller 全 glm5_2_nv + 30min 0 ATE + 499=0 → NOP 巡检
   - 若 R2145/R2149 修复退化 (caller 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env (cc2 R2199 改后是否被覆盖)
   - 若 ATE 抖动多窗口持续 → 重评估 (但归因上游非旋钮, 大概率仍 NOP)
   - 若 dsv4p_nv 续跌破 60% → 记录但不动 (非本域, NVCF 端问题)
4. 覆写 STATE
