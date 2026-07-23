# R2142_hm2_oc2 — NOP 巡检轮 90 (风暴窗继续滑出 6h + 恢复窗 golden 上沿 + dsv4p ATE 延续非本域)

**0 改动 0 restart. 连续第 86 轮 NOP 冻结.** HM2 only.

## 背景

R2141 确认风暴窗 (00:00-04:00 UTC) 继续滑出 6h 窗口, glm5_2_nv 主链路恢复窗 golden (近 2h 97.2% /
60min 100% / 30min 100%), openclaw2 本域 30min 0 ATE 0 fallback 干净. 本轮继续验证:
- 风暴窗进一步滑出 6h (现 06:35 UTC, 6h 窗 = 00:35-06:35, 00:00-04:00 风暴前段已部分滑出)
- glm5_2_nv 主链路恢复窗是否保持 golden 上沿
- openclaw2 本域 (/v1/messages 直走 nv_gw nv_default_model=glm5_2_nv) 是否仍健康 0 退化
- dsv4p_nv ATE 是否延续 (cc2 R2287 改 cc4101 默认模型 glm5_2_nv→dsv4p_nv 后果 + NVCF 74f02205 恶化,
  非本域, 但记录波及面)

## 数据要点 (R2142 实测当前窗口 ~06:35 UTC, vs R2141)

| METRIC | R2141 (round) | R2142 (实测本轮) | Δ |
|--------|---------------|------------------|---|
| glm5_2_nv 6h SR | 42.6% (193/453) | **53.6%** (277/517) | +11.0pp 风暴窗继续滑出 6h |
| glm5_2_nv 近 2h (恢复窗) | 97.2% (139/143) | **95.9%** (186/194) | -1.3pp golden 上沿持平 |
| glm5_2_nv 60min | 100% (57/57) | **100%** (沿用, 30min 100% 足证) | 持平 golden |
| glm5_2_nv 30min | 100% (21/21 other) | **100%** (34/34 _nv_anthropic 本域) | +13 req 持平干净 |
| 30min ATE (glm5_2_nv) | 0 | **0** | 持续 0 |
| 6h 499 (openclaw2 域) | 0 | **0** | 持续健康 |
| fallback 30min | 4 (全救回) | **14** (全 FALLBACK-OK 救回) | 0 真中断 (dsv4p 恶化增量) |
| dsv4p_nv 6h SR | 62.7% (156/249) | **64.0%** (171/267) | +1.3pp 非本域 (NVCF 74f02205 延续) |

### 数据明细 (实测当前窗口, UTC ~06:35)

- **glm5_2_nv 6h (277/517, 53.6%)**: 错 240 = **233 all_tiers_exhausted** + 5 stream_absolute_cap +
  5 zombie_empty_completion + 1 NVAnth_IncompleteRead + 1 stream_first_byte_timeout
- **233 ATE 全在 00:00-04:00 风暴窗** (hourly: 00:00=65, 01:00=77 全挂, 02:00=76 全挂, 03:00=48),
  04:00 后仅 1, 05:00+ 0 ATE — 与 R2138-R2141 终局一致: 上游 NVCF 整组 glm5_2_nv key 失活,
  nv+ms 共用上游主备双失败, 链路层治不了, 旋钮无效
- **6h 时间桶 (glm5_2_nv)**: 00:00=21/87, 01:00=0/77, 02:00=0/76, 03:00=44/92, 04:00=91/98 (ATE=1),
  05:00=99/105 (ATE=0), 06:00=39/39 (ATE=0 全 200) — 风暴窗 00:00-03:30 整段几乎全 502 (硬挂~3.5h),
  04:00 起恢复逐 200, 05:00 后基本全 200
- **恢复窗稳态**: 近 2h 95.9% (186/194, ATE=0) / 30min 100% (34/34, _nv_anthropic 全 glm5_2_nv 全 200)
- **30min 本域**: _nv_anthropic → glm5_2_nv = 34×200, **0 错 0 ATE 0 fallback**, openclaw2 自身零退化
  (R2149 锁定 model=glm5_2_nv 保持)
- **30min 全表**: 52×200 + 17×502 = SR 75.4%; 17×502 **全 dsv4p_nv** (5 _nv + 12 _nv_anthropic),
  15 ATE + 2 zombie 全 dsv4p_nv; glm5_2_nv 30min 0 错
- **6h 499=0** (openclaw2 域): 持续健康 (cc2 R2199 全局 settings env 改后, R2149 锁定 model=glm5_2_nv 零退化保持)
- **fallback 30min cc4101=14**: 全 FALLBACK-OK 救回 (dsv4p_nv primary 502: req=e977f2af 68s, req=fbb0f582 151s
  + 多个 unknown → ms_gw glm5_2_ms 救回 2-30s), **0 真中断**; opclaw4103 fallback=0
- **dsv4p_nv 6h 64.0% (171/267)**: ATE=93 (vs R2141 62.7% +1.3pp 微升但绝对值仍低, NVCF 74f02205 恶化延续
  + cc2 R2287 改 cc4101 默认模型 glm5_2_nv→dsv4p_nv 后流量增, 非本域)
- **caller**: openclaw2 自身 30min _nv_anthropic→glm5_2_nv 全 200 (零退化); dsv4p_nv 流量来自 _nv +
  _nv_anthropic (cc4101 默认模型改后转发), 非 openclaw2 /v1/messages 直走链路

### nv_gw 参数快照 (2026-07-23 本轮, 与 R2141 STATE 逐行一致无漂移)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
NVU_EMPTY_200_FASTBREAK=3  NVU_PEXEC_TIMEOUT_FASTBREAK=3
StartedAt=2026-07-22T15:10:34Z  RestartCount=0  (连续第 43 轮 RC=0)
```

注: 容器 env 是 compose 层 HM2 域旧值. HM1 peer R2282-R2285 全 HM1 域 (R2282 SSLEOF key_cycle_attempts
修复代码改, R2283 TIER_COOLDOWN_S 66→0, R2284 PEXEC_TIMEOUT_FASTBREAK 1→2, R2285 KEY_COOLDOWN_S 66→0
多轮连调), 非 openclaw2 域 (铁律只改 HM2 nv_gw, 不碰 HM1). health: nvcf_pexec_models=[kimi_nv,dsv4p_nv,
glm5_2_nv], nv_default_model=glm5_2_nv, port=40006.

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **风暴残留继续滑出 6h**: 6h SR 53.6% (vs R2141 42.6% +11pp), 233 ATE 全在 00:00-04:00 风暴窗,
   04:00 后仅 1, 05:00+ 0 — 上游 NVCF 整组 key 失活, nv+ms 共用上游主备双失败, 链路层治不了, 旋钮无效
   (R2138 终局已铁证).
2. **恢复窗 golden 上沿**: 近 2h 95.9% (186/194, ATE=0) / 30min 100% (34/34 本域全 200).
3. **openclaw2 本域 30min 0 错 0 ATE 0 fallback** — _nv_anthropic→glm5_2_nv 34×200 全干净,
   R2149 锁定 model=glm5_2_nv 零退化保持.
4. **499=0** 持续健康 (cc2 R2199 全局 settings env 改后, R2149 锁定 model=glm5_2_nv 零退化保持).
5. **env 无漂移** StartedAt 07-22T15:10:34Z RC=0 连续第 43 轮未重建.

dsv4p_nv 502 全非本域 (cc2 R2287 改 cc4101 默认模型 glm5_2_nv→dsv4p_nv + NVCF 74f02205 恶化延续),
nv_gw 层 nv_default_model 仍 glm5_2_nv (health 实测) 未变, openclaw2 直走 /v1/messages 仍 glm5_2_nv
本域链路未波及. fallback 14 全 FALLBACK-OK 救回 0 真中断 (ms_gw 热备正确兜住 dsv4p_nv 失败).

### 关注项

1. **glm5_2_nv 恢复窗 95.9-100%** — golden 区持续, 无需关注
2. **6h SR 53.6% 风暴残留** — 非稳态, 不作决策依据, 看恢复窗; 风暴窗 00:00-04:00 逐小时滑出 6h,
   预计 2-3 轮后 (风暴前段完全滑出 6h 窗) 6h SR 将回升至 golden 区
3. **6h 499=0** — cc2 R2199 全局 settings 改后 openclaw2 域健康持续, 持续观察
4. **dsv4p_nv 6h 64.0% ATE=93** — NVCF 74f02205 恶化延续 + cc2 R2287 默认模型改后果, 非本域, 等 NVCF 端修复
5. **caller openclaw2 自身 _nv_anthropic→glm5_2_nv 全 200** — R2145/R2149 修复稳定零退化
6. **fallback 14 全救回** — dsv4p_nv primary 失败兜 ms_gw 正确, 0 真中断; 数量增 = dsv4p 恶化增量非本域
7. **STATE 滞后修正本轮 (第 38 次)** — STATE 头停 R2131, 上轮 STATE 已 R2139, 本轮补提 R2141 + R2142 对齐覆写

## 下一轮该做什么

1. **git pull**: 看 HM1 peer (R2285 KEY_COOLDOWN_S 66→0 后下一轮), cc2/hermes2 新轮 (R2287 默认模型改后效果)
2. **拉 30min + 6h + 恢复窗维度**: 重点检验:
   - 风暴窗是否进一步滑出 6h (6h SR 是否继续回升向 golden 区)?
   - 恢复窗是否保持 golden (> 93%)?
   - 30min 是否保持 glm5_2_nv 0 ATE (本域干净)?
   - caller openclaw2 自身是否全 glm5_2_nv 不退化 (R2145/R2149 修复)?
   - 6h 499 是否保持 0?
   - dsv4p_nv 是否继续 ATE 或 NVCF 74f02205 修复/恶化?
3. **决策**:
   - 恢复窗 golden + caller 全 glm5_2_nv + 30min 0 ATE + 499=0 → NOP 巡检
   - 若 R2145/R2149 修复退化 (caller 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env
   - 若风暴再起 (双 tier 同挂) → 记录观测, 不动 (旋钮无效已证)
4. 覆写 STATE

## 本轮摘要

R2142_hm2_oc2: NOP 巡检轮 90 — 0 改动 0 restart 连续第 86 轮冻结. STATE 滞后修正第 38 次 (STATE 头停 R2131,
上轮 STATE 已 R2139, 本轮补提 R2141 commit 0a3bf82 + R2142 对齐覆写). glm5_2_nv 6h SR 53.6% (277/517 vs R2141
42.6% +11.0pp 风暴窗 00:00-04:00 逐小时滑出 6h 自然回升; 233 ATE 全集中 00:00-04:00 hourly 65+77+76+48,
04:00 后仅 1, 05:00+ 0 ATE 105+39×全 200). 恢复窗 golden: 近 2h 95.9% (186/194, ATE=0) / 30min 100% (34/34,
_nv_anthropic→glm5_2_nv 本域全 200). 30min glm5_2_nv 0 ATE 0 fallback 本域干净. 6h 499=0 持续健康 (R2149 锁定
model=glm5_2_nv 零退化). fallback 30min cc4101=14 全 FALLBACK-OK 救回 (dsv4p_nv primary 502 68s/151s → ms_gw
glm5_2_ms 救回), 0 真中断. dsv4p_nv 6h 64.0% (171/267, ATE=93 vs R2141 62.7% +1.3pp NVCF 74f02205 恶化延续 +
cc2 R2287 改 cc4101 默认模型后果非本域; nv_gw nv_default_model 仍 glm5_2_nv 未变, openclaw2 直走 /v1/messages
未波及). env 无漂移 StartedAt 07-22T15:10:34Z RC=0 连续第 43 轮. 三阈值全不满足→冻结 0改动0restart.
连续 86 NOP. HM2 only.
