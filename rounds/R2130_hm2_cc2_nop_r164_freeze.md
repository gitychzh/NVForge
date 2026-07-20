# R2130 (hm2_cc2) — NOP R164 连续第 99 轮冻结, SR 连续第 2 轮小升 62.3%

> date: 2026-07-21 CST 07:40 / UTC 23:40 (本 session 拉取)
> scope: HM2 only, nv_gw(40006), 不碰 ms_gw(40007), 不碰 HM1
> 模式: nv 直连 (cc4101→nv_gw), 指数退避+ms 双层方案半成品仍冻结 (NVU_GLM52_EXP_BACKOFF 不在 env=关, 从未 in-vivo 激活)

## 数据 (30min 窗口, UTC 23:10→23:40, 当前 UTC 23:40)

### nv_gw 30min SR
- **SR = 43/69 = 62.3%** (200:43 / 502:26)
- vs R2129 61.3% **+1.0pp 连续第 2 轮小升** (R2128 58.7 → R2129 61.3 → R2130 62.3, 降幅收窄后连续回升, 积极信号)
- vs R2124 92.2% -29.9pp 仍跌出 86-92% 次稳态带 (由散布型 all_tiers_exhausted 502 驱动, 非风暴簇)

### 1min 桶完整轨迹 (UTC, 35min, 23:06→23:41)
- 23:06-09 回稳带 (23:08 桶 4×200, 23:09 桶 5×200+3×502, 延续 R2129 末段回稳带)
- 23:11-22 散布又起 (bad 1-3/桶, 23:22 桶 bad=3)
- 23:23-27 部分回稳 (23:23-24 各 4-3×200, 23:27 桶 5×200)
- 23:31-41 散布延续 (bad 1-2/桶)
- **全程 bad≤3/桶, 无连续多桶 bad≥5 风暴簇** ✅ (对比 R2120/R2121 风暴主峰 bad 5-10/桶, R2126 22:35-40 bad 5-6/桶)
- 暂判散布期延续, 散布型收尾中, 连续第 2 轮 SR 小升确认积极趋势

### 30min 502 分类 (26 全 NVCF 已知类, 0 新可配置类) ✅
- all_tiers_exhausted ×24
- zombie_empty_completion ×2 (vs R2129 3 → 2 -1)
- NVAnth_IncompleteRead ×1 (vs R2129 1 持平, 仍单点未演变为簇 — STATE 下一步重点②已验证: 仍 1 条单点, 非新可配置类确认)
- vs R2129 29 → 26 (-3 散布量略降)

### tier 30min
- pexec_success ×36 (vs R2129 40 → 36 -4)
- 500_nv_error ×7 (vs R2129 6 → 7 +1, NVCF 已知类)
- pexec_conn_RemoteDisconnected ×2 (vs R2129 4 → 2 -2 回落)
- NVCFPexecRemoteDisconnected ×1 (vs R2129 2 → 1 -1 回落)
- pexec_SSLEOFError ×1 (vs R2129 1 持平)
- **429_nv_rate_limit = 0 持平** (第4波 429 仍滚出 30min 窗口) ✅
- STATE 下一步重点③已验证: tier 连接异常整体略降 (RemoteDisconnected 4→2, NVCFPexecRemoteDisconnected 2→1), 均 NVCF 已知类无新可配置类

### fallback (6 全 75s SKIP-CIRCUIT 被兜, 0 真中断 0 失败) ✅
- 6 条 FALLBACK-OK 全 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (header/ttfb 75s < chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类)
- **0 条 120s 跑满类** (持平 R2129) ✅
- req 样本: 3971cd0e / b88a9f1d / 30408f04 / 38742c79 / 3c65fb40 / 541983c4
- vs R2129 6 持平
- cc4101 `grep -cE "both failed|UPSTREAM-ERROR-SEEN"` 30min = **0** → 0 真中断确认

### breaker (连续第 32 轮未 OPEN) ✅
- cc4101 PRIMARY-BREAKER-OPEN 30min = **0**
- nv_gw 30min `grep -cE "NV-Anth-BREAKER-FAIL"` = **0** (state 未 OPEN, 连续第 32 轮)

### abs_cap / BUG-A
- **NV-CAP-RESET-MSFB = 5 条** (vs R2129 5 持平, R1818 bug7 cap_origin reset 机制 execute→ms_fb path 正常触发, 全被 ms_fb 兜住 0 真中断) ✅
- **BUG-A (R1913) SKIP-PEXEC2 触发 5 次** (vs R2129 5 持平, 持续复活触发中, 机制真实生效) ✅

### 健康/StartedAt
- nv_gw /health = ok (passthrough, 5 keys, kimi_nv/dsv4p_nv/glm5_2_nv, default=dsv4p_nv)
- nv_gw StartedAt = **2026-07-20T18:10:28Z** (连续第 19 轮核实未漂移; R2107 后未再变)
- cc4101 StartedAt = 2026-07-19T12:10:22Z (0 restart 未变)

## 本轮决策: NOP R164, 连续第 99 轮冻结, 0 改动 0 restart

**不改的理由 (STATE 下一步判断线 "本轮不满足持续恶化")**:
1. **SR 连续第 2 轮小升** (58.7→61.3→62.3, 降幅收窄后首现连续回升, 积极信号; 虽仍跌出 86-92% 次稳态带但趋势向上, 非持续恶化).
2. **502 全 NVCF 已知类 0 新可配置类** (all_tiers_exhausted×24 + zombie×2 + NVAnth_IncompleteRead×1 单点, NVAnth_IncompleteRead 仍 1 单点未爆发为簇 — STATE 下一步重点②已验证).
3. **0 真中断** (cc4101 both failed=0) + fallback 全 6 条 75s SKIP-CIRCUIT 被 ms_gw 兜住 0 失败 0 条 120s 跑满.
4. **breaker 仍未 OPEN** (连续第 32 轮).
5. **tier 429_nv_rate_limit=0** (第4波 429 仍滚出).
6. StartedAt 未漂移 (连续第 19 轮), env 仍 peer R2108 改后值非 cc2 改.

**解冻仍不对症**: 本轮问题是 NVCF 上游连接抖动散布期 (RemoteDisconnected/SSLEOFError/IncompleteRead/all_tiers_exhausted), 指数退避链路碰不到此错误类, 延长 chain_budget 反拖 SR. 连续第 14 轮论证. 解冻需先 in-vivo 验证 NVU_GLM52_EXP_BACKOFF (env 激活 + chain_budget 120→420 + cc4101 PRIMARY_HEADER_TIMEOUT 60→450 同步) + 实现 post-200 软挂换 key + 24h 观测, 当前不动.

## 验证结果
- 本轮 0 改动 0 restart, 无需验证 restart 后健康.
- nv_gw /health = ok, docker inspect StartedAt 未漂移 (18:10:28Z 连续第 19 轮), env 未变.
- 下一窗口 SR/fallback/breaker 未恶化即继续 NOP.

## STATE 下一步判断线对照 (本轮逐条验证)
1. ✅ SR 继续回升 (61.3→62.3 +1.0pp 连续第 2 轮小升, 确认 NVCF 上游散布瞬态收尾趋势, 但仍未回 86-92% 次稳态带).
2. ✅ NVAnth_IncompleteRead 仍 1 条单点 (未演变为持续/风暴簇, 非新可配置类确认).
3. ✅ tier 连接异常整体略降 (RemoteDisconnected 4→2, NVCFPexecRemoteDisconnected 2→1, 均 NVCF 已知类).
4. ✅ tier 429_nv_rate_limit 仍=0 (第4波 429 仍滚出).
5. ✅ 502 仍全 NVCF 已知类 0 新可配置类 (26 = all_tiers_exhausted×24 + zombie×2 + NVAnth_IncompleteRead×1).
6. ✅ fallback 仍全 75s SKIP-CIRCUIT 被兜 0 失败; 120s 跑满类仍 0 条.
7. ✅ breaker 仍非真 OPEN (连续第 32 轮); nv_gw StartedAt 仍 18:10:28Z (连续第 19 轮).
8. ✅ NV-CAP-RESET-MSFB 5 条持平 (未持续增多).

**结论**: 全 8 条判断线均 "未恶化/积极", 连续第 99 轮 NOP 冻结成立.

## 状态变化 (cc2 视角)
- 无 (0 改动 0 restart). 本轮需记录的变化:
  1. 30min SR 61.3%→62.3% +1.0pp 连续第 2 轮小升 (积极信号延续).
  2. 502 29→26 (-3 全 NVCF 已知类, NVAnth_IncompleteRead 仍 1 单点).
  3. tier 429_nv_rate_limit=0 持平 (第4波 429 仍滚出).
  4. tier pexec_success 40→36 (-4), 500_nv_error 6→7 (+1), pexec_conn_RemoteDisconnected 4→2 (-2), NVCFPexecRemoteDisconnected 2→1 (-1), SSLEOFError 1→1 持平.
  5. fallback 6 持平 全 75s SKIP-CIRCUIT 被 ms_gw 兜 0 真中断 0 失败 0 条 120s 跑满.
  6. NV-CAP-RESET-MSFB 5 持平 / BUG-A SKIP-PEXEC2 5 持平.
  7. breaker/abs_cap 全部未恶化, breaker 仍未 OPEN 连续第 32 轮, StartedAt 未漂移连续第 19 轮.

## 参数快照 (本轮 0 改动, env 与 R2129 完全一致)
- NVU_GLM52_EXP_BACKOFF 不在 env = 关 (半成品冻结中, 从未 in-vivo 激活)
- KEY_COOLDOWN_S=60 / TIER_COOLDOWN_S=180 / MIN_OUTBOUND_INTERVAL_S=10 (peer R2108 改后值, 非 cc2 改)
- UPSTREAM_TIMEOUT=90 / TIER_TIMEOUT_BUDGET_S=180 / chain_budget 仍 120s (未升 420)

HM2 only. R2130
