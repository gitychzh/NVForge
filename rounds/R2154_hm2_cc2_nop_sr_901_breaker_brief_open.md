# R2154 (hm2_cc2) — NOP R178, 连续第 113 轮冻结

> 日期: 2026-07-21 CST 12:13 / UTC 04:13
> 模式: nv 直连 (cc4101→nv_gw), 指数退避半成品仍冻结 (env NVU_GLM52_EXP_BACKOFF 关)
> 0 改动 0 restart, 纯巡检轮

## 数据 (30min 窗口, 窗口起点 ~03:43 UTC)

- **nv_gw 30min SR = 73/81 = 90.1%** (200:73 / 502:8)
  - vs R2153 82.6% **+7.5pp**, 重回 86-92% 次稳态带 ✅
  - vs R2151 89.7% 持平高位
- **1min 桶轨迹 (UTC, 40min, 03:36→04:15)**: 03:36-38 散布 → 03:39-40 两桶 bad=2 小簇 (与 R2153 同窗口尾部) → 03:41-48 回稳带 (03:46-47 连续 4×200 桶) → 03:49-55 散布 (bad 各 1 单点) → 03:56-04:00 连续 5 桶全 OK 回稳带 → 04:01-15 散布 (bad 各 1 单点, 04:11-12 回稳 5×200/4×200) → 04:15 收尾 bad=1. **全程 bad≤2/桶无连续多桶 bad≥5 风暴簇** ✅
- **502 = 8 全 NVCF 已知类 0 新可配置类** ✅:
  - all_tiers_exhausted×7 + NVAnth_IncompleteRead×1 (单点非簇, 与 R2153 同模式再现)
  - vs R2153 502=12 (11 all_tiers + 1 NVAnth), 本轮 -4, 改善
- **tier 30min**: pexec_success×64 + **pexec_429×25** (+16 vs R2153 的 9, 第4波 429 显著抬头) + pexec_conn_RemoteDisconnected×5 (+2 vs 3)
  - tier 层 SR = 64/94 = 68.1%, 但 nv_gw 最终 SR 90.1% — 说明 tier 层 429/conn 被 nv_gw 链路 retry+key rotation 兜住, **没传导到最终 502** ✅ (这是 nv_gw tier 机制设计正常工作的体现)
- **⚠️ nv_breaker 短暂真 OPEN (连续第 44 轮 0 后首次!)**: 11:40:21 CST CLOSED→OPEN, 11:40:42 `NV-MS-FB-BREAKER-OPEN` 直接跳过 nv 链 serve ms_gw (state=('OPEN',5,9)), 11:41:36 HALF_OPEN 探测, 11:42:51 CLOSED 自愈. **持续 ~2 分钟, 1 条 OPEN 切流被 ms_gw 兜住 0 真中断**. 这是 R1719 `nv_breaker` mid-stream 软挂 breaker 的设计行为, 非恶化 — 它在 nv 链上游连断压力下正确 OPEN 把请求甩给 ms_gw 兜底, 然后 HALF_OPEN 探测成功回 CLOSED, **40007 热备正确兜住**.
  - 另 1 条 `NV-ANTH-BREAKER-FAIL` (req=0cdc748f, 11:54 CST) = NVAnth_IncompleteRead 触发 mid-stream 软挂, state 仍 CLOSED 未推 OPEN (记 1 次 fail, 阈值未达).
- **NV-CAP-RESET-MSFB = 9 条** (vs R2153 13, -4), 全被 ms_fb 兜住 0 真中断 ✅
- **BUG-A (R1913) SKIP-PEXEC2 = 9 次** (vs R2153 12, -3), 持续复活触发, 机制真实生效 ✅
- **fallback = 7** FALLBACK-OK (vs R2153 9, -2): 全 7 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (header/ttfb 75s < chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类). **0 条 120s 跑满类** (持平 R2153) ✅
  - req 样本: 354d31c7 / 7a63a4dc / 6041a4be / d8375e28 / 89c7497c / 8089aa2c / b3599830
  - cc4101 `grep -cE "both failed|UPSTREAM-ERROR-SEEN"` 30min = **0** → 0 真中断确认 ✅
  - cc4101 PRIMARY-BREAKER-OPEN 30min = **0** ✅
- **nv_gw /health = ok** (passthrough, 5 keys, kimi_nv/dsv4p_nv/glm5_2_nv, default=dsv4p_nv)
- **nv_gw StartedAt = 2026-07-21T01:44:55Z** (连续第 7 轮核实未漂移) ✅
- **cc4101 StartedAt = 2026-07-19T12:10:22Z** (0 restart, 未变) ✅
- env 仍 peer R2108 改后值 (KEY60/TIER180/MIN_OUTBOUND10), **cc2 0 改动**, env 与 R2153 完全一致.

## 本轮核心变化 (vs R2153)

1. **30min SR 82.6% → 90.1% +7.5pp 重回 86-92% 次稳态带** ✅ (散布期小波动收尾, 非新波动期)
2. **502 12 → 8 (-4)**: 仍全 NVCF 已知类 (7 all_tiers + 1 NVAnth), 0 新可配类
3. **tier pexec_429 9 → 25 (+16) 显著抬头** 但仅 tier 层, 未传导到最终 502 (被 nv_gw retry+key rotation 兜住)
4. **⚠️ nv_breaker 短暂真 OPEN 首次** (连续 44 轮 0 后): 11:40 OPEN ~2min → 11:42 CLOSED 自愈, 1 条 OPEN 切流被 ms_gw 兜住 0 真中断. 设计行为非恶化.
5. fallback 9 → 7 (-2) 全 75s SKIP-CIRCUIT 被兜 0 真中断 0 失败 0 条 120s 跑满
6. NV-CAP-RESET-MSFB 13 → 9 / BUG-A SKIP-PEXEC2 12 → 9 均小幅回落
7. StartedAt 01:44:55Z 连续第 7 轮核实未漂移, env 未变

## 决策: 继续 NOP 冻结 (连续第 113 轮)

**依据**: 本轮数据全面向好, 不满足任何解冻触发线:
- SR 90.1% 回到次稳态带 (非 <45%)
- 无连续多桶 bad≥5 风暴簇 (1min 桶全程 bad≤2)
- 502 全 NVCF 已知类 0 新可配类
- 0 真中断 (both failed=0), 0 fallback 失败
- breaker 短暂 OPEN 是设计行为 (nv_breaker 在上游连断压力下正确切流→自愈), 非真持续性 OPEN
- abs_cap 30min 机制正常, BUG-A 真实生效

**tier 429 抬头 (25) 值得持续观察** 但当前未传导到最终 SR — 它说明 NVCF 上游 rate limit 第4波仍有余波, 但被 nv_gw tier retry 机制吸收. 解冻指数退避链路碰不到 429 类 (429 是 NVCF 侧 rate limit, 非 nv_gw 可调), 延长 chain_budget 反拖 SR.

**本轮 0 改动 0 restart, env 与 R2153 完全一致.**

## 下轮重点

1. 30min SR 是否稳在 86-92% 带 (本轮 90.1% 回带)
2. **⚠️ nv_breaker 是否再现短暂 OPEN** (本轮首次, 若频繁 OPEN 持续切流需评估是否 NVCF 上游进入新不稳定期)
3. tier pexec_429 是否仍高位 (本轮 25) 或回落; 是否开始传导到最终 502
4. NVAnth_IncompleteRead 是否仍单点非簇 (本轮 1) 或演变成簇
5. fallback 是否仍全 75s SKIP-CIRCUIT 0 失败; 120s 跑满类是否再现
6. 502 是否仍全 NVCF 已知类 0 新可配类
7. StartedAt 是否仍 01:44:55Z (连续第 8 轮核实)
8. breaker (cc4101 PRIMARY / nv_gw NV-ANTH) 是否仍非持续性 OPEN

HM2 only. 不碰 ms_gw, 不碰 HM1.
