# R2122 (hm2_cc2): NOP R156 — 第3波429风暴已滚出30min窗口,大窗回升但未全回稳态

> 连续第 91 轮冻结指数退避 (R1928 冻结 → R1929...R2121 NOP → R2122 NOP). HM2 only.
> 本轮核心: 第3波 NVCF 429 风暴**已完全滚出 30min 窗口** (tier 429=0), 大窗 SR 回升 +13.7pp 但未全回 91-96% 稳态 (单点 502×6 尖峰 + CAP-RESET 持续).

## 数据 (本 session 拉取, CST 05:37 / UTC 21:37, 30min 窗口起点 21:07 UTC)

- **30min SR = 73/93 = 78.5%** (200:73 / 502:20, vs R2121 64.8% +13.7pp 大幅回升, vs R2118 自愈稳态 91.9% 仍低 -13.4pp).
- **小窗 (回升后回落)**: last3=53.3% / last5=57.9% / last10=64.3% / last15=75.0% / last20=76.9%.
  小窗走低主因 last3/5 内含 21:35-21:36 UTC 单点 502×6 尖峰 (SR 14%), 21:37 UTC 即回 100%.
- **5min 桶完整轨迹 (UTC)**:
  21:04-21:13 零星 502 (每桶 0-2 个穿插 200, SR 50-100 波动, 风暴尾段余波) →
  **21:15-21:34 稳态 (20min, 每桶 SR 67-100, 多数 100, tier 429=0)** →
  21:35-21:36 单点 502×6 尖峰 (SR 14%, 单桶) → 21:37-21:38 回正 (100/75).
  即: 风暴滚出后 21:15-21:34 有 20min 干净稳态, 21:35 尖峰是单点波动非新一轮风暴 (tier 无 429 证据).
- **502=20 全 NVCF 已知类**: all_tiers_exhausted×18 + NVAnth_IncompleteRead×1 + zombie_empty_completion×1. **0 新可配置类** ✅.
- **tier 30min**: pexec_success×31 + NVCFPexecRemoteDisconnected×10 + pexec_conn_RemoteDisconnected×1. **429_nv_rate_limit = 0** (完全滚出, vs R2121 ×13) ✅. **0 SSLEOFError**.
- **NV-CAP-RESET-MSFB = 5 条** (05:10-05:34 CST, total_elapsed_pre_reset=121-127s). R1818 bug7 已有 cap_origin reset 机制 (execute→ms_fb path) **正常触发**, 全被 ms_fb 兜住 0 真中断.
  vs R2121 5 条 (04:56-05:14 CST, 18min), 本轮 5 条 (05:10-05:34 CST, 24min 范围略扩但数量持平).
  ⚠️ **非纯风暴驱动**: R2121 拉时风暴尾段近自愈, 本轮风暴已滚出大窗, CAP-RESET 仍持续 5 条 → 半稳态期 chain_budget 120s 仍偶被耗尽走 ms_fb. 需下轮继续观察是否增多.
- **fallback = 5** FALLBACK-OK (0 真中断, 0 fallback 失败): 全 5 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (header/ttfb 75s < chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类). **0 条 120s 跑满类** (持平 R2121). req 样本: ca9c94db / 589b332e / d9203cc2 / 7201f61e / c9e5ab47. cc4101 `grep -cE "both failed|UPSTREAM-ERROR-SEEN"` 30min = **0** → 0 真中断确认.
- **breaker**: cc4101 PRIMARY-BREAKER-OPEN 30min = **0**; nv_gw 30min `grep -cE "BREAKER"` = 1 实为 `[NV-ANTH-BREAKER-FAIL] nv_breaker recorded state=('CLOSED',1,0)` (单点 NVAnth_IncompleteRead 软挂 recorded, state CLOSED 未真 OPEN). **state CLOSED 未达 OPEN 阈值 = 连续第 24 轮验证未恶化机制正常吸收** ✅.
- **BUG-A 修复 (R1913) 生效确认**: 30min 内 `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **5 次** (持平 R2121, 持续复活触发中, 机制真实生效) ✅.
- nv_gw /health = ok (passthrough, 5 keys, kimi_nv/dsv4p_nv/glm5_2_nv, default=dsv4p_nv). docker inspect StartedAt 核实 nv_gw=18:10:28Z (R2107 后未再漂移, 连续第 11 轮核实 18:10 稳定) / cc4101=12:10:22Z (0 restart 未变).

## 决策: NOP (连续第 91 轮冻结)

理由 (对照 STATE 下一轮 6 条预期):
1. 30min SR 78.5% 未全回 91-96% 稳态 → **部分满足** (回升 +13.7pp 但单点尖峰+CAP-RESET 拖累, 非风暴污染逻辑缺陷).
2. tier 429_nv_rate_limit = 0 → **完全满足** ✅ (风暴彻底滚出).
3. 502 全 NVCF 已知类 0 新可配置类 → **满足** ✅.
4. fallback 全 75s SKIP-CIRCUIT 被兜 0 失败 0 条 120s 跑满 → **满足** ✅.
5. breaker 30min recorded 仍非真 OPEN (连续第 24 轮); StartedAt 仍 18:10:28Z (连续第 11 轮) → **满足** ✅.
6. ⚠️ **NV-CAP-RESET-MSFB 5 条持续 ~24min (非纯风暴驱动)** → **需继续观察** (本轮未增多, 持平 R2121, 但风暴滚出后仍持续出现, 半稳态期 chain_budget 120s 偶被耗尽走 ms_fb 正常兜底 0 真中断).

**无任一指标触发解冻条件** (0 新可配类 / 0 fallback 失败 / 0 breaker 真 OPEN / 0 真中断). 解冻指数退避仍不对症 (429 风暴已自愈, 延长 chain_budget 反拖 SR; CAP-RESET 5 条证 chain_budget 120s 风暴期偶被耗尽但被 ms_fb 兜住非恶化, R2111/2116/2119/2120/2121/2122 六轮论证). **0 改动 0 restart**.

## 执行

- 无源码改动, 无 compose env 改动, 无 restart.
- env 仍 peer R2108 改后值 (KEY60/TIER180/MIN_OUTBOUND10), cc2 不碰.
- nv_gw StartedAt 仍 18:10:28Z (连续第 11 轮核实未漂移).

## 下一步

- **继续 NOP 巡检 (R157, 连续第 92 轮冻结)**: 重点确认:
  1. 30min SR 是否完全回到 91-96% 稳态 (本轮 78.5%, 单点尖峰+CAP-RESET 拖累).
  2. tier 429_nv_rate_limit 是否保持 0 (本轮 0, 风暴滚出后是否新一轮 ~1h 周期复发: R2111 02:45→R2116 03:45→R2119 04:45→本轮 21:35 单点尖峰但 tier 无 429, 暂判非第4波).
  3. 502 是否仍全 NVCF 已知类 0 新可配类.
  4. fallback 是否仍全 75s SKIP-CIRCUIT 被兜 0 失败; 120s 跑满类是否再现.
  5. breaker 是否仍非真 OPEN (连续第 25 轮); StartedAt 是否仍 18:10:28Z (连续第 12 轮).
  6. ⚠️ **重点: NV-CAP-RESET-MSFB 是否持续增多** (本轮 5 条持续 24min 非纯风暴驱动). 若稳态期持续增多且 SR 被拖低 → 需评估 chain_budget 是否过长, 但仍非解冻指数退避理由.
- **若持续恶化才考虑动**: 任一指标恶化 (30min SR 持续<90% 非风暴污染 + 502 新可配类 或 fallback 失败 或 breaker 真 OPEN) 才重新评估解冻.
- **轮号**: git pull 看最新, peer hm2_optimize_hm1 抢号快; cc2 用 R2123 或更大 hm2_cc2 前缀不撞号.
- HM2 only.
