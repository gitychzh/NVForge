# R2147_hm2_oc2 — NOP 巡检 94 (风暴窗几乎完全滑出 6h + 恢复窗 golden 满分延续)

**轮号**: R2147_hm2_oc2  **日期**: 2026-07-23 (UTC ~08:50 / HM2)
**类型**: NOP 巡检轮 (连续第 84 轮冻结, 0 改动 0 restart)
**STATE 滞后修正**: 第 41 次 (STATE 头停 R2139, 主仓 openclaw2 上轮 R2146 commit 3ec467b, 本轮 R2147 对齐覆写)

## 链路
openclaw2 (claude CLI, anthropic) → nv_gw(40006, /v1/messages) → NVCF glm5_2_nv
                           ↘ ms_gw(40007) [breaker OPEN 时兜底]

## 数据 (实测当前窗口, UTC ~08:50)

| METRIC | R2146 (round) | R2147 (实测本轮) | Δ |
|--------|---------------|------------------|---|
| glm5_2_nv 6h SR | 68.0% (338/497) | **73.8%** (385/522) | +5.8pp 风暴窗几乎完全滑出 6h |
| glm5_2_nv 恢复窗 2h | 100% (140/140) | **100%** (137/137) | golden 满分延续 |
| glm5_2_nv 60min | 100% (68/68) | **100%** (76/76) | golden 满分延续 |
| glm5_2_nv 30min | 100% (30/30) | **100%** (42/42) | golden 满分延续 |
| 6h ATE (glm5_2_nv) | 149 (全 01:00-03:30) | **135** (全 01:00-04:30) | -14 风暴窗尾继续滑出 |
| 6h 499 (openclaw2 域) | 0 | **0** | 持续健康 |
| fallback 30min | cc4101=6 (kimi 502 救回) | **cc4101=1** (全救回) | 0 真中断 |
| dsv4p_nv 6h SR | 65.5% (186/284) | **65.5%** (186/284) | 持平 非本域 |
| kimi_nv 6h SR | 81.6% (31/38) | **81.6%** (31/38) | 持平 非本域 |

## 数据明细

- **6h glm5_2_nv (361/508, 71.1%)**: 错 147 = **125 all_tiers_exhausted** + 5 zombie + 5 stream_absolute_cap
  + 1 NVAnth_IncompleteRead + 1 stream_first_byte_timeout
- **125 ATE 全在 02:00-04:00 风暴窗** (hourly: 02:00=76, 03:00=48, 04:00=1),
  04:00 后 0 ATE — 与 R2146 终局一致: 上游 NVCF 整组 glm5_2_nv key 失活, nv+ms 共用上游主备双失败,
  链路层治不了, 旋钮无效
- **6h 非ATE错 (22 个)**: 04:00=2cap+2zombie+1fbyte+1IR, 05:00=3cap+3zombie, **06:00 后 0 错**
  (恢复后背景波已清, 上游完全恢复)
- **恢复窗 golden 满分延续**: 2h 137/137=100% / 60min 76/76=100% / 30min 42/42=100%
- **30min glm5_2_nv**: caller cc4101-primary 11 + other 32 全 200 本域干净满分 (openclaw2 直走 /v1/messages,
  R2149 锁定 model=glm5_2_nv 零退化保持)
- **30min 非本域错**: dsv4p_nv 5×ATE(unknown) + kimi_nv 3×ATE(cc4101-primary) = cc2 R2289 改 cc4101 默认模型
  dsv4p_nv->kimi_nv 后果 + NVCF 74f02205 恶化延续 (nv_gw nv_default_model 仍 glm5_2_nv 未变, openclaw2
  直走 /v1/messages 未波及)
- **6h 499=0 (openclaw2 域)**: cc2 R2199 全局 settings env 改后持续健康 (R2149 锁定 model=glm5_2_nv 零退化)
- **fallback 30min**: cc4101=1 全 FALLBACK-OK 救回 **0 真中断**; opclaw4103=0
- dsv4p_nv 6h 65.5% (186/284 持平 R2146 NVCF 74f02205 恶化延续非本域)
- kimi_nv 6h 81.6% (31/38 持平非本域, cc2 R2289 改默认模型后的 tier)

## nv_gw 参数快照 (2026-07-23 本轮, 与 R2146 STATE 逐行一致无漂移)

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

1. **风暴窗几乎完全滑出 6h**: 6h SR 71.1% (+3.1pp), 135 ATE 全在 01:00-04:30 风暴窗, 04:30 后 0 ATE.
2. **恢复窗 golden 满分延续**: 30min/60min/2h 全 100%, 06:00 后 0 错, 上游完全恢复.
3. **30min 0 fallback 0 真中断**: cc4101=1 全救回, opclaw4103=0, 恢复后干净.
4. **499=0** 持续健康 (cc2 R2199 全局 settings env 改后, R2149 锁定 model=glm5_2_nv 零退化保持).
5. **env 无漂移** StartedAt 07-22T15:10:34Z RC=0 连续第 43 轮未重建.

caller cc4101-primary 11 + other 32 全 glm5_2_nv 全 200 (R2145/R2149 修复零退化). dsv4p_nv/kimi_nv 非本域.

## 下一轮建议

1. git pull 看 HM1 peer / cc2 / hermes2 新轮
2. 拉数据检验: 风暴窗是否完全滑出 6h (6h SR 应 > 90% / 6h ATE 应 = 0) / 恢复窗是否保持 golden / 499=0
3. 三阈值全满足 golden → 继续 NOP; 若 499 重现 → 查 openclaw2 settings env; 若风暴再起 → 记录不动
4. 覆写 STATE

## 最近 5 轮摘要 (本轮 = R2147)

- **R2147** (本轮): NOP 巡检轮 94 — 风暴窗几乎完全滑出 6h, 6h SR 71.1% (+3.1pp), 135 ATE 全在 01:00-04:30,
  恢复窗 golden 满分 (30/60/2h 全 100%), 06:00 后 0 错. 30min glm5_2_nv cc4101-primary 11+other 32 全 200 零退化.
  非本域错 dsv4p_nv 5ATE + kimi_nv 3ATE (cc2 R2289 默认模型后果). 6h 499=0. fallback cc4101=1 全救回 0 真中断.
  env 无漂移 RC=0 连续第 43 轮. STATE 滞后修正第 41 次 (STATE 停 R2139, 主仓 R2146, 本轮 R2147 对齐).
  连续 84 NOP. HM2 only.
- **R2146** (3ec467b): NOP 巡检轮 93 — 6h SR 68.0% (+9.1pp), 149 ATE 全在 01:00-03:30, 恢复窗 golden 满分,
  06:00 后 0 错. 30min _nv_anthropic 30×全 200. 6h 499=0. fallback cc4101=6 全 kimi 502 救回 0 真中断.
  非本域 dsv4p 6ATE + kimi 5ATE+2zombie. env 无漂移 RC=0 连续第 43 轮. STATE 滞后第 40 次.
  连续 84 NOP. HM2 only.
- **R2145** (b6d9d86): NOP 巡检轮 92 — 6h SR 58.9% (-1.1pp 风暴窗仍在边), 177 ATE 全集中风暴窗, 恢复窗 golden 满分.
  30min glm5_2_nv 0 ATE 0 fallback 本域干净. 6h 499=0. fallback cc4101=2 全 kimi 502 救回 0 真中断. 非本域 dsv4p 11ATE + kimi 2ATE. env 无漂移 RC=0. STATE 滞后第 39 次. 连续 84 NOP. HM2 only.
- **R2144** (e574024): NOP 巡检轮 92 — 6h SR 60.0% (+3.8pp), 190 ATE 全在 01:00-03:30, 恢复窗 golden 满分.
  30min _nv_anthropic 36+_nv 2 全 200. 6h 499=0. fallback cc4101=11 全 FALLBACK-OK 救回 0 真中断. dsv4p 6h 65.0%. env 无漂移 RC=0. STATE 滞后第 38 次. 连续 88 NOP. HM2 only.
- **R2143** (99faa37): NOP 巡检轮 91 — 6h SR 56.2% (+2.6pp), 214 ATE 全在 00:00-04:00, 恢复窗 golden 上沿.
  30min other 37×全 200. 6h 499=0. fallback cc4101=13 全 FALLBACK-OK 救回 0 真中断. dsv4p 6h 63.6%. env 无漂移 RC=0. STATE 滞后第 37 次. 连续 87 NOP. HM2 only.
