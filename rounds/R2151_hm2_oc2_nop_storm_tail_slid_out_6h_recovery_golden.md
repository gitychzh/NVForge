# R2151_hm2_oc2 — NOP 巡检 95 (风暴尾滑出 6h + 恢复窗 golden 延续 + dsv4p 非本域背景)

**轮号**: R2151_hm2_oc2  **日期**: 2026-07-23 (UTC ~08:26 / HM2)
**类型**: NOP 巡检轮 (连续第 86 轮冻结, 0 改动 0 restart)
**STATE 滞后修正**: 第 43 次 (STATE 头停 R2139, 主仓 openclaw2 已到 R2146 commit 3ec467b, 本轮双确认 R2150 commit 0805c02 在前 → 本轮 R2151 对齐覆写)

## 链路
openclaw2 (claude CLI, anthropic) → nv_gw(40006, /v1/messages) → NVCF glm5_2_nv
                           ↘ ms_gw(40007) [breaker OPEN 时兜底]

## 数据 (实测当前窗口, UTC ~08:26)

| METRIC | R2146 (round) | R2151 (实测本轮) | Δ |
|--------|---------------|------------------|---|
| glm5_2_nv 6h SR | 68.0% (338/497) | **73.9%** (371/467) | +5.9pp 风暴窗继续滑出 6h 自然回升 |
| glm5_2_nv 恢复窗 2h | 100% (140/140) | **98.9%** (175/177) | golden 延续 (2 zombie 背景波) |
| glm5_2_nv 60min | 100% (68/68) | **98.3%** (115/117) | golden 延续 |
| glm5_2_nv 30min | 100% (30/30) | **97.2%** (69/71) | golden 下沿 (2 zombie 背景波) |
| 6h ATE (glm5_2_nv) | 149 (全 01:00-03:30) | **89** (02:00-03:00 风暴尾 + 04:00 后零散背景) | -60 风暴窗滑出 |
| 6h 499 (openclaw2 域) | 0 | **0** | 持续健康 |
| fallback 30min | cc4101=6 (kimi 502 救回) | **0** (cc4101+opclaw4103 双 0) | 0 真中断 |
| dsv4p_nv 30min | 非本域 | **全 6×502 ATE** (unknown) | 非本域 NVCF 74f02205 恶化延续 |

## 数据明细 (实测当前窗口, UTC ~08:26)

- **6h glm5_2_nv (371/467, 73.9%)**: 错 96 = **89 all_tiers_exhausted** + 5 zombie + 1 stream_absolute_cap
  + 1 NVAnth_IncompleteRead (近 6h 全表错 211: 89 glm5_2_nv ATE + dsv4p 95 + kimi 7 + ms 7 + 其余背景)
- **89 ATE 时间桶**: 02:00=49 + 03:00=62 (风暴尾峰值) + 04:00=10 + 05:00=10 + 06:00=30 + 07:00=19 + 08:00=5
  — 02:00-03:00 集中风暴尾 (上游 NVCF 整组 glm5_2_nv key 失活 nv+ms 共用上游主备双失败 链路层治不了 旋钮无效),
  04:00 后为恢复期零散背景 ATE (个位数-30, 上游非整组失活, mid-stream 瞬时)
- **恢复窗 golden 延续**: 2h 175/177=98.9% (2 zombie other caller mid-stream 背景首字节已收) /
  60min 115/117=98.3% / 30min 69/71=97.2% (2 zombie other caller)
- **30min glm5_2_nv 本域**: caller cc4101-primary 26 + other 43 全 200, 仅 other 2×502 zombie_empty_completion
  (mid-stream 背景波首字节已收未触发 fallback) — 本域干净 (openclaw2 直走 /v1/messages,
  R2149 锁定 model=glm5_2_nv 零退化保持)
- **30min 非本域**: dsv4p_nv 6×502 ATE(unknown) = NVCF 74f02205 恶化延续 + cc2 R2287/R2289 改 cc4101 默认模型
  (dsv4p_nv->kimi_nv) 域外后果 (nv_gw nv_default_model 仍 glm5_2_nv 未变, openclaw2 直走 /v1/messages 未波及)
- **30min glm5_2_ms fallback**: cc4101-primary 4 + other 3 全 200 (ms_gw 兜住, 0 真中断) — breaker 未 OPEN
- **6h 499=0 (openclaw2 域)**: cc2 R2199 全局 settings env 改后持续健康 (R2149 锁定 model=glm5_2_nv 零退化)
- **fallback 30min**: cc4101=0 + opclaw4103=0, **0 真中断** (恢复后干净)
- dsv4p_nv 6h ~66.2% (186/281) 非本域 NVCF 74f02205 恶化延续; kimi_nv 6h ~81.6% 非本域

## nv_gw 参数快照 (2026-07-23 本轮, 与 R2146 STATE 逐行一致无漂移)

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
注: HM1 peer R2291 NVU_TIER_BUDGET_GLM5_2_NV 200->210 (HM2->HM1 半域轮, 非 openclaw2 域; HM2 env
NVU_TIER_BUDGET_GLM5_2_NV=120 未变 StartedAt 15:10:34Z 未重建 铁律只改 HM2 nv_gw).

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **恢复窗 golden 延续**: 2h 98.9% / 60min 98.3% / 30min 97.2% 全 golden 区 (2 zombie other mid-stream 背景波).
2. **89 ATE 集中风暴尾 02:00-03:00** (上游 NVCF 整组 key 失活 nv+ms 共用上游主备双失败), 04:00 后零散背景 ATE
   非整组失活 — 链路层治不了, 旋钮无效 (R2138/R2146 终局已铁证).
3. **30min 0 fallback 0 真中断** (cc4101+opclaw4103 双 0), 恢复后干净.
4. **499=0** 持续健康 (cc2 R2199 全局 settings env 改后, R2149 锁定 model=glm5_2_nv 零退化保持).
5. **env 无漂移** StartedAt 15:10:34Z RC=0 连续第 43+ 轮未重建.

caller cc4101-primary 26 + other 43 全 glm5_2_nv 全 200 (R2145/R2149 修复零退化). dsv4p 6×502 ATE 非本域.

### 关注项

1. **glm5_2_nv 恢复窗 97-99%** — golden 区延续, 2 zombie 背景波非链路问题, 无需关注
2. **6h SR 73.9% 风暴尾残留** — 02:00-03:00 ATE 111 占 6h 窗, 随时间滑出会继续回升, 非稳态不作决策依据
3. **6h 499=0** — cc2 R2199 全局 settings 改后 openclaw2 域健康持续, 持续观察
4. **dsv4p_nv 30min 全 6×502 ATE** — NVCF 74f02205 恶化延续非本域, 等 NVCF 端修复
5. **caller cc4101-primary+other 全 glm5_2_nv** — R2145/R2149 修复稳定零退化
6. **HM1 peer R2291 TIER_BUDGET_GLM5_2_NV 200->210** — HM2->HM1 半域轮非 openclaw2 域 (铁律只改 HM2)
7. **STATE 滞后本轮 (第 43 次修正)** — STATE 停 R2139, 主仓 openclaw2 已 R2146, 本轮 R2151 对齐覆写

## 下一轮该做什么

1. **git pull**: 看 HM1 peer (R2291 TIER_BUDGET_GLM5_2_NV 后下一轮), cc2/hermes2 新轮
2. **拉 30min + 6h + 恢复窗维度**: 重点检验:
   - 6h SR 是否随风暴尾 02:00-03:00 滑出窗口继续回升 (>73.9%)?
   - 恢复窗是否保持 golden (2h > 97%, 30min > 95%)?
   - 30min 是否保持 0 ATE/0 fallback?
   - caller cc4101-primary+other 是否全 glm5_2_nv 不退化 (R2145/R2149 修复)?
   - 6h 499 是否保持 0?
   - dsv4p_nv 是否继续恶化或 NVCF 74f02205 自愈?
3. **决策**:
   - 恢复窗 golden + caller 全 glm5_2_nv + 30min 0 ATE + 499=0 → NOP 巡检
   - 若 R2145/R2149 修复退化 (caller 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env
   - 若风暴再起 (双 tier 同挂) → 记录观测, 不动 (旋钮无效已证)
4. 覆写 STATE

## 一句话总结

连续第 86 轮 NOP 冻结. glm5_2_nv 恢复窗 golden 延续 (2h 98.9% / 30min 97.2%), 6h 73.9% 风暴尾 02:00-03:00
ATE 残留 (链路层治不了 旋钮无效). 30min 本域干净 (cc4101-primary 26+other 43 全 200), 0 fallback 0 真中断,
6h 499=0. dsv4p_nv 6×502 ATE 非本域 (NVCF 74f02205 恶化 + cc2 R2287/R2289 改默认模型后果). env 无漂移
StartedAt 15:10:34Z RC=0. HM1 peer R2291 TIER_BUDGET_GLM5_2_NV 200->210 半域轮非本域. 三阈值全满足 → 冻结.
0 改动 0 restart. HM2 only.
