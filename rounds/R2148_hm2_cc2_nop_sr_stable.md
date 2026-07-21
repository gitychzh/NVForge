# R2148 (hm2_cc2) — NOP R173, 连续第 108 轮冻结

- **日期**: 2026-07-21 CST 11:09 / UTC 03:09
- **模式**: nv 直连 (cc4101→nv_gw), 指数退避+ms 双层方案半成品冻结 (NVU_GLM52_EXP_BACKOFF 不在 env=关, 从未 in-vivo 激活)
- **改动**: 0 改动, 0 restart (NOP 巡检轮)

## 数据 (30min 窗口, 起点 ~02:39 UTC, 当前 UTC 03:09)

**nv_gw 30min SR = 78/86 = 90.7%** ✅ 连续第 2 轮稳在 86-92% 次稳态带
(vs R2147 90.2% +0.5pp 持平, **散布期结束 + 新稳态期确认** (连续 2 轮 ≥90%);

**1min 桶完整轨迹 (UTC, 40min, 02:28→03:08)**:
- 02:28-04: 回稳带 (bad≤1/桶, 02:30/32/35/40 各 1 条散布 502)
- 02:41-49: 回稳延续 (02:42/50 各 1 条散布 502, 02:52 桶 1×502 单点)
- 02:53-03:04: 回稳带 (02:53 桶 5×200 全 OK, 02:57 单点 502)
- 03:05: 单点风暴簇 (bad=3 单桶, 非连续多桶)
- 03:06-08: 回稳收尾 (bad=0/桶)
- **全程 bad≤3/桶, 无连续多桶 bad≥5 风暴簇** ✅ (对比 R2120/R2121 风暴主峰 bad 5-10/桶 连续多桶, R2126 22:35-40 bad 5-6/桶)

**502 = 8** 全 NVCF 上游已知类, **0 新可配置类** ✅:
- all_tiers_exhausted ×6 (vs R2147 9 → 6, -3 持平低位)
- **zombie_empty_completion ×2** (vs R2147 0 → 2, +2 单点重现非簇) ⚠️ 观察
- 0 NVAnth_IncompleteRead (连续第 7 轮消失 R2132-2148, **持续确认非新可配类**) ✅

**tier 30min** (vs R2147 持平+低位):
- pexec_success ×70 (vs R2147 73, -3)
- pexec_conn_RemoteDisconnected ×12 (vs R2147 14, -2 回落)
- **pexec_429 ×4** (vs R2147 0 → 4, +4 抬头) ⚠️ 第4波 429 复发早期信号, 但 SR 未被拖低 + 0 真中断, 自愈性单点抬头非风暴
- 0 SSLEOFError (vs R2147 1, -1)
- 连接异常整体低位均 NVCF 已知类

## fallback / breaker / 兜底机制 (全未恶化)

- **fallback 8** FALLBACK-OK (vs R2147 7 → 8, +1):
  全 8 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (header/ttfb 75s < chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类).
  **0 条 120s 跑满类** (持平 R2147) ✅. req 样本: baef8e00 / ac1aad3f / c8b489bf / 13e16e7a / 1d3bf5df / 4c6e4d99 / 885aacf1 等 8 条.
  全 8 条被 ms_gw 兜住, **0 fallback 失败**.
- **0 真中断**: cc4101 `grep -cE "both failed|UPSTREAM-ERROR-SEEN"` 30min = **0** ✅ (用户诉求"可报错但不中断"仍达成).
- **breaker 未 OPEN**: cc4101 `PRIMARY-BREAKER-OPEN` 30min = **0**; nv_gw `NV-Anth-BREAKER-FAIL` 30min = **0** (state 未 OPEN, **连续第 40 轮**) ✅.
- **BUG-A 修复 (R1913) 生效确认**: 30min 内 `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **7 次** (vs R2147 7 持平, 持续复活触发中, 机制真实生效) ✅.
- **NV-CAP-RESET-MSFB = 7 条** (vs R2147 7 持平; R1818 bug7 已有 cap_origin reset 机制 execute→ms_fb path 正常触发, 全被 ms_fb 兜住 0 真中断) ✅.
- **abs_cap 30min 正常** (CAP-RESET 7 条, 与 breaker 段持平) ✅.

## 状态变化 (cc2 视角)

- nv_gw StartedAt 仍 **2026-07-21T01:44:55Z** (R2146 peer 重启后值, **连续第 2 轮核实未漂移**) ✅.
- cc4101 StartedAt 仍 2026-07-19T12:10:22Z (0 restart 未变).
- env 仍 peer R2108 改后值 (KEY60/TIER180/MIN_OUTBOUND10), **非 cc2 改**, cc2 0 改动 0 restart.
- /health = ok (passthrough, 5 keys, kimi_nv/dsv4p_nv/glm5_2_nv, default=dsv4p_nv).
- docker ps: nv_gw Up / cc4101 Up / ms_gw Up(热备在) / logs_db Up.

本轮需记录的变化 (vs R2147):
1. **30min SR 90.2%→90.7% +0.5pp 持平**, 连续第 2 轮稳在 86-92% 次稳态带 → **散布期结束 + 新稳态期确认** ✅.
2. 502 9→8 (-1 全 NVCF 已知类); 但 **zombie 0→2 (+2 单点重现)**, NVAnth_IncompleteRead 连续第 7 轮消失 (0).
3. tier **pexec_429 0→4 (+4 抬头)** 第4波 429 复发早期信号 (SR 未被拖低, 自愈性单点非风暴); pexec_conn_RemoteDisconnected 14→12 (-2 回落); pexec_success 73→70 (-3).
4. fallback 7→8 (+1) 全 75s SKIP-CIRCUIT 被兜, 0 真中断 0 失败 0 条 120s 跑满.
5. NV-CAP-RESET-MSFB 7→7 持平 / BUG-A SKIP-PEXEC2 7→7 持平.
6. breaker/abs_cap 全部未恶化, breaker 仍未 OPEN 连续第 40 轮, StartedAt 未漂移连续第 2 轮 (基线 01:44:55Z).

## 解冻判断 (连续第 23 轮论证)

**解冻不对症, 本轮仍 NOP.** 冻结理由仍成立 (半成品未经 in-vivo 验证 + 激活需同步 chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key 未实现 + 24h 观测窗口).

本轮 STATE 下一步判断线 8 条核对:
1. ✅ SR 90.7% ≥85% (连续第 2 轮, 散布期结束新稳态期确认)
2. ✅ NVAnth_IncompleteRead 连续第 7 轮消失 (持续确认非新可配类); ⚠️ zombie 重现 2 条单点 (非 NVAnth 同类, 非簇, 观察)
3. ✅ tier 连接异常低位 (RemoteDisconnected 12, SSLEOFError 0)
4. ⚠️ tier pexec_429 0→4 第4波 429 复发早期信号 (但 SR 未被拖低 + 0 真中断, 自愈性单点抬头非风暴)
5. ✅ 502 全 NVCF 已知类 (all_tiers_exhausted + zombie), 0 新可配置类
6. ✅ fallback 全 75s SKIP-CIRCUIT 被兜 0 失败, 0 条 120s 跑满
7. ✅ breaker 未 OPEN 连续第 40 轮; StartedAt 01:44:55Z 连续第 2 轮未漂移
8. ✅ NV-CAP-RESET-MSFB 7 持平未增多

**恶化判断线 (任一命中才考虑动)**: 30min SR 持续 <45% **或出现风暴簇** (连续多桶 bad≥5) 且 502 出新可配置类持续非单点, 或 fallback 失败, 或 breaker 真 OPEN 切流. **本轮均不满足** (SR 90.7% + 502 全 NVCF 已知类 + 0 真中断 + breaker 未 OPEN).

## 下一轮 (R2149) 重点

1. **30min SR 是否仍 ≥85%** (连续第 3 轮则新稳态期确认成立; 若回落至散布期 <85% 则散布期可能未真结束).
2. ⚠️ **tier pexec_429 是否从 +4 抬头演变为风暴簇** (本轮第4波复发早期信号; 若爆发为 tier 429 ×10+ 持续且 SR 被拖低 → 需观察是否进入第5波 NVCF 429 风暴期).
3. ⚠️ **zombie_empty_completion 是否从 +2 单点演变为持续/簇** (本轮重现 2 条; 若再现并爆发为簇需重新评估解冻判断线; 若下轮又消失则确认单点瞬态).
4. NVAnth_IncompleteRead 是否仍消失 (连续第 7 轮 → 第 8 轮持续确认).
5. tier 连接异常是否延续低位自愈.
6. fallback 是否仍全 75s SKIP-CIRCUIT 被兜; **关注 120s 跑满类是否再现增多** (本轮 0 条).
7. breaker 是否仍非真 OPEN (连续第 41 轮); nv_gw StartedAt 是否仍 01:44:55Z (连续第 3 轮).
8. NV-CAP-RESET-MSFB 是否持续增多 (本轮 7 持平; 若稳态期持续增多且 SR 被拖低 → 评估 chain_budget 是否过长耗 SR, 仍非解冻理由).

**若持续恶化才考虑动**: 任一判断线命中才重新评估解冻. 本轮不满足.

**轮号**: 下一轮 git pull 看最新, peer hm2_optimize_hm1 抢号很快; cc2 用 R2149 hm2_cc2 前缀避撞号.

HM2 only. R2148
