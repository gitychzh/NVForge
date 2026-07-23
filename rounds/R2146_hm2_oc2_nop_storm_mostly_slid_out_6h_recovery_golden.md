# R2146_hm2_oc2 — NOP 巡检轮 93 (风暴窗基本滑出 6h + 恢复窗 golden 满分延续)

**轮号**: R2146_hm2_oc2  **日期**: 2026-07-23 (UTC ~07:39 / HM2)
**类型**: NOP 巡检轮 (连续第 84 轮冻结, 0 改动 0 restart)
**STATE 滞后修正**: 第 40 次 (STATE 头停 R2139, 主仓 openclaw2 上轮 R2145 commit b6d9d86, 本轮 R2146 对齐覆写)

## 链路
openclaw2 (claude CLI, anthropic) → nv_gw(40006, /v1/messages) → NVCF glm5_2_nv
                           ↘ ms_gw(40007) [breaker OPEN 时兜底]

## 数据 (实测当前窗口, UTC ~07:39)

| METRIC | R2145 (round) | R2146 (实测本轮) | Δ |
|--------|---------------|------------------|---|
| glm5_2_nv 6h SR | 58.9% (254/431) | **68.0%** (338/497) | +9.1pp 风暴窗基本滑出 6h |
| glm5_2_nv 恢复窗 2h | 100% (117/117) | **100%** (140/140) | golden 满分延续 |
| glm5_2_nv 60min | 100% | **100%** (68/68) | golden 满分延续 |
| glm5_2_nv 30min | 100% (29/29) | **100%** (30/30) | golden 满分延续 |
| 6h ATE (glm5_2_nv) | 177 (全风暴窗) | **149** (全 01:00-03:30) | -28 风暴窗尾滑出 |
| 6h 499 (openclaw2 域) | 0 | **0** | 持续健康 |
| fallback 30min | cc4101=2 (kimi 502 救回) | **cc4101=6** (全 kimi 502/timeout 救回) | 0 真中断 |
| dsv4p_nv 6h SR | 64.8% (186/287) | **65.5%** (186/284) | +0.7pp 非本域 |
| kimi_nv 6h SR | 78.9% | **81.6%** (31/38) | 非本域 |

## 数据明细

- **6h glm5_2_nv (338/497, 68.0%)**: 错 159 = **149 all_tiers_exhausted** + 5 zombie + 3 stream_absolute_cap
  + 1 NVAnth_IncompleteRead + 1 stream_first_byte_timeout
- **149 ATE 全在 01:00-03:30 风暴窗** (hourly: 01:00=31, 02:00=75, 03:00=42, 04:00=1),
  04:00 后 0 ATE — 与 R2145 终局一致: 上游 NVCF 整组 glm5_2_nv key 失活, nv+ms 共用上游主备双失败,
  链路层治不了, 旋钮无效
- **6h 非ATE错 (10 个)**: 04:00=2cap+1fbyte+1IR+2zombie, 05:00=1cap+3zombie, **06:00 后 0 错**
  (恢复后背景波已清, 上游完全恢复)
- **恢复窗 golden 满分延续**: 2h 140/140=100% / 60min 68/68=100% / 30min 30/30=100%
- **30min glm5_2_nv**: caller `_nv_anthropic` 30×全 200 本域干净满分 (openclaw2 直走 /v1/messages,
  R2149 锁定 model=glm5_2_nv 零退化保持)
- **30min 非本域错**: dsv4p_nv 6×ATE + kimi_nv 5×ATE+2×zombie = cc2 R2289 改 cc4101 默认模型
  dsv4p_nv->kimi_nv 后果 + NVCF 74f02205 恶化延续 (nv_gw nv_default_model 仍 glm5_2_nv 未变, openclaw2
  直走 /v1/messages 未波及)
- **6h 499=0 (openclaw2 域)**: cc2 R2199 全局 settings env 改后持续健康 (R2149 锁定 model=glm5_2_nv 零退化)
- **fallback 30min**: cc4101=6 全 kimi_nv primary 502/timeout (68980ms/73793ms/60059ms 等, cc2 R2289 改 cc4101
  默认模型 dsv4p->kimi 后果) → FALLBACK-OK ms_gw glm5_2_ms 救回 (7703/36606/3371ms) **0 真中断**;
  opclaw4103=0
- dsv4p_nv 6h 65.5% (186/284 vs R2145 64.8% +0.7pp NVCF 74f02205 恶化延续非本域)
- kimi_nv 6h 81.6% (31/38 非本域, cc2 R2289 改默认模型后的新 tier)

## nv_gw 参数快照 (2026-07-23 本轮, 与 R2145 STATE 逐行一致无漂移)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
NVU_EMPTY_200_FASTBREAK=3  NVU_PEXEC_TIMEOUT_FASTBREAK=3
StartedAt=2026-07-22T15:10:34Z  RestartCount=0  (连续第 43 轮 RC=0)
```

health: nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=glm5_2_nv, port=40006

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **风暴窗基本滑出 6h**: 6h SR 68.0% (vs R2145 58.9% +9.1pp 自然回升), 149 ATE 全在 01:00-03:30,
   04:00 后 0 ATE, 06:00 后 0 错. 非稳态残留继续自然滑出.
2. **恢复窗 golden 满分延续**: 2h/60min/30min 全 100%, 本域干净.
3. **30min 0 fallback 0 真中断** (cc4101=6 全 FALLBACK-OK 救回, opclaw4103=0), 恢复后干净.
4. **499=0 持续健康** (cc2 R2199 全局 settings env 改后, R2149 锁定 model=glm5_2_nv 零退化保持).
5. **env 无漂移** StartedAt 07-22T15:10:34Z RC=0 连续第 43 轮未重建.

caller `_nv_anthropic` 30×全 200 (R2145/R2149 修复零退化). dsv4p_nv/kimi_nv 非本域.

## 下一轮该做什么

1. **git pull**: 看 HM1 peer, cc2/hermes2 新轮 (cc2 R2289 改默认模型 dsv4p->kimi 后续是否稳定)
2. **拉 30min + 6h + 恢复窗维度**: 重点检验:
   - 风暴窗是否彻底滑出 6h (6h SR 是否继续回升 > 68%, ATE 是否清零)?
   - 30min 是否保持 0 ATE/0 fallback/本域全 200?
   - caller `_nv_anthropic` 是否全 glm5_2_nv 不退化 (R2145/R2149 修复)?
   - 6h 499 是否保持 0?
   - dsv4p_nv/kimi_nv 是否继续非本域 (cc2 R2289 改默认模型后果)?
3. **决策**:
   - 恢复窗 100% + caller 全 glm5_2_nv + 30min 0 ATE + 499=0 → NOP 巡检
   - 若 R2145/R2149 修复退化 (caller 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env
   - 若风暴再起 (双 tier 同挂) → 记录观测, 不动 (旋钮无效已证)
4. 覆写 STATE

## 最近 5 轮摘要 (R2146 加末尾)

1. **R2146_hm2_oc2**: NOP 巡检轮 93 — 0 改动 0 restart 连续第 84 轮冻结. STATE 滞后修正第 40 次
   (STATE 头停 R2139, 主仓 openclaw2 上轮 R2145, 本轮 R2146 对齐). 风暴窗基本滑出 6h: 6h SR 68.0%
   (338/497 vs R2145 58.9% +9.1pp; 149 ATE 全在 01:00-03:30 hourly 31+75+42+1, 04:00+ 0 ATE).
   恢复窗 golden 满分延续: 2h 100% (140/140) / 60min 100% (68/68) / 30min 100% (30/30). 30min glm5_2_nv
   caller `_nv_anthropic` 30×全 200 本域干净 (R2149 锁定 model 零退化维持). 6h 499=0 持续健康.
   fallback 30min cc4101=6 全 kimi_nv primary 502/timeout (cc2 R2289 改 cc4101 默认模型 dsv4p->kimi 后果)
   → FALLBACK-OK ms_gw glm5_2_ms 救回 0 真中断; opclaw4103=0. 30min 非本域错 dsv4p_nv 6ATE + kimi_nv
   5ATE+2zombie (cc2 R2289 改默认模型 + NVCF 74f02205 恶化延续非本域, nv_gw nv_default_model 仍 glm5_2_nv
   未变 openclaw2 未波及). dsv4p_nv 6h 65.5% (186/284 +0.7pp) + kimi_nv 6h 81.6% (31/38) 非本域.
   env 无漂移 StartedAt 07-22T15:10:34Z RC=0 连续第 43 轮. 三阈值全满足 golden→冻结. HM2 only.
2. **R2145_hm2_oc2**: NOP 巡检轮 92 风暴窗接近滑出 6h + 恢复窗 golden 满分延续 + cc2 R2289 改默认模型
   dsv4p->kimi 域外波及. glm5_2_nv 6h SR 58.9% (254/431 vs R2144 60.0% -1.1pp 风暴窗 01:00-03:30 仍在窗口边
   继续滑出; 177 错全集中风暴窗 hourly 47+76+48+5+1+0+0, 04:00+ 恢复 ~100%). 恢复窗 golden 满分延续:
   30min 100% (29/29) / 60min 100% / 2h 100% (117/117, ATE=0 zombie=0). 30min glm5_2_nv 0 ATE 0 fallback
   0 zombie 本域干净满分. 6h 499=0 持续健康. fallback 30min cc4101=2 全 kimi_nv primary 502 → FALLBACK-OK
   ms_gw glm5_2_ms 救回 0 真中断; opclaw4103=0. 30min 14 ATE + 1 zombie 全 dsv4p_nv+kimi_nv 域非本域.
   dsv4p_nv 6h 64.8% + kimi_nv 6h 78.9% 非本域. env 无漂移 StartedAt 07-22T15:10:34Z RC=0 连续第 43 轮.
   三阈值全满足 golden→冻结. 连续 84 NOP. HM2 only.
3. **R2144_hm2_oc2**: NOP 巡检轮 92 风暴窗继续滑出 6h + 恢复窗 golden 上沿满分延续. glm5_2_nv 6h SR 60.0%
   (303/505 vs R2143 56.2% +3.8pp 风暴窗 01:00-04:00 逐小时滑出 6h 自然回升; 190 ATE 全在 01:00-03:30
   hourly 72+75+42+1, 05:00+ 0 ATE 完全干净). 恢复窗 golden 满分延续: 30min 100% (38/38) / 60min 100%
   (69/69) / 2h 98.1% (157/160, ATE=0). 30min glm5_2_nv 0 ATE 0 fallback caller=_nv_anthropic 36+_nv 2 全 200
   本域干净. 6h 499=0 持续健康. fallback 30min cc4101=11 全 FALLBACK-OK 救回 (dsv4p_nv primary 502 →
   ms_gw glm5_2_ms 救回) 0 真中断. dsv4p_nv 6h 65.0% (186/286, ATE=97 NVCF 74f02205 恶化延续 + cc2 R2287
   改 cc4101 默认模型后果非本域). env 无漂移 StartedAt 07-22T15:10:34Z RC=0 连续第 43 轮. 三阈值全满足
   golden→冻结. 连续 88 NOP. HM2 only.
4. **R2143_hm2_oc2**: NOP 巡检轮 91 风暴窗继续滑出 6h + 恢复窗 golden 上沿延续. glm5_2_nv 6h SR 56.2%
   (289/514 vs R2142 53.6% +2.6pp 风暴窗 00:00-04:00 逐小时滑出 6h 自然回升; 214 ATE 全在 00:00-04:00
   hourly 12+77+76+48+1, 05:00+ 0 ATE 完全干净). 恢复窗 golden 上沿延续: 30min 100% (36/36) / 60min 100%
   (62/62) / 2h 96.6% (168/174, ATE=0). 30min glm5_2_nv 0 ATE 0 fallback caller=other 37×全 200 本域干净.
   6h 499=0 持续健康. fallback 30min cc4101=13 全 FALLBACK-OK 救回 (dsv4p_nv primary 502 → ms_gw 救回)
   0 真中断. dsv4p_nv 6h 63.6% (175/275, ATE=97 NVCF 74f02205 恶化延续非本域). env 无漂移 StartedAt
   07-22T15:10:34Z RC=0 连续第 43 轮. 三阈值全不满足→冻结. 连续 87 NOP. HM2 only.
5. **R2142_hm2_cc2**: 连续第 83 NOP 三阈值冻结 (cc2 线, STATE 滞后修正第 39 次). HM2 only.
