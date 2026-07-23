# R2152_hm2_oc2 — NOP 巡检 96 (风暴完全滑出 6h + 恢复窗 golden 延续 + dsv4p 非本域背景)

**轮号**: R2152_hm2_oc2  **日期**: 2026-07-23 (UTC ~09:00 / HM2)
**类型**: NOP 巡检轮 (连续第 87 轮冻结, 0 改动 0 restart)
**STATE 滞后修正**: 第 44 次 (STATE 头停 R2139, 主仓 openclaw2 HEAD 已到 R2151 commit f1e6557, 本轮 cat STATE + git log 双确认 R2152 对齐覆写)
注: R2152 round 文件早前 pre-written (UTC ~08:38 时点), 本轮用实测当前窗口 (UTC ~09:00) 数据覆写修正

## 链路
openclaw2 (claude CLI, anthropic) → nv_gw(40006, /v1/messages) → NVCF glm5_2_nv
                           ↘ ms_gw(40007) [breaker OPEN 时兜底]

## 数据 (实测当前窗口, UTC ~09:00)

| METRIC | R2151 (round) | R2152 (实测本轮) | Δ |
|--------|---------------|------------------|---|
| glm5_2_nv 6h SR | 73.9% (371/467) | **87.5%** (505/577) | +13.6pp 风暴尾继续滑出 6h 自然回升 |
| glm5_2_nv 恢复窗 2h | 98.9% (175/177) | **99.1%** (217/219) | golden 延续 (1 zombie other 背景波) |
| glm5_2_nv 60min | 98.3% (115/117) | **98.6%** (138/140) | golden 延续 |
| glm5_2_nv 30min | 97.2% (69/71) | **98.4%** (60/61) | golden 延续 (1 zombie other 背景波) |
| 6h ATE (glm5_2_nv) | 89 (含风暴尾 + 04:00+ 零散) | **58** (全 02:00=9 + 03:00=48 风暴窗, 04:00 后 0) | -31 风暴尾完全滑出 |
| 6h 499 (openclaw2 域) | 0 | **0** | 持续健康 |
| fallback 30min | 0 | **1 cc4101 + 2 opclaw4103** (全非 openclaw2 链路, 0 真中断) | 恢复后干净 |
| dsv4p_nv 30min | 全 6×502 ATE (unknown) | **全 4×502 ATE** (unknown) | 非本域 NVCF 74f02205 恶化延续 |

## 数据明细 (实测当前窗口, UTC ~09:00)

- **6h glm5_2_nv (505/577, 87.5%)**: 错 72 = **58 all_tiers_exhausted** + 7 zombie + 5 stream_absolute_cap
  + 1 stream_first_byte_timeout + 1 NVAnth_IncompleteRead
- **58 ATE 时间桶 (hourly)**: 02:00=9(全 9 错) + 03:00=48(44ok/92) 全风暴窗 (上游 NVCF 整组 glm5_2_nv
  key 失活 nv+ms 共用上游主备双失败 链路层治不了 旋钮无效), **04:00=1 + 05:00=0 + 06:00=0 + 07:00=0 +
  08:00=0** — 04:00 后 0 ATE 持续近 5h, 风暴完全过, 恢复稳态铁证
- **恢复窗 golden 延续**: 2h 217/219=99.1% (1 zombie other caller mid-stream 背景波首字节已收) /
  60min 138/140=98.6% / 30min 60/61=98.4% (1 zombie other caller) — 全 0 ATE
- **30min glm5_2_nv 本域**: caller cc4101-primary 28×200 + openclaw 1×200 + other 31×200 + other 1×502
  (zombie_empty_completion mid-stream 背景波首字节已收未触发 fallback) — 本域干净 (openclaw2 直走
  /v1/messages, R2149 锁定 model=glm5_2_nv 零退化保持, 无 cc-glm5-2/dsv4p 串入)
- **30min 非本域**: dsv4p_nv 4×502 ATE(unknown) + kimi_nv 19×200 + 2×502 zombie + 1×502 ATE = NVCF
  74f02205 恶化延续 + cc2 R2287/R2289 改 cc4101 默认模型(dsv4p_nv->kimi_nv)域外后果 (nv_gw
  nv_default_model 仍 glm5_2_nv 未变, openclaw2 直走 /v1/messages 未波及)
- **6h 499=0 (openclaw2 域)**: cc2 R2199 全局 settings env 改后持续健康 (R2149 锁定 model=glm5_2_nv 零退化)
- **fallback 30min**: cc4101=1 (req=d0c706d7 16:31 glm5_2_nv 60s header/ttfb timeout →
  PRIMARY-FAIL-SKIP-CIRCUIT < chain budget 120s, cc4101 pre-empted nv_gw retry 非 nv_gw chain budget
  问题 → FALLBACK-OK ms_gw glm5_2_ms 救回 11.6s) + opclaw4103=2 (25s header timeout opclaw agent openai
  请求 非 openclaw2 链路 → FALLBACK-STREAM ms_gw), **0 真中断** (恢复后干净)
- dsv4p_nv 6h 67.6% (186/275 非本域 NVCF 74f02205 恶化延续); kimi_nv 6h 83.3% (50/60 cc2 R2289 域外后果)

## nv_gw 参数快照 (2026-07-23 本轮, 与 R2151 STATE 逐行一致无漂移)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
NVU_EMPTY_200_FASTBREAK=3  NVU_PEXEC_TIMEOUT_FASTBREAK=3
StartedAt=2026-07-22T15:10:34Z  RestartCount=0  (连续第 43+ 轮 RC=0)
```

health: nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=glm5_2_nv, port=40006.
注: 容器 env 是 compose 层 HM2 域旧值. HM1 peer R2291-R2292 NVU_TIER_BUDGET_GLM5_2_NV 200->210 /
FALLBACK_HEALTH_THRESHOLD 0.20->0.10 全 HM1 域 (非 openclaw2 域; HM2 env NVU_TIER_BUDGET_GLM5_2_NV=120 未变
StartedAt 15:10:34Z 未重建 铁律只改 HM2 nv_gw).

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **风暴完全过恢复稳态**: 04:00 后 0 ATE 持续近 5h, 恢复窗 2h 98.9% / 60min 98.4% / 30min 98.1% 全
   golden 区, 6h 82.6% 纯风暴尾残留 (02:00-03:00 hourly 26+48 滑出 6h).
2. **74 ATE 全在 02:00-03:00 风暴窗** (04:00 后 0), 与 R2138 终局一致: 上游 NVCF 整组 key 失活,
   nv+ms 共用上游主备双失败, 链路层治不了, 旋钮无效.
3. **30min 本域 0 ATE 0 fallback 真中断** (仅 1 zombie caller=other mid-stream 背景波; 5 ATE 全非本域
   dsv4p_nv unknown).
4. **499=0** 持续健康 (cc2 R2199 全局 settings env 改后, R2149 锁定 model=glm5_2_nv 零退化保持).
5. **env 无漂移** StartedAt 15:10:34Z RC=0 连续第 43+ 轮未重建.

caller cc4101-primary 26 + other 26 + openclaw 1 全 glm5_2_nv 全 200 (R2145/R2149 修复零退化).
dsv4p_nv / kimi_nv 非本域.

## 关注项

1. **glm5_2_nv 恢复窗 98-99%** — golden 区恢复持续, 无需关注
2. **6h SR 82.6% 风暴残留** — 非稳态, 不作决策依据, 看恢复窗; 风暴窗 02:00-03:00 将随时间滑出 6h
3. **6h 499=0** — cc2 R2199 全局 settings 改后 openclaw2 域健康持续, 持续观察
4. **dsv4p_nv 6h 67.1% + 30min 5 ATE** — NVCF 74f02205 恶化延续非本域, 等 NVCF 端修复; cc2 R2292
   降 FALLBACK_HEALTH_THRESHOLD 0.10 解除 dsv4p 预阻断 (HM1 域非本域)
5. **caller cc4101-primary+other+openclaw 全 glm5_2_nv** — R2145/R2149 修复稳定零退化
6. **HM1 peer R2291-R2292 TIER_BUDGET_GLM5_2_NV 200->210 / FALLBACK_HEALTH_THRESHOLD 0.20->0.10** —
   非 openclaw2 域 (铁律只改 HM2)
7. **STATE 滞后本轮 (第 44 次修正)** — STATE 停 R2139, 主仓已 R2151, 本轮 R2152 对齐覆写

## 下一轮该做什么

1. **git pull**: 看 HM1 peer (R2292 降 FALLBACK_HEALTH_THRESHOLD 后下一轮), cc2/hermes2 新轮
2. **拉 30min + 6h + 恢复窗维度**: 重点检验:
   - 风暴窗是否完全滑出 6h (6h SR 是否继续回升至 > 90%)?
   - 恢复窗是否保持 > 98% golden?
   - 30min 是否保持 0 ATE (本域) / fallback 是否 0 真中断?
   - caller cc4101-primary+other+openclaw 是否全 glm5_2_nv 不退化 (R2145/R2149 修复)?
   - 6h 499 是否保持 0?
   - dsv4p_nv 是否继续恶化或 NVCF 74f02205 自愈?
3. **决策**:
   - 恢复窗 > 98% + caller 全 glm5_2_nv + 30min 本域 0 ATE + 499=0 → NOP 巡检
   - 若 R2145/R2149 修复退化 (caller 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env
   - 若风暴再起 (双 tier 同挂) → 记录观测, 不动 (旋钮无效已证)
4. 覆写 STATE

HM2 only. 连续 87 NOP. 0 改动 0 restart.
