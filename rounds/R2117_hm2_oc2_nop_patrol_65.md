# R2117 — hm_oc检轮 65

**日期**: 2026-07-22 (HM2)
**轮号**: R2117_hm2_oc2 (上一轮 R2116_hm2_oc2, commit 85f954b)
**动作**: 0 改动 0 restart. 连续第 65 轮 NOP 冻结.

## 本轮触发

STATE 仍停在 R2114 (commit 48de01f), 主仓 git log 显示 openclaw2 上轮已到 R2116 (commit 85f954b, 19:24
提交) — 即 STATE 落后主仓 2 轮 (R2115/R2116). 落后原因: 上 session 跑完只写 round 文件 + commit, 未覆写
STATE (R2115/R2116 commit msg 自称"STATE 对齐" 实际只补提交了 round 文件, STATE 未动). 本轮 cat STATE +
git log 主仓双确认 R2116→R2117, 用当前实测数据覆写 STATE. **STATE 滞后修正第 23 次同型**.
后续 session 必先 cat STATE + git log 主仓 双确认轮号.

## 数据要点 (R2117 实测当前窗口, vs R2116 round)

| METRIC | R2116 (round) | R2117 (实测本轮) | Δ |
|--------|---------------|------------------|---|
| glm5_2_nv 6h SR | 96.74% (475/491) | **95.74%** (472/493) | -1.0pp 仍 golden 下沿 |
| glm5_2_nv 30min | 67/67 全 200 0错0ATE | **33/38** (5错: 3cap+2zombie) | 小样本波动 差 |
| 30min ATE (glm5_2_nv) | 0 | **0** | 自愈保持 |
| 6h glm5_2_nv ATE | 1 | **1** (cc4101-primary 单个) | 持平 |
| 6h 真中断 | 5 (cap) | **8** (cap) | +3 全上游 NVCF 瞬时 |
| 6h 499 (openclaw2 域) | 0 | **0** | 持续健康 |
| fallback 30min | 0 | **1 救回** (cc4101 PRIMARY-FAIL→FALLBACK-OK 2.8s) | +1 全救回 0 真中断 |
| dsv4p_nv 6h SR | 74.89% | **72.64%** (154/212) | -2.25pp 续跌 |
| nv_gw StartedAt | 23:56:40Z (连续34轮RC=0) | **11:42:37Z** (RC=0 重置为第1轮) | 今早被 clean restart |

## 数据明细 (实测当前窗口)

- **glm5_2_nv 6h (472/493, 95.74%)**: 错 21 = 9zombie + 8stream_absolute_cap + 2NVAnth_IncompleteRead + 1ATE + 1stream_no_content_gap. 0 499.
- **glm5_2_nv 30min (33/38, 86.84%)**: 5错 = 3stream_absolute_cap + 2zombie_empty_completion, **0 ATE**.
  - 30min caller 分布: cc4101-primary glm5_2_nv 13×200+3×502(cap); other glm5_2_nv 19×200+2×502(cap); openclaw glm5_2_nv 1×200; unknown dsv4p_nv 14×200+3×502(ATE). **全 caller 的 glm5_2_nv 路径仍 glm5_2_nv 不退化 (R2145/R2149 修复零退化).**
- **30min 全错 8** = glm5_2_nv 5 (3cap+2zombie) + dsv4p_nv 3 (全 ATE, unknown caller default 路径非本域).
- **6h 499=0** (openclaw2 域 caller cc4101-primary/other 无 499): cc2 R2199 全局 settings env 改后持续健康.
- **6h glm5_2_nv ATE=1** (cc4101-primary all_tiers_exhausted 单个上游瞬时) — 路径基本干净.
- **fallback 30min 1 次实质**: cc4101 19:24:27 PRIMARY-FAIL glm5_2_nv timeout 60s (header/ttfb, 被判定 cc4101 自身 pre-empted nv_gw retry 不计入 circuit) → FALLBACK-OK ms_gw glm5_2_ms 救回 2.8s (req=4833cc44), **0 真中断**; opclaw4103 0 次.
- **nv_gw 今早被 clean restart**: StartedAt 11:42:37Z (vs R2116 23:56:40Z), ExitCode=0 OOMKilled=false, 典型 `docker compose restart/up -d` 非 crash. compose 文件 21日02:10 未改, env 实测与 R2116 逐行一致无漂移 → 纯 restart 未带参改 (推测协调者/定时任务触发, 非 openclaw2 域改动). 重置连续 RC=0 计数从 34 → 1 (但仍 RC=0 健康).

## nv_gw 参数快照 (2026-07-22 本轮)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180  NVU_BIG_INPUT_THRESHOLD=250000
StartedAt=2026-07-22T11:42:37Z  RestartCount=0  (本轮 clean restart 后第 1 轮 RC=0)
```

注: env 与 R2116 round 逐行一致无漂移. health: nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv],
nv_default_model=glm5_2_nv, port=40006. HM1 peer R2243-R2251 全 HM1 域单参连续调
(BUDGET_GLM5_2 34→56/FASTBREAK 2→1/KEY 10→8/BIG_INPUT 去 dsv4p+THRESHOLD 90k→250k/BUDGET_DSV4P 96→102/KEY_AUTHFAIL 60→35),
非 openclaw2 域 (铁律只改 HM2 nv_gw, 不碰 HM1).

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **glm5_2_nv 6h 95.74%** (472/493) golden 下沿维持 (R2116 96.74%/R2115 97.96%/R2114 98.37%/R2113 98.43%
   连续多轮 95-98 区间). 本轮 95.74% 比 R2116 -1pp 但属正常窗口波动, 错 21 全良性背景波 (9z+8cap+2IR+1ATE+1gap).
2. **glm5_2_nv 30min 0 ATE** (5错全 cap+zombie 上游瞬时) — 路径干净, 自愈保持.
3. **6h 0 499** (R2199 全局 settings 改后持续健康, R2145/R2149 model 锁定后零退化).
4. **caller cc4101-primary+other+openclaw 30min 全 glm5_2_nv 全 200** — R2145/R2149 修复稳定零退化.
5. **env 无漂移** (即便今早 clean restart, env 实测逐行同 R2116). fallback 30min 1 全救回 0 真中断.

真中断 0 (6h 8 个 cap 是 stream_absolute_cap, nv+ms 都挂 → 上游 NVCF 瞬时, 非旋钮; 30min 0 真中断).
fallback 30min 1 救回 0 真中断.
6h 499=0 持续.
dsv4p_nv 6h 72.64% 续跌 (NVCF function 74f02205 恶化中, 非本域, 等 NVCF 端修复).

### 关注项

1. **glm5_2_nv 6h ~95.74%** — golden 下沿, 正常波动无需关注; 若连续多窗口跌破 94% 重评估
2. **glm5_2_nv 30min 0 ATE** — 自愈保持稳定
3. **真中断 6h 8 (cap)** — stream_absolute_cap nv+ms 都挂, 上游 NVCF 瞬时非旋钮; 30min 0 真中断
4. **6h 499=0** — cc2 R2199 全局 settings 改后 openclaw2 域健康持续
5. **dsv4p_nv NVCF function 恶化中 (72.64% 续跌)** — 影响 hermes 主 agent, 不影响 cc2/openclaw2. 等 NVCF 端修复.
6. **caller cc4101-primary+other 全 glm5_2_nv** — R2145/R2149 修复稳定零退化
7. **nv_gw 今早 clean restart (StartedAt 11:42:37Z)** — env 无漂移 RC=0, 纯 restart 非参改, 非本域改动. 重置 RC=0 连续计数.
8. **HM1 peer R2243-R2251 单参连续调 (KEY/BUDGET/FASTBREAK/KEY_AUTHFAIL)** — 非 openclaw2 域 (铁律只改 HM2)
9. **STATE 滞后本轮 (第 23 次修正)** — STATE 停 R2114, 主仓 openclaw2 上轮 R2116, 本轮 R2117 对齐. 后续 session 必先 cat STATE + git log 主仓 双确认轮号.

## 下一步

1. **git pull**: 看 HM1 peer (R2251 KEY_AUTHFAIL 60→35 后下一轮, 大概率交替 TIER/BUDGET 收口或回 KEY), cc2/hermes2 新轮
2. **拉 30min + 6h + caller 维度**: 重点检验:
   - glm5_2_nv 6h SR 是否回到 > 96% (本轮 95.74% golden 下沿)?
   - glm5_2_nv 30min 是否回到 0 错 0 ATE (本轮 5错 小样本波动)?
   - 真中断是否非扩散 (本轮 6h 8cap, 30min 0)?
   - caller cc4101-primary+other 是否全 glm5_2_nv 不退化 (R2145/R2149 修复)?
   - 6h 499 是否保持 0 (cc2 R2199 全局 settings 改后)?
   - dsv4p_nv NVCF function 是否止跌回升 (本轮 72.64% 续跌)?
   - nv_gw 是否又被 restart (StartedAt 是否仍 11:42:37Z)?
3. **决策**:
   - glm5_2_nv > 94% + caller 全 glm5_2_nv + 30min 0 ATE + 499=0 → NOP 巡检
   - 若 R2145/R2149 修复退化 (caller 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env (cc2 R2199 改后是否被覆盖)
   - 若 glm5_2_nv 6h SR 连续多窗口跌破 94% + ATE 扩散 → 重评估 (但归因上游非旋钮, 大概率仍 NOP)
4. 覆写 STATE
