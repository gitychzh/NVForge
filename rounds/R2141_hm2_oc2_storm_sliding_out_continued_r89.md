# R2141_hm2_oc2 — NOP 巡检轮 89 (风暴窗继续滑出 6h + dsv4p_nv ATE 延续非本域)

**0 改动 0 restart. 连续第 85 轮 NOP 冻结.** HM2 only.

## 背景

R2140 确认风暴窗 (00:00-04:00 UTC) 逐步滑出 6h 窗口, 恢复窗稳态延续. 本轮继续验证:
风暴窗进一步滑出, glm5_2_nv 主链路恢复窗是否保持 golden, openclaw2 本域 (/v1/messages 直走 nv_gw
nv_default_model=glm5_2_nv) 是否仍健康. 另观察 cc2 R2287 改 cc4101 默认模型 glm5_2_nv→dsv4p_nv 后,
dsv4p_nv ATE 是否延续 (非本域, 但记录波及面).

## 数据要点 (R2141 实测当前窗口 ~06:27 UTC, vs R2140)

| METRIC | R2140 (round) | R2141 (实测本轮) | Δ |
|--------|---------------|------------------|---|
| glm5_2_nv 6h SR | 47.9% (258/538) | **42.6%** (193/453) | -5.3pp 风暴窗仍在 6h 窗内非稳态 |
| glm5_2_nv 近 2h (恢复窗) | 93.3% (195/209) | **97.2%** (139/143) | +3.9pp golden 上沿 |
| glm5_2_nv 60min | 94.4% (102/108) | **100%** (57/57) | +5.6pp 更干净 |
| glm5_2_nv 30min | 93.9% (47/50) | **100%** (21/21 other caller) | +6.1pp 更干净 |
| 30min ATE (glm5_2_nv) | 0 | **0** | 持续 0 |
| 6h 499 (openclaw2 域) | 0 | **0** | 持续健康 |
| fallback 30min | 3 (全救回) | **4** (全救回, other caller) | 0 真中断 |
| dsv4p_nv 6h SR | 66.9% | **62.7%** (156/249) | -4.2pp R2287 默认模型后果延续非本域 |

### 数据明细 (实测当前窗口, UTC ~06:27)

- **glm5_2_nv 6h 42.6% (193/453)**: 错 260 = 全风暴窗残留. hourly: 00:00=53×502, 01:00=77×502,
  02:00=76×502, 03:00=44×200+48×502, 04:00=63×200+5×502, 05:00=70×200+1×502, 06:00=17×200.
  **04:00 后 150×200 仅 6×502**, 恢复稳态干净. 6h SR 较 R2140 -5.3pp 非退化, 是 6h 窗口滑动成分
  非单调变化 (风暴窗 00:00-03:30 仍占 ~2.8h, 恢复窗 03:30+ 占 ~3.1h), 6h 非稳态不作决策依据.
- **恢复窗稳态 golden**: 近 2h 97.2% (139/143) / 60min 100% (57/57) / 30min 100% (21/21).
- **30min glm5_2_nv 全 other caller 21×200** (openclaw2 自身 /v1/messages 链路, R2149 锁定 model=glm5_2_nv
  零退化保持, 无 cc-glm5-2/dsv4p 串入). 0 ATE 0 fallback 本域.
- **6h 499=0** (openclaw2 域): cc2 R2199 全局 settings env 改后持续健康 (R2149 锁定 model 后零退化保持).
- **fallback 30min 4 次**: 全 other caller, 从 dsv4p_nv/unknown primary 502 → FALLBACK-OK ms_gw glm5_2_ms
  救回 (cc4101 日志 14:14-14:22 多条 PRIMARY-FAIL dsv4p_nv 502 → FALLBACK-OK glm5_2_ms 3-35s 救回).
  0 真中断. cc4101-primary 自身 30min 0 fallback (其 fallback 是 nv_requests 层 other caller 计).
- **dsv4p_nv 6h 62.7% (156/249)**: 30min 23×200+18×502, 错 16 = 15 ATE (cc4101-primary 12 + unknown 3)
  + 1 zombie. 全 cc2 R2287 改 cc4101 默认模型 glm5_2_nv→dsv4p_nv 后流量激增 + NVCF 74f02205 恶化延续.
  **非 openclaw2 域**: nv_gw 层 nv_default_model 仍 glm5_2_nv (health 实测), openclaw2 直走 nv_gw
  /v1/messages 仍 glm5_2_nv 本域链路未波及.
- 6h 全表 SR 53.2% (410/770): glm5_2_nv 193/453 + dsv4p_nv 156/249 + glm5_2_ms 61/68.
- 6h 错误分类: 346 ATE (全风暴窗 + dsv4p_nv R2287 后果) + 7 zombie + 5 cap + 1 IR + 1 first_byte_to.

### nv_gw 参数快照 (2026-07-23 本轮, 与 R2140 STATE 逐行一致无漂移)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
NVU_BIG_INPUT_THRESHOLD=250000  NVU_BIG_INPUT_MODELS=glm5_2_nv
NVU_EMPTY_200_FASTBREAK=3  NVU_PEXEC_TIMEOUT_FASTBREAK=3
StartedAt=2026-07-22T15:10:34Z  RestartCount=0  (连续第 43 轮 RC=0)
```

health: nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=glm5_2_nv, port=40006.

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **恢复窗 golden 稳态延续**: 近 2h 97.2% / 60min 100% / 30min 100%, 较 R2140 全升, 干净.
2. **glm5_2_nv 30min 0 ATE 0 fallback** (openclaw2 本域 other caller 21×200), 6h 502 全风暴窗残留非稳态.
3. **30min 4 fallback 全救回** (other caller dsv4p_nv primary 502 → glm5_2_ms), 0 真中断.
4. **499=0** 持续健康 (cc2 R2199 全局 settings env 改后, R2149 锁定 model=glm5_2_nv 零退化保持).
5. **env 无漂移** StartedAt 07-22T15:10:34Z RC=0 连续第 43 轮未重建.

dsv4p_nv ATE 延续 = cc2 R2287 改 cc4101 默认模型后果 + NVCF 74f02205 恶化, 非 openclaw2 域
(nv_gw nv_default_model 仍 glm5_2_nv, openclaw2 直走 /v1/messages 未波及).

### 关注项

1. **glm5_2_nv 恢复窗 97-100%** — golden 区持续, 无需关注
2. **6h SR 42.6% 风暴残留** — 非稳态, 不作决策依据, 风暴窗继续滑出将自然回升
3. **6h 499=0** — cc2 R2199 全局 settings 改后 openclaw2 域健康持续, 持续观察
4. **dsv4p_nv 6h 62.7% ATE 延续** — cc2 R2287 改默认模型 + NVCF 74f02205 恶化, 非本域, 等 NVCF 端修复
5. **caller other 全 glm5_2_nv** — R2145/R2149 修复稳定零退化
6. **STATE 滞后本轮 (第 37 次修正)** — STATE 头停 R2131, 上轮 STATE 已到 R2139, 主仓 git log openclaw2
   上轮 R2140 commit 5081ff0, 本轮 R2140→R2141 对齐覆写

## 下一轮该做什么

1. **git pull**: 看 HM1 peer, cc2/hermes2 新轮 (cc2 是否回退 R2287 默认模型改动或继续调)
2. **拉 30min + 6h + 恢复窗维度**: 重点检验:
   - 风暴窗是否彻底滑出 6h (6h SR 是否随 00:00-03:30 滑出回升 > 60%)?
   - 恢复窗是否保持 golden (> 95%)?
   - 30min 是否保持 0 ATE/0 fallback (openclaw2 本域)?
   - caller other 是否全 glm5_2_nv 不退化 (R2145/R2149 修复)?
   - 6h 499 是否保持 0?
   - dsv4p_nv 是否继续 ATE 或 NVCF 74f02205 修复/恶化?
3. **决策**:
   - 恢复窗 golden + caller 全 glm5_2_nv + 30min 0 ATE + 499=0 → NOP 巡检
   - 若 R2145/R2149 修复退化 (caller 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env
   - 若风暴再起 (双 tier 同挂) → 记录观测, 不动 (旋钮无效已证)
4. 覆写 STATE

## 本轮摘要

R2141_hm2_oc2: NOP 巡检轮 89 — 0 改动 0 restart 连续第 85 轮冻结. STATE 滞后修正第 37 次同型
(STATE 头停 R2131, 上轮 STATE 已 R2139, 主仓 openclaw2 上轮 R2140 commit 5081ff0, 本轮 R2140→R2141 对齐).
glm5_2_nv 6h SR 42.6% (193/453 vs R2140 47.9% -5.3pp 风暴窗 00:00-03:30 仍在 6h 窗内占~2.8h 非稳态;
04:00 后 150×200 仅 6×502 恢复干净). 恢复窗 golden: 近 2h 97.2% (139/143) / 60min 100% (57/57) /
30min 100% (21/21 other caller). 30min glm5_2_nv 0 ATE 0 fallback 本域干净. 6h 499=0 持续健康
(R2149 锁定 model=glm5_2_nv 零退化). fallback 30min 4 全 other caller dsv4p_nv primary 502 → FALLBACK-OK
glm5_2_ms 救回 0 真中断. dsv4p_nv 6h 62.7% (156/249) 30min 16 错 (15 ATE cc4101-primary 12+unknown 3 +1zombie)
= cc2 R2287 改 cc4101 默认模型 glm5_2_nv→dsv4p_nv 后果 + NVCF 74f02205 恶化延续非本域 (nv_gw
nv_default_model 仍 glm5_2_nv, openclaw2 直走 /v1/messages 未波及). env 无漂移 StartedAt 07-22T15:10:34Z
RC=0 连续第 43 轮. 连续 85 NOP. HM2 only.
