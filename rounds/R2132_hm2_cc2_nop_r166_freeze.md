# R2132 (hm2_cc2) — NOP R166 连续第 101 轮冻结指数退避

> 本轮: 0 改动 0 restart. 巡检轮. CST 08:01 / UTC 00:01 拉取 30min 窗口数据 (起点 ~23:31 UTC).

## 数据 (30min nv_gw 窗口, 本 session 拉取)

- **30min SR = 51/89 = 57.3%** (200:51 / 502:38).
  - vs R2131 59.8%: **-2.5pp 继续小幅回落** (R2128 58.7 → R2129 61.3 → R2130 62.3 → R2131 59.8 → R2132 57.3, 连续第 2 轮小升被打断后延续回落至 R2128 58.7% 附近偏低 1.4pp).
  - vs R2124 92.2%: -34.9pp 仍跌出 86-92% 次稳态带, 由散布型 all_tiers_exhausted 502 驱动非风暴簇.

- **1min 桶完整轨迹 (UTC, 35min, 23:27→00:01)**:
  23:27-28 散布 (23:27 桶 4×200, 23:28 桶 502×1) → 23:29-34 散布延续 (bad 1-2/桶, 23:31 桶 2×200+2×502, 23:34 桶 1×200+1×502) → 23:35-41 回稳带 (23:35/40 桶 4×200, 23:41 桶 3×200, 23:40 桶 4×200+1×502) → 23:42-48 散布延续 (bad 1-2/桶, 23:42/44/47/48 桶 bad=2) → 23:49-50 小回稳 (23:49 桶 3×200) → 23:51-56 散布 (23:52 桶 502×3 单峰, 其余 bad≤2/桶) → 23:57-59 回稳带 (23:57/58/59 桶各 4×4×4×200 连续) → 00:00 桶 bad=3 → 00:01 桶 4×200 回稳.
  **全程 bad≤3/桶** (仅 23:52 桶 502×3 单峰, 00:00 桶 bad=3), **无连续多桶 bad≥5 风暴簇** (对比 R2120/R2121 风暴主峰 bad 5-10/桶, R2126 22:35-40 bad 5-6/桶). 散布期延续, 散布型收尾中, 23:57-59 连续 3 桶 200×4 小回稳带是积极信号.

- **502 = 38 全 all_tiers_exhausted×38** (全 NVCF 上游已知类, **0 新可配置类**). vs R2131 33 → 38 (+5 散布量略增非簇). **0 zombie / 0 NVAnth_IncompleteRead** (本轮 NVAnth 单点消失, R2129-R2131 持续的 1 条单点本轮未再现, 持续确认非新可配类).

- **tier 30min**: pexec_success×46 + pexec_conn_RemoteDisconnected×2. **429_nv_rate_limit = 0** (vs R2131 0 持平, **第4波 429 仍滚出 30min 窗口**) ✅. vs R2131: pexec_success 43→46 (+3), 500_nv_error 1→0 (回落清零), pexec_conn_RemoteDisconnected 0→2 (+2 低位), NVCFPexecRemoteDisconnected 1→0 (回落), SSLEOFError 0→0 持平. tier 层连接异常整体低位均 NVCF 已知类无新可配置类.

## 验证项 (STATE 下一步判断线 8 条)

- **fallback = 5** FALLBACK-OK (**0 真中断**, cc4101 `both failed` / `UPSTREAM-ERROR-SEEN` 30min = **0**):
  - 4 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (header/ttfb 75s < chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类): req 541983c4 / 1f4d66de / 9015da93 / aebb372b.
  - 1 条 conn 41s `PRIMARY-FAIL` (RemoteDisconnected, 256066f4, 非 75s 类但仍被 ms_gw 兜住 8769ms).
  - **0 条 120s 跑满类** (持平 R2131) ✅. R2131 fallback 5 → 本轮 5 持平.
- **breaker**: nv_gw 30min `NV-Anth-BREAKER-FAIL` = **0** (state 未 OPEN, 连续第 34 轮) ✅; cc4101 `PRIMARY-BREAKER-OPEN` 30min = **0** ✅.
- **BUG-A 修复 (R1913) 生效确认**: 30min 内 `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **4 次** (vs R2131 5 → -1, 持续复活触发中, 机制真实生效) ✅.
- **abs_cap 30min 正常**: `NV-CAP-RESET-MSFB` = 4 条 (vs R2131 5 → -1, R1818 bug7 已有 cap_origin reset 机制 execute→ms_fb path 正常触发, 全被 ms_fb 兜住 0 真中断) ✅.
- nv_gw /health = ok (passthrough, 5 keys, kimi_nv/dsv4p_nv/glm5_2_nv, default=dsv4p_nv). docker ps 全 Up (nv_gw/cc4101/ms_gw).
- **nv_gw StartedAt 核实 = 2026-07-20T18:10:28Z** (R2107 后未再漂移, **连续第 21 轮核实 18:10 稳定**) ✅; cc4101 StartedAt = 2026-07-19T12:10:22Z (0 restart 未变).
- **env 快照 (docker exec env)**: NVU_GLM52_EXP_BACKOFF **不在 env 中 = 关** (半成品冻结, 从未 in-vivo 激活). env 仍 peer R2108 改后值 (KEY_COOLDOWN 25→60, TIER_COOLDOWN 25→180, MIN_OUTBOUND 0→10), 非 cc2 改. chain_budget 仍 120s, 未升 420.

## 状态变化 (cc2 视角, 本轮)

无 (0 改动 0 restart). nv_gw StartedAt 仍 18:10:28Z (连续第 21 轮核实未漂移), env 仍 peer R2108 改后值, cc2 0 改动. 本轮需记录的变化:
1. **30min SR 59.8%→57.3% 继续小幅回落** (-2.5pp, R2128 58.7→R2129 61.3→R2130 62.3→R2131 59.8→R2132 57.3, 连续第 2 轮小升被打断后延续回落至 R2128 偏低 1.4pp, 仍跌出 86-92% 次稳态带, 散布型 502 延续但 23:57-59 连续 3 桶 200×4 小回稳带是积极信号).
2. 502 33→38 (+5 全 all_tiers_exhausted NVCF 已知类, **0 zombie / 0 NVAnth_IncompleteRead** 本轮单点消失, 持续确认 NVAnth 非新可配类).
3. tier 429_nv_rate_limit=0 持平 (第4波 429 仍滚出); pexec_success 43→46 (+3), 500_nv_error 1→0 (回落清零), pexec_conn_RemoteDisconnected 0→2 (+2 低位), NVCFPexecRemoteDisconnected 1→0 (回落), 连接异常整体低位均 NVCF 已知类.
4. fallback 5 持平全被兜 (4 条 75s SKIP-CIRCUIT + 1 条 conn 41s), 0 真中断 0 失败 0 条 120s 跑满.
5. NV-CAP-RESET-MSFB 5→4 / BUG-A SKIP-PEXEC2 5→4 (均小幅波动, 机制持续生效).
6. breaker/abs_cap 全部未恶化, breaker 仍未 OPEN 连续第 34 轮, StartedAt 未漂移连续第 21 轮.

## 冻结理由 (连续第 100 轮) 仍成立

半成品未经 in-vivo 验证 (env 开关从未激活) + 激活需同步 chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key 未实现 + 24h 观测窗口. 风险/收益不对等 (本轮 30min SR 57.3% 散布型 all_tiers_exhausted 502 非风暴簇 + 第4波 429 仍滚出 tier 429=0 + 0 真中断 + abs_cap 30min 机制正常 + BUG-A 修复真实生效 + 4 条 NV-CAP-RESET-MSFB 全被 ms_fb 兜住非恶化, 边际收益小; **解冻不对症** — 本轮问题是 NVCF 上游连接抖动散布期 (all_tiers_exhausted / RemoteDisconnected), 指数退避链路碰不到此错误类, 延长 chain_budget 反拖 SR, 十六轮论证).

STATE 下一步判断线 8 条全未恶化 (SR<85% 但连续散布非风暴污染 + 502 全 NVCF 已知类 NVAnth 单点本轮消失 + 0 真中断 + breaker 未 OPEN).

## 结论

**NOP R166, 连续第 101 轮冻结指数退避, 0 改动 0 restart.** 本轮 30min SR 57.3% 散布期延续 (23:57-59 连续 3 桶 200×4 小回稳带是积极信号, 但 00:00 桶 bad=3 未确认稳态回归), 502 全 NVCF 已知类 0 新可配类 (NVAnth 单点本轮消失), tier 429=0 第4波仍滚出, 0 真中断, breaker 仍未 OPEN 连续第 34 轮, StartedAt 未漂移连续第 21 轮. 解冻不对症 (NVCF 上游连接抖动散布期, 指数退避链路碰不到, 延长 chain_budget 反拖 SR, 十六轮论证). HM2 only. R2132
