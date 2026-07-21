# R2136 (hm2_cc2): NOP R170 连续第105轮冻结

**时间**: CST 2026-07-21 08:57 / UTC 00:57 (30min 窗口起点 ~00:27 UTC)
**轮号**: R2136 (hm2_cc2 前缀避撞号; peer hm2_optimize_hm1 抢号到 R2135 HM1 侧 TIER 52→50)
**上一轮**: R2135 (76a8340) NOP R169 连续第104轮冻结, 30min SR 53.2%

## 数据 (改前必有数据, 本 session 拉取)

### nv_gw 30min 成功率
- total=77, ok=38, 502=38 (vs R2135 41/77=53.2%, **本轮 38/77 = 49.4% -3.8pp 小幅回落**, 散布期延续, 仍跌出 86-92% 次稳态带)
- 502 全 **all_tiers_exhausted×38** (0 zombie, 0 NVAnth_IncompleteRead — **NVAnth_IncompleteRead 连续第5轮消失 R2132-2136, 持续确认非新可配类**) ✅
- 全 NVCF 上游已知类, **0 新可配置类** ✅

### 1min 桶完整轨迹 (UTC, 40min, 00:17→00:56)
- 00:17 回稳带 (4×200) → 00:18 散布又起 (3×200+3×502 单峰) → 00:20-27 散布延续 (00:27 桶 3×502 单峰) → 00:28-31 小回稳 (00:31 桶 4×200) → 00:32-33 散布 → 00:34 小回稳 (1×200) → 00:35-43 散布延续 (bad 1-3/桶, 00:38 桶 2×502 单峰) → 00:44-47 散布 (00:46 桶 2×502) → 00:48-50 小回稳 → 00:52-54 散布 (00:54 桶 3×502 单峰) → 00:55-56 回稳收尾 (00:56 桶 3×200)
- **全程 bad≤3/桶, 无连续多桶 bad≥5 风暴簇** (对比 R2120/R2121 风暴主峰 bad 5-10/桶 连续多桶, R2126 22:35-40 bad 5-6/桶) ✅
- 暂判散布期延续, 本轮小回落 -3.8pp 但未确认趋势恶化 (仍散布非簇, 无风暴)

### tier 30min error_type
- pexec_success×32 + pexec_conn_RemoteDisconnected×2 + NVCFPexecRemoteDisconnected×1 + pexec_SSLEOFError×1 + pexec_empty_200×1
- **429_nv_rate_limit = 0** (vs R2135 0 持平, **第4波 429 仍滚出 30min 窗口**) ✅
- vs R2135: pexec_success 34→32 (-2), pexec_conn_RemoteDisconnected 3→2 (-1 回落), NVCFPexecRemoteDisconnected 1→1 持平, SSLEOFError 1→1 持平, pexec_empty_200 1→1 持平, tier 层连接异常整体低位均 NVCF 上游已知类无新可配置类 ✅

### fallback / breaker / cap / BUG-A
- fallback **7** FALLBACK-OK (vs R2135 8 -1, 0 真中断, 0 fallback 失败): 全 7 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (header/ttfb 75s < chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类). **0 条 120s 跑满类** (持平 R2135) ✅. req 样本: 9351ce41 / 1fce4bd7 / eecb40c0 / 03eb76ed / 72b0f237 / e830c9b2 / 342c79fa
- cc4101 `grep -cE "both failed|UPSTREAM-ERROR-SEEN"` 30min = **0** → 0 真中断确认 ✅
- cc4101 PRIMARY-BREAKER-OPEN 30min = **0**
- nv_gw 30min `grep -cE "NV-Anth-BREAKER-FAIL"` = **0** (state 未 OPEN, **连续第38轮**) ✅
- **NV-CAP-RESET-MSFB = 5 条** (vs R2135 6 -1, R1818 bug7 已有 cap_origin reset 机制 execute→ms_fb path 正常触发, 全被 ms_fb 兜住 0 真中断) ✅
- **BUG-A 修复 (R1913) 生效确认**: 30min 内 `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **5 次** (vs R2135 6 -1, 持续复活触发中, 机制真实生效) ✅
- **abs_cap 30min 正常** (CAP-RESET 5 条, 与 breaker 段持平) ✅

### health / StartedAt / env
- nv_gw /health = ok (passthrough, 5 keys, kimi_nv/dsv4p_nv/glm5_2_nv, default=dsv4p_nv)
- nv_gw StartedAt = **2026-07-20T18:10:28Z** (R2107 后未再漂移, **连续第25轮核实 18:10 稳定**)
- cc4101 StartedAt = 2026-07-19T12:10:22Z (0 restart 未变)
- env 仍 peer R2108 改后值 (KEY_COOLDOWN=60, TIER_COOLDOWN=180, MIN_OUTBOUND=10), cc2 0 改动; NVU_GLM52_EXP_BACKOFF 不在 env 中 = 半成品冻结中

## 决策: NOP R170, 连续第105轮冻结指数退避

**0 改动 0 restart**. 依据 STATE 下一步判断线 8 条全未恶化:
1. 30min SR 49.4% (vs R2135 53.2% -3.8pp 小幅回落, 散布期延续但本轮小回落, 未确认趋势恶化, 仍散布非簇)
2. NVAnth_IncompleteRead 连续第5轮消失 (R2132-2136) 持续确认非新可配类
3. tier 连接异常整体低位均 NVCF 已知类 (pexec_conn_RemoteDisconnected 2, SSLEOFError 1, pexec_empty_200 1)
4. tier 429_nv_rate_limit=0 (第4波 429 仍滚出)
5. 502 全 NVCF 已知类 all_tiers_exhausted×38, 0 新可配置类
6. fallback 全 75s SKIP-CIRCUIT 被兜 0 失败, 0 条 120s 跑满
7. breaker 仍非真 OPEN (连续第38轮); nv_gw StartedAt 仍 18:10:28Z (连续第25轮)
8. NV-CAP-RESET-MSFB 5 条 (vs R2135 6 -1 回落, 未持续增多)

**解冻不对症 (二十轮论证)**: 本轮问题是 NVCF 上游 all_tiers_exhausted 散布期 (RemoteDisconnected/SSLEOFError/empty_200/all_tiers_exhausted), 指数退避链路碰不到此错误类, 延长 chain_budget 反拖 SR. 半成品未经 in-vivo 验证 (env 开关从未激活) + 激活需同步 chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key 未实现 + 24h 观测窗口. 风险/收益不对等.

**用户诉求 "可以报错但不能让 cc2 中断" 仍达成**: 0 真中断, 7 条 FALLBACK-OK 全被 ms_gw 兜住 0 fallback 失败.

## 验证
- N/A (NOP 0 改动, 无需 restart 验证; 数据即验证)

## 状态变化
- 无 (cc2 视角). nv_gw StartedAt 仍 18:10:28Z (连续第25轮核实未漂移), env 仍 peer R2108 改后值, cc2 0 改动 0 restart.
- 本轮需记录的变化:
  (1) 30min SR 53.2%→49.4% 小幅回落 (-3.8pp 散布期延续但本轮小回落, 仍跌出 86-92% 次稳态带)
  (2) 502 36→38 (+2 全 NVCF 已知类, NVAnth_IncompleteRead 连续第5轮消失已确认非新可配类)
  (3) tier 429_nv_rate_limit=0 持平 (第4波 429 仍滚出)
  (4) tier pexec_success 34→32 (-2), pexec_conn_RemoteDisconnected 3→2 (-1 回落), NVCFPexecRemoteDisconnected 1→1 持平, SSLEOFError 1→1 持平, pexec_empty_200 1→1 持平, 连接异常整体低位均 NVCF 已知类
  (5) fallback 8→7 (-1) 全 75s SKIP-CIRCUIT 被兜 0 真中断 0 失败 0 条 120s 跑满
  (6) NV-CAP-RESET-MSFB 6→5 (-1) / BUG-A SKIP-PEXEC2 6→5 (-1)
  (7) breaker/abs_cap 全部未恶化, breaker 仍未 OPEN 连续第38轮, StartedAt 未漂移连续第25轮

HM2 only. 不碰 proxy/ms-gw/. R2136
