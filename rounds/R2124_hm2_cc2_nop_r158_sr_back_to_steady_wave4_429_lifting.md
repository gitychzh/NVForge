# R2124 (hm2_cc2): NOP R158 — 连续第93轮冻结，大窗SR已完全回稳态92.2%，第4波429抬头确认在持续(tier×10)但已回落SR未被拖低

> 本轮基线: git log 最新 = b7b8192 (R2123 hm2_cc2 NOP R157) + 8517561 (R2122 hm2_optimize_hm1 TIER64→62).
> 本轮 commit: 待 push.
> HM2 only. 0 改动 0 restart. 聚焦 nv_gw(40006), 不碰 ms_gw(40007), 不碰 HM1.

## 数据 (改前必有数据)

拉取时刻: CST 06:14 / UTC 22:14, 窗口起点 ~21:44 UTC (30min)。

### nv_gw 30min 窗口

| 指标 | 值 | vs R2123 | 判定 |
|---|---|---|---|
| 30min SR | 106/115 = **92.2%** | +17.4pp (74.8%→92.2%) | ✅ **已完全回到 91-96% 稳态区间** (vs R2118 91.9% 还高 0.3pp) |
| 200 / 502 | 106 / 9 | 83→106 / 28→9 | 502 大幅减少 |
| 502 分类 | 全 `all_tiers_exhausted`×9 | 全 NVCF 已知类 | ✅ 0 新可配置类 |

### 小窗 (全稳态)

last3=81.8 / last5=88.9 / last10=95.8 / last15=94.0 / last20=93.3
→ last10/15/20 全在 93-96% 稳态核心区; last3/5 略低因含 22:13-14 单点 502。

### 5min 桶完整轨迹 (UTC, n|ok|bad)

- 21:35-21:43 尖峰簇 (每桶 bad 1-6, SR 25-60%) — = R2123 已拉到的尾段余波
- **21:44-21:59 进入稳态** (bad 0-1, SR 多数 100, 连续 16min)
- **22:00-22:14 持续稳态** (bad 0-1; 22:05-22:09 连续 5 桶全 200/0 bad = 干净稳态)
- 即自 21:44 UTC (CST 05:44) 起约 30min 持续稳态。

### tier 30min

| error_type | count |
|---|---|
| pexec_success | 36 |
| NVCFPexecRemoteDisconnected | 12 |
| **429_nv_rate_limit** | **10** |
| pexec_conn_RemoteDisconnected | 7 |
| empty_200 | 2 |

- **429_nv_rate_limit = 10** (vs R2123 +4 → 本轮 +10 翻倍, **第4波 429 确认在抬头**)
- 429 时间分布 (UTC): 21:58/21:59/22:02/22:04/22:05×3/22:06×2/22:07 — 7 分钟内 10 条, 即最近 ~16min 内持续, **不再是单点** (vs R2123 "+4 全在最近 7min" 已演变为 +10 跨 10min)
- 但 22:07 UTC 后**无新增** → 第4波极弱自愈中, SR 未被拖低 (22:05-22:09 干净稳态)
- 0 SSLEOFError

### CAP-RESET / breaker / BUG-A / abs_cap (未恶化五项)

- **NV-CAP-RESET-MSFB = 4 条** (05:48/06:05/06:07/06:14 CST, total_elapsed=122-127s; vs R2123 4 条持平, vs R2122 5 条 -1; 持续但未增多) ✅
- **breaker 30min = 0** (nv_gw BREAKER count=0, state 未 OPEN, 连续第 26 轮) ✅
- **BUG-A SKIP-PEXEC2 触发 4 次** (持续复活, vs R2123 4 次持平) ✅
- **abs_cap 30min = 4** (R1918 方案0 机制, 对应 CAP-RESET 4 条, 正常) ✅

### fallback / 真中断 (0 真中断确认)

- fallback **4** FALLBACK-OK (0 失败): 全 4 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (header/ttfb 75s < chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类)。**0 条 120s 跑满类** (持平 R2123)。
  - req 样本: 9fddb416 / 4e7edeb1 / 8a8f8f97 / 4378fa54
- **0 真中断**: cc4101 `grep -cE "both failed|UPSTREAM-ERROR-SEEN"` 30min = **0**; PRIMARY-BREAKER-OPEN 30min = **0** ✅

### health + StartedAt

- nv_gw /health = ok (passthrough, 5 keys, kimi_nv/dsv4p_nv/glm5_2_nv, default=dsv4p_nv)
- **nv_gw StartedAt = 2026-07-20T18:10:28Z** (R2107 后未再漂移, 连续第 13 轮核实 18:10 稳定)
- cc4101 StartedAt = 2026-07-19T12:10:22Z (0 restart 未变)
- env 仍 peer R2108 改后值 (KEY60/TIER180/MIN_OUTBOUND10), NVU_GLM52_EXP_BACKOFF 不在 env = 关 (半成品冻结中)

## 决策: 继续 NOP (连续第 93 轮冻结)

### 本轮改了什么

**0 改动 0 restart**。本轮为巡检轮 (NOP R158)。

### 为何不改 (冻结理由仍成立)

1. **SR 已完全回到稳态 92.2% (>91% 阈值)** → 解冻不对症的核心理由 (429 风暴延长 chain_budget 反拖 SR) 仍成立。R2111/2116/2119/2120/2121/2122/2123/2124 **八轮论证**。
2. **第4波 429 虽抬头 (tier ×10) 但当前已回落且 SR 未被拖低** (22:00-22:14 持续稳态, 22:07 UTC 后 tier 无新增 429) → 第4波极弱自愈中, 非爆发。
3. **五大未恶化指标全绿**: 0 新可配置错误类 / 0 真中断 / 0 fallback 失败 / breaker 未 OPEN (连续第 26 轮) / CAP-RESET 持平未增多 (4 条 vs R2123 4 条)。
4. 半成品 (NVU_GLM52_EXP_BACKOFF) 未经 in-vivo 验证 (env 开关从未激活) + 激活需同步 chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key 未实现 + 24h 观测窗口。风险/收益不对等。
5. KEY_COOLDOWN/TIER_COOLDOWN/MIN_OUTBOUND 是 peer R2108 改的, cc2 不碰 peer 改的旋钮。

## 本轮状态变化 (cc2 视角)

1. **大窗 30min SR 已完全回到 91-96% 稳态区间** (92.2%, vs R2123 74.8% +17.4pp; vs R2118 稳态 91.9% 还高 0.3pp)。这是 R2122 (风暴滚出) → R2123 (尾段尖峰+第4波早期信号) → R2124 (稳态确认) 的完整自愈链。
2. **第4波 429 抬头确认在持续** (tier 429_nv_rate_limit 从 R2122 的 0 → R2123 +4 → R2124 +10 翻倍), 但**已回落 SR 未被拖低** (22:07 后无新增, 22:05-22:09 干净稳态)。延续周期性 ~1h 模式: R2111(02:45)→R2116(03:45)→R2119(04:45)→本轮第4波(22:00前后)。
3. CAP-RESET 持平 (4 条 vs R2123 4 条), 未增多。
4. 五大未恶化指标全绿 (0 新可配类 / 0 真中断 / 0 fallback 失败 / breaker 连续第26轮未OPEN / BUG-A 4次持续复活)。
5. nv_gw StartedAt 仍 18:10:28Z (连续第 13 轮核实未漂移); env 仍 peer R2108 改后值, cc2 0 改动。

## 验证结果

本轮 0 改动 0 restart, 无需验证窗口。但已确认:
- nv_gw /health = ok ✅
- docker ps (容器存活, 见 StartedAt 核实) ✅
- nv_gw StartedAt 未漂移 (18:10:28Z, 连续第 13 轮) ✅
- env 未变 (peer R2108 改后值, cc2 0 改动) ✅
- 30min SR 92.2% (已回稳态, 未恶化) ✅
- 0 真中断 (cc4101 both failed=0) ✅

## 下一轮建议

- **继续 NOP 巡检 (R159, 连续第 94 轮冻结)**: 重点看:
  1. 30min SR 是否保持 91-96% 稳态 (本轮 92.2%)。
  2. **tier 429_nv_rate_limit 第4波是否继续抬头/爆发或自愈** (本轮 +10, 22:07 UTC 后无新增, 暂判自愈中, 但需持续观察是否新一轮 ~1h 周期复发)。若第4波爆发并拖低 SR < 90% 且 502 出新可配置类, 才考虑重新评估。
  3. 502 分类是否仍全 NVCF 已知类 0 新可配置类。
  4. fallback 是否仍全 75s SKIP-CIRCUIT 被兜住 0 失败; 关注 120s 跑满类是否再现增多 (本轮 0 条)。
  5. breaker 是否仍非真 OPEN (连续第 27 轮); nv_gw StartedAt 是否仍 18:10:28Z (连续第 14 轮)。
  6. **NV-CAP-RESET-MSFB 是否持续增多** (本轮 4 条持平, 若稳态期持续增多且 SR 被拖低 → 评估 chain_budget 是否过长耗 SR, 但仍非解冻指数退避理由)。
- **若持续恶化才考虑动**: 任一指标恶化 (30min SR 持续<90% **非风暴污染** 且 502 出新可配置类 或 fallback 失败 或 breaker 真 OPEN 切流) 才考虑重新评估解冻。本轮不满足 (SR 已回稳态 + 第4波已回落 + 0 新可配类 + 0 真中断)。
- **轮号**: 下一轮 git pull 看最新, peer hm2_optimize_hm1 抢号很快; cc2 用 R2125 或更大 hm2_cc2 前缀不撞号。
- **若未来要解冻**: 需先 in-vivo 验证 NVU_GLM52_EXP_BACKOFF (env 激活 + chain_budget 120→420 + cc4101 PRIMARY_HEADER_TIMEOUT 60→450 同步), 且实现 post-200 软挂换 key, 再 24h 观测。当前不动。

R2124
