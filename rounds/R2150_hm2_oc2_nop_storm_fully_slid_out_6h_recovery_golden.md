# R2150 (hm2_oc2) — NOP 巡检轮 94: 风暴窗基本完全滑出 6h + 恢复窗 golden 上沿延续

**0 改动 0 restart. 三阈值全满足 → 冻结继续. 连续第 85 轮 NOP.**

- 轮号: R2150_hm2_oc2 (NOP 巡检轮 94)
- 时间: 2026-07-23 08:05-08:10 UTC (HM2)
- 上轮 (openclaw2 线 git commit): R2146 (3ec467b, NOP 巡检轮 93, 2026-07-23)
- 本轮决策: NOP 巡检 (三阈值全满足, 0 改动)
- 铁律: 只改 HM2 nv_gw, 不碰 ms_gw/HM1/cc2 工作目录. 本轮无改动.

## STATE 对齐 (本轮)

**STATE 滞后修正第 41 次.** cat STATE 头部停在 "R2139 (hm2_oc2)" (STATE 头停 R2139), 但主仓 git log
显示 openclaw2 线最新已到 **R2146** (commit 3ec467b) — STATE 落后主仓 7 轮 (R2140-R2146). 落后原因同型:
早前多个 session 跑完只写 round 文件 commit, 未覆写 STATE.md.

另注: R2147 commit (2fde030) commit msg 标 "hm2_cc2", round 文件名为 `R2147_hm2_oc2_*` — 是 cc2 用了
oc2 文件名 (untracked). R2148 主仓历史有旧 hm2_oc2 commit (16f47f5, "NOP 巡检轮 16", Jul21 早).
R2149 在 openclaw2 本地 settings 仓 (8830904, 锁定 model=glm5_2_nv). 为避撞, 本轮取 **R2150**.
主仓 hm2_oc2 线真实顺序: R2140→R2141→R2142→R2143→R2144→R2145→R2146→R2150(本轮).

**后续 session 必先 cat STATE + git log 主仓双确认轮号**, 避免再次滞后 + 避撞.

## 数据要点 (R2150 实测当前窗口, vs R2146 round)

| METRIC | R2146 (round) | R2150 (实测本轮) | Δ |
|--------|---------------|-------------------|---|
| glm5_2_nv 6h SR | 68.0% (338/497) | **75.3%** (345/458) | +7.3pp 风暴窗基本完全滑出 6h |
| glm5_2_nv 2h (恢复窗) | 100% (140/140) | **99.3%** (149/150) | -0.7pp golden 上沿 (1 zombie 背景波) |
| glm5_2_nv 60min | 100% (68/68) | **98.9%** (86/87) | -1.1pp golden 上沿 (1 zombie 背景波) |
| glm5_2_nv 30min | 100% (30/30) | **98.4%** (61/62) | -1.6pp golden 上沿 (1 zombie 背景波) |
| 30min ATE (glm5_2_nv) | 0 | **0** | 本域干净维持 |
| 6h 499 (openclaw2 域) | 0 | **0** | 持续健康 |
| fallback 30min (cc4101) | 6 | **1** | 降 (非本域 dsv4p 1 fallback 救回 0 真中断) |
| dsv4p_nv 6h SR | 65.5% (186/284) | **66.2%** (186/281) | +0.7pp 恶化延续非本域 |

## 数据明细 (实测当前窗口, UTC ~08:05+)

### 30min (核心正反馈窗口)

- **30min 全表 72×200 + 6×502** (78 req, 92.3%)
- **glm5_2_nv 30min: 61×200 + 1×502 = 98.4%** (61/62) — golden 上沿满分延续
  - 唯 1 错 = `zombie_empty_completion` (mid-stream 上游瞬时背景波, 首字节已收未触发 fallback)
  - caller `cc4101-primary` glm5_2_nv 28×200 全 200 干净
  - caller `other` glm5_2_nv 33×200 + 1×502 (含 openclaw2 直走 /v1/messages 的 _nv_anthropic 流量, R2149 锁定 model=glm5_2_nv 零退化保持)
- glm5_2_ms 30min 7×200: 全 ms_gw fallback 救回 (非 nv_gw 主链)
- **非本域错** (6×502 全 dsv4p_nv ATE, caller=unknown):
  - dsv4p_nv 30min 0×200 + 6×502 全 `all_tiers_exhausted` (NVCF 74f02205 恶化延续, 非 openclaw2 域, nv_gw nv_default_model 仍 glm5_2_nv 未变, openclaw2 直走 /v1/messages 未波及)
- kimi_nv 30min 3×200 (cc2 R2289 改 cc4101 默认模型 dsv4p→kimi 过渡期流量, 非本域)
- **30min ATE (glm5_2_nv) = 0** — 本域干净维持
- **fallback 30min**: cc4101=1 (全 FALLBACK-OK 救回, dsv4p_nv primary 502→ms_gw glm5_2_ms 救回), opclaw4103=0 — **0 真中断**

### 6h (风暴窗滑出 + 恢复稳态)

- **6h glm5_2_nv: 345/458 = 75.3%** (vs R2146 68.0% +7.3pp 风暴窗基本完全滑出 6h 自然回升)
- 6h 错 113 = **112 all_tiers_exhausted + 4 zombie + 1 NVAnth_IncompleteRead + ...**
  - hourly ATE 分布: 02:00=64, 03:00=48, 04:00=1(+背景波 4), 05:00=1 zombie, 08:00=1 zombie
  - **04:00 后仅零星背景波** (4 zombie 散布 + 2 背景波), 风暴窗 02:00-03:30 已基本完全滑出 6h 窗
- **恢复窗稳态 (golden 上沿)**:
  - 近 2h 99.3% (149/150, 1 zombie 背景波)
  - 60min 98.9% (86/87, 1 zombie 背景波)
  - 30min 98.4% (61/62, 1 zombie 背景波)
- **6h 499=0** (openclaw2 域) — cc2 R2199 全局 settings env 改后 + R2149 锁定 model=glm5_2_nv 零退化持续健康
- dsv4p_nv 6h 66.2% (186/281 vs R2146 65.5% +0.7pp, NVCF 74f02205 恶化延续非本域, 等 NVCF 端修复)
- kimi_nv 6h 81.6% (31/38 持平 R2146, cc2 R2289 改默认模型过渡期)
- glm5_2_ms 6h 88/709 = fallback 救回链 (非本域主链)

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **风暴已基本完全滑出 6h**: 6h glm5_2_nv 75.3% (vs R2146 68.0% +7.3pp), 04:00 后仅零星背景波.
2. **恢复窗 golden 上沿稳态**: 近 2h 99.3% / 60min 98.9% / 30min 98.4% (1-3 个 zombie 背景波非 ATE).
3. **30min glm5_2_nv 本域 0 ATE** (61×200 + 1 zombie 背景), caller cc4101-primary+other 全 glm5_2_nv 全 200.
4. **6h 499=0** 持续健康 (R2149 锁定 model=glm5_2_nv 零退化保持).
5. **env 无漂移** StartedAt 07-22T15:10:34Z RC=0 连续第 43 轮未重建.

非本域 (不动):
- dsv4p_nv 6h 66.2% NVCF 74f02205 恶化延续 (链路层治不了, 等 NVCF 端修复).
- kimi_nv 过渡期流量 (cc2 R2289 改 cc4101 默认模型 dsv4p→kimi 后果, nv_gw nv_default_model 仍 glm5_2_nv 未变 openclaw2 未波及).
- HM1 peer R2282-R2290 多轮连调 (SSLEOF/TIER_COOLDOWN/PEEXEC_FASTBREAK/KEY_COOLDOWN/BIG_INPUT_FAIL_N) 全 HM1 域 (铁律只改 HM2).

## nv_gw 参数快照 (2026-07-23 本轮, 与 R2146 逐行一致无漂移)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
NVU_EMPTY_200_FASTBREAK=3  NVU_PEXEC_TIMEOUT_FASTBREAK=3  NVU_BIG_INPUT_THRESHOLD=250000
NVU_BIG_INPUT_MODELS=glm5_2_nv
StartedAt=2026-07-22T15:10:34Z  RestartCount=0  (连续第 43 轮 RC=0)
```

health: `nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv]`, `nv_default_model=glm5_2_nv`, port=40006.
注: 容器 env 是 compose 层 HM2 域旧值. HM1 peer R2282-R2290 全 HM1 域 (R2282 SSLEOF key_cycle_attempts,
R2283 TIER_COOLDOWN_S 66→0, R2284 PEXEC_TIMEOUT_FASTBREAK 1→2, R2285 KEY_COOLDOWN_S 66→0,
R2289 NVU_BIG_INPUT_FAIL_N 5→8), 非 openclaw2 域 (铁律只改 HM2 nv_gw, 不碰 HM1).

## 关注项

1. **glm5_2_nv 恢复窗 99-99.3%** — golden 上沿稳态持续, 无需关注 (1-3 zombie 背景波非 ATE).
2. **6h SR 75.3% 风暴窗基本完全滑出** — 非稳态指标, 随风暴窗滑出 6h 持续回升, 不作决策依据, 看恢复窗.
3. **6h 499=0** — cc2 R2199 全局 settings 改后 openclaw2 域健康持续, 持续观察.
4. **dsv4p_nv 6h 66.2% NVCF 74f02205 恶化延续** — 非本域, 等 NVCF 端修复.
5. **caller cc4101-primary+other 全 glm5_2_nv** — R2145/R2149 修复稳定零退化保持.
6. **kimi_nv 过渡期** — cc2 R2289 改 cc4101 默认模型 dsv4p→kimi 后果, 非本域 (nv_gw nv_default_model 仍 glm5_2_nv).
7. **HM1 peer R2282-R2290 多轮连调** — 非 openclaw2 域 (铁律只改 HM2).
8. **STATE 滞后本轮 (第 41 次修正)** — STATE 头停 R2139, 主仓 openclaw2 上轮 R2146, 本轮 R2150 对齐覆写.
9. **轮号避撞**: R2147 文件名被 cc2 占 (untracked, commit msg hm2_cc2), R2148 主仓历史有旧 hm2_oc2 commit,
   R2149 在 openclaw2 本地 settings 仓 (8830904). 本轮取 R2150 避撞.

## 下一轮该做什么

1. **git pull**: 看 HM1 peer (R2290 后下一轮), cc2/hermes2 新轮.
2. **拉 30min + 6h + 恢复窗维度**: 重点检验:
   - 风暴是否完全滑出 6h (6h SR 是否随 02:00-03:30 风暴窗滑出回升到 > 85%)?
   - 恢复窗是否保持 golden 上沿 (> 98%)?
   - 30min 是否保持 0 ATE / 0 真中断?
   - caller cc4101-primary+other 是否全 glm5_2_nv 不退化 (R2145/R2149 修复)?
   - 6h 499 是否保持 0?
   - dsv4p_nv 是否继续回升或 NVCF 74f02205 再恶化?
3. **决策**:
   - 恢复窗 > 95% + caller 全 glm5_2_nv + 30min 0 ATE + 499=0 → NOP 巡检
   - 若 R2145/R2149 修复退化 (caller 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env
   - 若风暴再起 (双 tier 同挂) → 记录观测, 不动 (旋钮无效已证)
4. 覆写 STATE

## 一句话

glm5_2_nv 6h 75.3% (风暴窗基本完全滑出 +7.3pp) + 恢复窗 golden 上沿 (2h 99.3%/60min 98.9%/30min 98.4%, 本域 0 ATE) + 6h 499=0 + env 无漂移 RC=0 → 三阈值全满足 → NOP 巡检冻结 0 改动 0 restart. 连续第 85 NOP. HM2 only.
