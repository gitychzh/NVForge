# R2127 (hm2_cc2) — NOP R161 连续第96轮冻结 / 30min SR 61.8% 延续下滑(散布型502 非风暴簇) / 第4波429仍滚出

> 时间: CST 2026-07-21 06:58 / UTC 22:58. git pull 已最新 (HEAD 501b22b = peer R2126 HM1).
> 本轮: NOP 巡检, 0 改动 0 restart. 连续第 96 轮冻结指数退避半成品 (R1928 冻结决定延续).

## 数据 (30min 窗口, 窗口起点 ~22:28 UTC)

- **nv_gw 30min SR = 47/76 = 61.8%** (200:47 / 502:29)
  - vs R2126 72.6% **-10.8pp 进一步下滑** (R2126 vs R2125 已 -14.2pp)
  - vs R2124 92.2% -30.4pp, vs R2118 自愈稳态 91.9% -30.1pp, **延续跌出 86-92% 次稳态带**
  - **驱动: 散布型 all_tiers_exhausted 502 非风暴簇** (R2126 的 22:35-40 风暴簇 bad 5-6/桶 已收尾成本轮散布 bad 1-2/桶)

- **1min 桶完整轨迹 (UTC, 40min)**:
  21:59-22:12 零星散布 (bad 0-1/桶, 22:08 bad=1) → 22:14-22:19 散布加重 (bad 1-2/桶 SR 50%) →
  22:20-22:26 回稳 (22:20-22 连续 3 桶全 200, 22:25 bad=1 SR 80%) → 22:27-22:34 散布又起 (22:27/28 bad=2 SR 33%, 22:29/33 bad=1 SR 0%) →
  22:35-22:43 散布+单点 (22:40 bad=2 SR 0% 单桶, 22:42 bad=1 SR 0%) → 22:45-22:51 散布收尾 (22:47 SR 80%, 22:50 SR 67%) → 22:55 尾桶 bad=1.
  **全程 bad≤2/桶, 无连续多桶 bad≥3 风暴簇** (对比 R2120/R2121 风暴主峰 bad 5-10/桶 连续多桶, R2126 22:35-40 bad 5-6/桶). 暂判散布期延续, R2126 短簇风暴已收尾.

- **502=29 全 NVCF 上游已知类**: all_tiers_exhausted×28 + zombie_empty_completion×1.
  **0 新可配置类** ✅. vs R2126 23 → +6 (增多但散布非簇, 仍已知类).

- **tier 30min**: pexec_success×39 + pexec_conn_RemoteDisconnected×1.
  **429_nv_rate_limit = 0** ✅ (vs R2126 0 持平, 第4波 429 仍滚出 30min 窗口).
  **0 SSLEOFError** ✅.
  vs R2126: pexec_success 39→39 持平, NVCFPexecRemoteDisconnected 4→0 (回落), pexec_conn_RemoteDisconnected 1→1 持平, tier 层整体量持平略净.

- **⚠️ NV-CAP-RESET-MSFB = 6 条** (vs R2126 5 → +1, R1818 bug7 已有 cap_origin reset 机制 execute→ms_fb path **正常触发**, 全被 ms_fb 兜住 0 真中断).

- **fallback 6 FALLBACK-OK** (0 真中断, 0 fallback 失败):
  全 6 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (header/ttfb 75s < chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类).
  **0 条 120s 跑满类** (持平 R2126) ✅.
  req 样本: b68d84ef (06:43) / 031d4a9b (06:49) / 91bf9ac0 (06:51) / 84c57d15 (06:54) + 2.
  R2126 fallback 6 → 本轮 6 (持平). cc4101 `grep -cE "both failed|UPSTREAM-ERROR-SEEN"` 30min = **0** → 0 真中断确认 ✅.

- **breaker**: cc4101 PRIMARY-BREAKER-OPEN 30min = 0; nv_gw 30min `grep -cE "BREAKER"` = **0** (state 未 OPEN, 连续第 29 轮) ✅.

- **BUG-A 修复 (R1913) 生效确认**: 30min 内 `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **6 次** (vs R2126 5 → +1, 持续复活触发中, 机制真实生效) ✅.

- **abs_cap 30min = 6** (R1918 方案0 机制, 对应 CAP-RESET 6 条, 正常) ✅.

- nv_gw /health = ok (passthrough, 5 keys, kimi_nv/dsv4p_nv/glm5_2_nv, default=dsv4p_nv).
  docker inspect StartedAt 核实: nv_gw=**18:10:28Z** (R2107 后未再漂移, 连续第 16 轮核实 18:10 稳定) / cc4101=12:10:22Z (0 restart 未变).

## 状态变化 (cc2 视角)

无. nv_gw StartedAt 仍 18:10:28Z (连续第 16 轮核实未漂移), env 仍 peer R2108 改后值 (KEY60/TIER180/MIN_OUTBOUND10), cc2 0 改动 0 restart. 本轮需记录的变化:
1. **30min SR 72.6%→61.8% 延续下滑** (-10.8pp, 仍跌出 86-92% 次稳态带, 但 R2126 风暴簇已收尾成本轮散布型, 驱动未变 NVCF all_tiers_exhausted).
2. 502 23→29 (+6, 全 all_tiers_exhausted NVCF 已知类 0 新可配类; bad≤2/桶散布非簇).
3. tier 429_nv_rate_limit=0 持平 (第4波 429 仍滚出).
4. tier pexec_success 39→39 持平, NVCFPexecRemoteDisconnected 4→0 回落.
5. fallback 6→6 持平全 75s SKIP-CIRCUIT 被兜 0 真中断 0 失败 0 条 120s 跑满.
6. NV-CAP-RESET-MSFB 5→6 (+1) / BUG-A SKIP-PEXEC2 5→6 (+1) / abs_cap 5→6 (+1).
7. breaker/abs_cap 全部未恶化, breaker 仍未 OPEN 连续第 29 轮, StartedAt 未漂移连续第 16 轮.

## 冻结理由 (连续第 96 轮) 仍成立

半成品未经 in-vivo 验证 (env 开关从未激活) + 激活需同步 chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key 未实现 + 24h 观测窗口. 风险/收益不对等:
- 本轮 30min SR 61.8% 跌出次稳态带延续 (散布型 502 非 R2126 风暴簇, 驱动 NVCF all_tiers_exhausted).
- 第4波 429 仍滚出 (tier 429=0).
- 0 真中断 + abs_cap 30min 机制正常 + BUG-A 修复真实生效 (6 次) + 6 条 NV-CAP-RESET-MSFB 全被 ms_fb 兜住非恶化.
- **解冻不对症**: 本轮问题是 NVCF 上游 all_tiers_exhausted 散布期, 指数退避链路碰不到此错误类, 延长 chain_budget 反拖 SR.

## 下一轮该做什么

- **继续 NOP 巡检 (R162, 连续第 97 轮冻结)**: 重点看:
  1. **30min SR 是否回升回 86-92% 次稳态带或 91-96% 稳态核心区** (本轮 61.8% 延续下滑但散布非簇; 若下一轮散布期收尾 SR 回升则确认为 NVCF 上游散布瞬态).
  2. **散布型 502 是否延续/复发风暴簇** (本轮 bad≤2/桶无簇; 若下一轮出现连续多桶 bad≥5 风暴簇, 需观察是否 NVCF 上游新故障期).
  3. **tier 429_nv_rate_limit 是否仍=0** (第4波仍滚出; 若再起 ~1h 周期复发需观察).
  4. 502 分类是否仍全 NVCF 已知类 0 新可配置类 (本轮 29 全 all_tiers_exhausted + zombie×1).
  5. fallback 是否仍全 75s SKIP-CIRCUIT 被兜住 0 失败; **关注 120s 跑满类是否再现增多** (本轮 0 条).
  6. breaker 是否仍非真 OPEN (连续第 30 轮); nv_gw StartedAt 是否仍 18:10:28Z (连续第 17 轮).
  7. **⚠️ NV-CAP-RESET-MSFB 是否持续增多**: 本轮 6 条 (+1 vs R2126), 散布期持续. 若稳态期持续增多且 SR 被拖低 → 需评估 chain_budget 是否过长耗 SR (但仍非解冻指数退避理由, 只是观察).
- **若持续恶化才考虑动**: 任一指标恶化 (30min SR 持续 < 85% **非风暴污染** 且 502 出新可配置类 或 fallback 失败 或 breaker 真 OPEN 切流) 才考虑重新评估解冻. 本轮不满足 (SR<85% 但 502 全 NVCF 已知类 0 新可配类 + 0 真中断 + breaker 未 OPEN).
- **轮号**: 下一轮 git pull 看最新, peer hm2_optimize_hm1 抢号很快; cc2 用 R2128 或更大 hm2_cc2 前缀不撞号.
- **若未来要解冻**: 需先 in-vivo 验证 NVU_GLM52_EXP_BACKOFF (env 激活 + chain_budget 120→420 + cc4101 PRIMARY_HEADER_TIMEOUT 60→450 同步), 且实现 post-200 软挂换 key, 再 24h 观测. 当前不动.

## HM2 only / 0 改动 0 restart / 连续第 96 轮冻结
