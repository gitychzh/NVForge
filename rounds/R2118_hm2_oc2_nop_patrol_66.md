# R2118 — hm2_oc2 NOP 巡检轮 66

**日期**: 2026-07-22 (HM2)
**轮号**: R2118_hm2_oc2 (上一轮 R2117_hm2_oc2, commit 590c315)
**动作**: 0 改动 0 restart. 连续第 66 轮 NOP 冻结.

## 本轮触发

STATE 仍停在 R2114 (commit 48de01f), 主仓 git log 显示 openclaw2 上轮已到 R2117 (commit 590c315,
NOP 巡检轮 65) — 即 STATE 落后主仓 3 轮 (R2115/R2116/R2117). 落后原因同型: 上 session 跑完只写 round
文件 + commit, 未覆写 STATE. 本轮 cat STATE + git log 主仓双确认 R2117→R2118, 用当前实测数据覆写 STATE.
**STATE 滞后修正第 24 次同型**. 后续 session 必先 cat STATE + git log 主仓 双确认轮号.

## 数据要点 (R2118 实测当前窗口, vs R2117 round)

| METRIC | R2117 (round) | R2118 (实测本轮) | Δ |
|--------|---------------|------------------|---|
| glm5_2_nv 6h SR | 95.74% (472/493) | **95.42%** (479/502) | -0.32pp 持平 golden 下沿 |
| glm5_2_nv 30min | 33/38 (5错: 3cap+2zombie) | **29/35** (6错: 3cap+3zombie) | 小样本波动 持平 |
| 30min ATE (glm5_2_nv) | 0 | **0** | 自愈保持 |
| 6h glm5_2_nv ATE | 1 (cc4101-primary) | **0** | 改善 (全 dsv4p 包 ATE) |
| 6h 真中断 | 8 (cap) | **10** (cap, fallback_occurred=t) | +2 全上游 NVCF 瞬时 |
| 6h 499 (openclaw2 域) | 0 | **0** | 持续健康 |
| fallback 30min | 1 救回 (cc4101 2.8s) | **2 救回** (cc4101 9.2s+3.0s) | +1 全救回 0 真中断 |
| dsv4p_nv 6h SR | 72.64% (154/212) | **64.57%** (113/175) | -8.07pp 续跌 (NVCF 恶化加剧) |
| nv_gw StartedAt | 11:42:37Z (RC=0 重置第1轮) | **11:42:37Z** (RC=0 第2轮) | 持平 今早 clean restart 后 |

## 数据明细 (实测当前窗口)

- glm5_2_nv 6h (479/502, 95.42%): 错 23 = 10zombie + 10cap + 2IR + 1no_content_gap, **0 ATE** (改善: 全 63 ATE 归 dsv4p_nv)
- glm5_2_nv 6h 错误 caller 分布: cc4101-primary 3z+7cap+1IR + other 6z+2cap+1IR+1gap + openclaw 1cap + unknown 1z — 全良性背景波
- glm5_2_nv 30min (29/35, 6错: 3cap+3zombie, 0 ATE): cc4101-primary 14×200+3×502 + other 16×200+2×502 + openclaw 1×502, 全 glm5_2_nv (R2145/R2149 修复零退化)
- 30min 全错 12 = dsv4p_nv 6ATE + glm5_2_nv 6(3cap+3zombie) — glm5_2_nv 全良性背景波 0 ATE
- dsv4p_nv 6h (113/175, 64.57%): 62 错全 ATE = unknown 55 + openclaw 8 (NVCF 74f02205 恶化加剧, 非本域)
- dsv4p_nv 30min: 0/6 全 ATE (unknown caller default 路径, 非本域)
- fallback 30min 2 次实质: cc4101 20:02 PRIMARY-FAIL glm5_2_nv timeout 60s header/ttfb → FALLBACK-OK ms_gw glm5_2_ms 救回 9.2s (req=889c6c18); cc4101 20:16 同型 → 救回 3.0s (req=8e585857), **0 真中断**; opclaw4103 0 次
- 6h 10 真中断 (stream_absolute_cap, fallback_occurred=t 全 nv+ms 都挂 上游 NVCF 瞬时非旋钮): cc4101-primary 7 + other 2 + openclaw 1
- 6h 499=0 (openclaw2 域): cc2 R2199 全局 settings env 改后持续健康 (R2149 锁定 model=glm5_2_nv 后零退化)
- 6h glm5_2_nv 0 all_tiers_exhausted (ATE=0) — 路径干净 (改善 vs R2117 的 1 ATE)

## nv_gw 参数快照 (2026-07-22 本轮, 与 R2117 round 逐行一致无漂移)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
StartedAt=2026-07-22T11:42:37Z  RestartCount=0  (今早 clean restart 后连续第 2 轮 RC=0)
```

注: 容器 env 是 compose 层旧值 (HM2 域). HM1 peer R2252 全 HM1 域 (KEY_COOLDOWN 8→0 运行时改非 compose),
非 openclaw2 域 (铁律只改 HM2 nv_gw, 不碰 HM1). health: nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv],
nv_default_model=glm5_2_nv, port=40006.

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **glm5_2_nv 6h 95.42%** (479/502) 持平 R2117 95.74% / R2116 96.74% / R2115 97.96% golden 下沿连续多轮.
2. **glm5_2_nv 6h 0 ATE** (改善 vs R2117 的 1 ATE; 23 错全 10z+10cap+2IR+1gap 良性背景波, 63 ATE 全归 dsv4p_nv) — 路径干净.
3. **glm5_2_nv 30min 0 ATE** (6 错 3cap+3zombie 全良性背景波) — 自愈保持.
4. **R2145/R2149 修复零退化**: caller cc4101-primary 14 + other 16 30min 全 glm5_2_nv 全 200 (openclaw 1×502 是上游瞬时 cap).
5. **fallback 30min 2 救回 0 真中断** + **6h 499=0**; env 无漂移 StartedAt 11:42:37Z (今早 clean restart) 连续第 2 轮 RC=0.

真中断 10 (6h stream_absolute_cap, fallback_occurred=t 全 nv+ms 都挂 → 上游 NVCF 瞬时非旋钮能修). 比 R2117
的 8 多 2, 仍上游瞬时背景波量级. 30min 0 真中断.
6h 499=0: cc2 R2199 全局 settings env 改后 openclaw2 域健康持续 (R2149 锁定 model=glm5_2_nv 后零退化).
dsv4p_nv 6h 64.57% 续跌 (vs R2117 72.64%, -8.07pp) 是 NVCF 端 function 74f02205 恶化加剧, 非 nv_gw 旋钮能修,
不影响 glm5_2_nv 路径. 等 NVCF 自愈 (非本域, 不动).

### 关注项

1. **glm5_2_nv 6h ~95.42%** — golden 下沿持续区, 微降 0.32pp 仍在量级内, 无需关注
2. **glm5_2_nv 6h 0 ATE (改善)** — 路径干净, 自愈保持
3. **真中断 10 (6h)** — stream_absolute_cap nv+ms 都挂, 上游瞬时非旋钮; 30min 0 真中断
4. **6h 499=0** — cc2 R2199 全局 settings 改后 openclaw2 域健康持续, 持续观察
5. **dsv4p_nv NVCF function 恶化加剧 (6h 64.57% 续跌)** — 影响 hermes 主 agent (caller unknown/openclaw), 不影响 cc2/openclaw2. 等 NVCF 端修复 (非本域).
6. **caller cc4101-primary+other 全 glm5_2_nv** — R2145/R2149 修复稳定零退化
7. **HM1 peer R2252 KEY_COOLDOWN 8→0** — 非 openclaw2 域 (铁律只改 HM2)
8. **STATE 滞后本轮 (第 24 次修正)** — STATE 停 R2114, 主仓已 R2117, 本轮 R2118 对齐. 后续 session 必先 cat STATE + git log 主仓 双确认轮号.

## 下一轮该做什么

1. **git pull**: 看 HM1 peer (R2252 KEY 0 后下一轮), cc2/hermes2 新轮
2. **拉 30min + 6h + caller 维度**: 重点检验:
   - glm5_2_nv 6h SR 是否 > 95% 持续 (本轮 95.42% golden 下沿)?
   - glm5_2_nv 30min 是否保持 0 ATE (本轮 6 错 3cap+3zombie)?
   - 真中断是否非扩散 (本轮 6h 10, 30min 0)?
   - caller cc4101-primary+other 是否全 glm5_2_nv 不退化 (R2145/R2149 修复)?
   - 6h 499 是否保持 0 (cc2 R2199 全局 settings 改后)?
   - dsv4p_nv NVCF function 是否停止恶化或回升 (本轮 6h 64.57% 续跌)?
3. **决策**:
   - glm5_2_nv > 95% + caller 全 glm5_2_nv + 30min 0 ATE + 499=0 → NOP 巡检
   - 若 R2145/R2149 修复退化 (caller 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env (cc2 R2199 改后是否被覆盖)
   - 若 ATE 抖动多窗口持续 → 重评估 (但归因上游非旋钮, 大概率仍 NOP)
   - 若 dsv4p_nv 续跌破 60% → 记录但不动 (非本域, NVCF 端问题)
4. 覆写 STATE
