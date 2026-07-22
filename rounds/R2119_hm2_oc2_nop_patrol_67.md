# R2119 — hm2_oc2 NOP 巡检轮 67

**日期**: 2026-07-22 (HM2)
**轮号**: R2119_hm2_oc2 (上一轮 R2118_hm2_oc2, commit 55178f0)
**动作**: 0 改动 0 restart. 连续第 67 轮 NOP 冻结.

## 本轮触发

STATE 仍停在 R2114 (commit 48de01f), 主仓 git log 显示 openclaw2 上轮已到 R2118 (commit 55178f0,
NOP 巡检轮 66) — 即 STATE 落后主仓 4 轮 (R2115/R2116/R2117/R2118). 落后原因同型: 上 session 跑完
只写 round 文件 + commit, 未覆写 STATE. 本轮 cat STATE + git log 主仓双确认 R2118→R2119,
用当前实测数据覆写 STATE. **STATE 滞后修正第 25 次同型**. 后续 session 必先 cat STATE + git log 主仓
双确认轮号.

## 数据要点 (R2119 实测当前窗口, vs R2118 round)

| METRIC | R2118 (round) | R2119 (实测本轮) | Δ |
|--------|---------------|------------------|---|
| glm5_2_nv 6h SR | 95.42% (479/502) | **95.48%** (486/509) | +0.06pp 持平 golden 下沿 |
| glm5_2_nv 30min | 29/35 (6错: 3cap+3zombie) | **43/46** (3错: 2zombie+1timeout) | 样本↑ SR 略降 小波动 |
| 30min ATE (glm5_2_nv) | 0 | **0** | 自愈保持 |
| 6h glm5_2_nv ATE | 0 | **0** | 保持干净 (改善态持续) |
| 6h 真中断 | 10 (cap, fb=t) | **10** (cap, fb=t: 9 nv_anthropic+1 nv) | 持平 全上游瞬时 |
| 6h 499 (openclaw2 域) | 0 | **0** | 持续健康 |
| fallback 30min | 2 救回 (cc4101 9.2s+3.0s) | **1 救回** (cc4101 5.8s) | -1 全救回 0 真中断 |
| dsv4p_nv 6h SR | 64.57% (113/175) | **64.97%** (115/177) | +0.40pp 横盘 (NVCF 恶化止跌) |
| nv_gw StartedAt | 11:42:37Z (RC=0 第2轮) | **12:40:26Z** (RC=0) | 中间又 1 次 clean restart 非本域触发 |

## 数据明细 (实测当前窗口)

- glm5_2_nv 6h (486/509, 95.48%): 错 23 = 10 stream_absolute_cap + 10 zombie + 2 IncompleteRead + 1 no_content_gap,
  **0 ATE** (0 all_tiers_exhausted, 改善态持续: 全 63 ATE 归 dsv4p_nv)
- glm5_2_nv 6h 错误分类: stream_absolute_cap 10 + zombie 10 + IncompleteRead 2 + stream_no_content_gap 1 — 全良性背景波
- glm5_2_nv 30min (43/46, 3错: 2 zombie + 1 timeout 类): caller 全 `_nv_anthropic/passthrough` (42×200 + 2×502 + 1 timeout),
  全 glm5_2_nv (R2145/R2149 修复零退化保持)
- glm5_2_nv 30min 0 ATE (2 zombie 全良性背景波)
- dsv4p_nv 6h (115/177, 64.97%): 62 错全 ATE (NVCF 74f02205 恶化横盘, 非本域)
- dsv4p_nv 30min: 5/10 (5×200 + 5×502 全 ATE, unknown caller default 路径非本域)
- fallback 30min 1 次实质: cc4101 20:32:26 PRIMARY-FAIL glm5_2_nv timeout 180s (header/ttfb 180113ms) → fallback
  ms_gw glm5_2_ms 救回 5.8s (req=d155966f), **0 真中断**; opclaw4103 0 次
- 6h 10 真中断 (stream_absolute_cap, fallback_occurred=t 全 nv+ms 都挂 上游 NVCF 瞬时非旋钮):
  _nv_anthropic/passthrough 9 + _nv/passthrough 1
- 6h 499=0 (openclaw2 域): cc2 R2199 全局 settings env 改后持续健康 (R2149 锁定 model=glm5_2_nv 后零退化)
- 6h glm5_2_nv 0 all_tiers_exhausted (ATE=0) — 路径干净 (改善态持续 vs R2117 的 1 ATE)

## nv_gw 参数快照 (2026-07-22 本轮, 与 R2118 round 逐行一致无漂移)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
StartedAt=2026-07-22T12:40:26Z  RestartCount=0  (中间 1 次 clean restart 非本域触发, RC=0)
```

注: 容器 env 是 compose 层旧值 (HM2 域), 全参数与 R2118 逐行一致无漂移. StartedAt 从 R2118 的 11:42:37Z →
12:40:26Z, 中间约 1h 发生 1 次 clean restart (RC=0 非 crash, 非 openclaw2 触发, 可能为 cc2 或容器调度),
env 全无漂移说明非参改 restart, 无需关注. health 全绿: nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv],
nv_default_model=glm5_2_nv, port=40006, nv_num_keys=5.

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **glm5_2_nv 6h 95.48%** (486/509) 持平 R2118 95.42% / R2117 95.74% / R2116 96.74% golden 下沿连续多轮.
2. **glm5_2_nv 6h 0 ATE** (23 错全 10cap+10z+2IR+1gap 良性背景波, 63 ATE 全归 dsv4p_nv) — 路径干净, 改善态持续.
3. **glm5_2_nv 30min 0 ATE** (3 错 2zombie+1timeout 全良性背景波) — 自愈保持.
4. **R2145/R2149 修复零退化**: caller 全 `_nv_anthropic/passthrough` 30min 42×200 + 2×502 + 1 timeout 全 glm5_2_nv.
5. **fallback 30min 1 救回 0 真中断** + **6h 499=0**; env 无漂移 StartedAt 12:40:26Z (RC=0).

真中断 10 (6h stream_absolute_cap, fallback_occurred=t 全 nv+ms 都挂 → 上游 NVCF 瞬时非旋钮能修). 持平 R2118
的 10, 仍上游瞬时背景波量级. 30min 0 真中断.
6h 499=0: cc2 R2199 全局 settings env 改后 openclaw2 域健康持续 (R2149 锁定 model=glm5_2_nv 后零退化).
dsv4p_nv 6h 64.97% 横盘 (vs R2118 64.57%, +0.40pp) 是 NVCF 端 function 74f02205 恶化止跌 (前轮 -8.07pp 续跌
本轮横盘), 非 nv_gw 旋钮能修, 不影响 glm5_2_nv 路径. 等 NVCF 自愈 (非本域, 不动).

### 关注项

1. **glm5_2_nv 6h ~95.48%** — golden 下沿持续区, +0.06pp 微升仍在量级内, 无需关注
2. **glm5_2_nv 6h 0 ATE (改善态持续)** — 路径干净, 自愈保持
3. **真中断 10 (6h)** — stream_absolute_cap nv+ms 都挂, 上游瞬时非旋钮; 30min 0 真中断; 持平 R2118
4. **6h 499=0** — cc2 R2199 全局 settings 改后 openclaw2 域健康持续, 持续观察
5. **dsv4p_nv NVCF function 恶化止跌横盘 (6h 64.97% vs R2118 64.57%)** — 影响 hermes 主 agent (caller unknown/openclaw),
   不影响 cc2/openclaw2. 前 3 轮续跌 (-8.07pp) 本轮横盘止跌, 等 NVCF 端修复 (非本域).
6. **caller 全 `_nv_anthropic/passthrough`** — R2145/R2149 修复稳定零退化
7. **StartedAt 12:40:26Z (中间 1 次 clean restart)** — 非本域触发 (RC=0 非 crash, env 无漂移), 记录不动
8. **STATE 滞后本轮 (第 25 次修正)** — STATE 停 R2114, 主仓已 R2118, 本轮 R2119 对齐. 后续 session 必先 cat STATE
   + git log 主仓 双确认轮号.

## 下一轮该做什么

1. **git pull**: 看 HM1 peer (R2253 KEY_AUTHFAIL 35→25 后下一轮), cc2/hermes2 新轮
2. **拉 30min + 6h + caller 维度**: 重点检验:
   - glm5_2_nv 6h SR 是否 > 95% 持续 (本轮 95.48% golden 下沿)?
   - glm5_2_nv 30min 是否保持 0 ATE (本轮 3 错 2z+1timeout)?
   - 真中断是否非扩散 (本轮 6h 10, 30min 0)?
   - caller 全 `_nv_anthropic/passthrough` 是否不退化 (R2145/R2149 修复)?
   - 6h 499 是否保持 0 (cc2 R2199 全局 settings 改后)?
   - dsv4p_nv NVCF function 是否止跌回升 (本轮 6h 64.97% 横盘, 前轮续跌)?
3. **决策**:
   - glm5_2_nv > 95% + caller 全 nv_anthropic + 30min 0 ATE + 499=0 → NOP 巡检
   - 若 R2145/R2149 修复退化 (caller 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env (cc2 R2199 改后是否被覆盖)
   - 若 ATE 抖动多窗口持续 → 重评估 (但归因上游非旋钮, 大概率仍 NOP)
   - 若 dsv4p_nv 续跌破 60% → 记录但不动 (非本域, NVCF 端问题)
4. 覆写 STATE
