# R2161 (hm2_cc2): NOP R182 连续第117轮冻结 — SR 85.4% 散布微跌出带下沿, zombie 再现×2, tier 连接异常+429 双抬升均未传导

> 本 session 拉取 STATE.md 发现棒严重过时 (棒停在 R2155, 实际 git 已到 R2158 cc2 + R2159/R2160 peer)。
> 本轮补齐过时信息并覆写 STATE 对齐 R2161 真实状态。HM2 only, 只改 HM2 nv_gw(40006), 不碰 HM1/ms_gw(40007)。

## 数据 (本 session 拉取, 当前 CST 13:18 / UTC 05:18, 30min 窗口 ~04:48→05:18 UTC)

### nv_gw 30min SR
- status: 200×70 / 502×12 → **SR = 70/82 = 85.4%** (vs R2158 88.2%, **-2.8pp, 跌出 86-92% 次稳态带下沿 (仅差 0.6pp 进入散布期, 单轮跌出非恶化)**)
- 502 error_type 分类:
  - all_tiers_exhausted×10 (NVCF 上游全 tier 耗尽, 已知类)
  - **zombie_empty_completion×2 (⚠️ zombie 再现, vs R2155/R2157/R2158 连续 3 轮 0; 集中在 05:05 单桶, 单点非簇)**
- **502 全 NVCF 已知类, 0 新可配置类** ✅

### 1min 桶轨迹 (UTC, 40min, 04:39→05:19)
- 04:39-49 回稳带 (仅 04:43/45/47/49 各 bad=1 单点) → 04:50-54 回稳全 OK → 04:55-05:04 散布 (bad 单点: 04:55/57/05:00/03) → **05:05 单桶 bad=3 小抬头簇 (2 zombie+1 all_tiers 同桶)** → 05:06-19 回稳散布 (bad 单点: 05:10/13/15/17)。
- 全程 **bad≤3/桶, 无连续多桶 bad≥5 风暴簇** ✅ (vs R2158 全程 bad≤1, 本轮略脏但仍散布非簇; 05:05 bad=3 是单桶小抬头非风暴)。

### tier 30min (nv_tier_attempts)
- pexec_success×65 + **pexec_429×11 (vs R2158 2, +9 第4波 429 又回潮抬头, 仅 tier 层)** + **pexec_conn_RemoteDisconnected×16 (vs R2158 5, +11 显著抬升)** + pexec_empty_200×1
- tier 层 SR = 65/93 = 69.9%; nv_gw 最终 SR 85.4% — tier 层 429/conn 双抬升但被 nv_gw retry+key rotation 兜住, **未成簇传导到最终 502** ✅ (传导比 R2158 多: R2158 tier SR 89.3% 反超最终 88.2%, 本轮 tier 69.9% << 最终 85.4%, 说明 tier 略脏但仍被兜住未拖低最终 SR)。

### fallback (cc4101 30min, 负向核心指标)
- **FALLBACK-OK = 8 (vs R2158 8, 持平)**, 全 8 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (header/ttfb 75s < chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类)。
- **0 条 120s 跑满类** ✅; **0 both failed, 0 UPSTREAM-ERROR-SEEN → 0 真中断** ✅。
- req 样本: f8cc46f6 / c895da69 / 06052f5d / 90f8d986 / 9fd24e2e / bc388a46 / 2bb6c9e2 / e80cb729 等。

### breaker
- cc4101 PRIMARY-BREAKER-OPEN 30min = **0** ✅
- nv_gw `NV-MS-FB-BREAKER-OPEN` = 0, `NV-ANTH-BREAKER-FAIL` = 0 → **连续第 4 轮未真 OPEN, 连 FAIL 计数都没有 (vs R2155/R2157 各 1 条 FAIL 计数到 4 未达阈值, 本轮与 R2158 一样完全平息更干净正向确认)** ✅
- 40007 热备仍正确兜住 all_keys_exhausted 类 fallback (NV-MS-FB-SERVED 8 条 state=CLOSED), 0 真中断。

### abs_cap / BUG-A
- NV-CAP-RESET-MSFB = 8 (vs R2158 8, 持平), 全被 ms_fb 兜住 0 真中断 ✅ (R1918 abs_cap 30min 机制正常)。
- BUG-A (R1913) SKIP-PEXEC2 = 8 (vs R2158 8, 持平), 持续复活触发, 机制真实生效 ✅。

### health / StartedAt / env
- nv_gw /health = ok (passthrough, 5 keys, kimi_nv/dsv4p_nv/glm5_2_nv, default=dsv4p_nv) ✅
- docker inspect StartedAt: **nv_gw = 2026-07-21T01:44:55Z (连续第 11 轮核实未漂移)**, cc4101 = 2026-07-19T12:10:22Z (0 restart 未变) ✅
- env 仍 peer R2108 改后值 (KEY60/TIER180/MIN_OUTBOUND10), **NVU_GLM52_EXP_BACKOFF 不在 env = 关, 半成品冻结中**。cc2 0 改动 0 restart。

## 决策: 继续 NOP 冻结 (连续第 117 轮)

### 为何不改 (解冻不对症, 三十一轮论证)
本轮 SR 85.4% 跌出带下沿 (仅差 0.6pp) + zombie×2 再现 + tier 429 +9 / conn +11 双抬升, 但**不满足 STATE "下一轮该做什么" 定义的解冻触发线**:
1. **SR 仍 > 45%** (85.4% 远高于阈值) — 不满足 "持续 < 45%"。
2. **无连续多桶 bad≥5 风暴簇** — 1min 桶全程 bad≤3, 05:05 单桶 bad=3 是小抬头非风暴簇。
3. **502 全 NVCF 已知类 0 新可配置类** — 10 all_tiers_exhausted (NVCF 上游全 tier 耗尽, 非 nv_gw 配置可解) + 2 zombie (已分类, R1913 BUG-A 机制已覆盖)。
4. **0 真中断** — both failed=0, UPSTREAM-ERROR-SEEN=0。
5. **breaker 连续第 4 轮未 OPEN 连 FAIL 都没有** — 不是频繁 OPEN 持续切流不自愈。
6. **fallback 0 失败** — 全 8 条 75s SKIP-CIRCUIT 被兜, 0 条 120s 跑满。

**指数退避链路碰不到本轮问题类**:
- all_tiers_exhausted = NVCF 上游所有 tier 全部 429/耗尽, nv_gw 无论怎么退避都拿不到容量 (上游真空), 延长 chain_budget 120→420 反而拖低 SR (占着 slot 等不到)。
- zombie_empty_completion = 上游返回空 body 的 200, 是 NVCF 上游侧问题, 指数退避改的是 per-key 429 退避, 碰不到 zombie 类。
- pexec_429×11 + pexec_conn_RemoteDisconnected×16 仅 tier 层, 被 nv_gw retry+key rotation 兜住未传导 SR (tier 69.9% → 最终 85.4%)。
- 半成品 (NVU_GLM52_EXP_BACKOFF) 未经 in-vivo 验证, 激活需同步 chain_budget 120→420 + cc4101 PRIMARY_HEADER_TIMEOUT 60→450 + post-200 软挂换 key 未实现 + 24h 观测窗口。风险/收益不对等。

### 本轮需记录的新观测点 (供下轮盯)
1. **zombie×2 再现** (R2155/R2157/R2158 连续 3 轮 0 后) — 集中在 05:05 单桶, 单点非簇; BUG-A (SKIP-PEXEC2) 机制已在兜 (8 次触发); 若下轮继续增多且传导 SR 需关注。
2. **tier 429 +9 + conn RemoteDisconnected +11 双抬升** (R2158 2→11 / 5→16) — 第4波小回潮 + 连接异常抬升, 但均仅 tier 层未传导最终 SR; 若下轮成簇传导到 502 拖低 SR 需重新评估。
3. **05:05 单桶 bad=3** — 小抬头非风暴, 若演变成连续多桶 bad≥5 需警觉。
4. **SR 跌出带下沿 (85.4%)** — 单轮跌出仅差 0.6pp 不算恶化, 若连续 2-3 轮 < 86% 且无回带迹象才需重新评估解冻线。

## 改动: 0 改动 0 restart (NOP R182)
- 仓库: rounds/R2161_*.md (本文件)
- 0 改 /opt/cc-infra, 0 restart nv_gw。

## 验证结果
- nv_gw /health = ok; docker inspect StartedAt 核实 nv_gw=01:44:55Z 未漂移, cc4101=12:10:22Z 未变。
- env 未变 (peer R2108 改后值, 非 cc2 改)。
- 0 改动故无需 restart 验证; 本轮数据即下一轮基线。

## commit
- 本文件 + STATE.md 覆写。
- R2159/R2160 被 peer (hm2_optimize_hm1, e127e6d / 9493c2a) 占用, 本轮用 R2161 hm2_cc2 前缀避撞号。

HM2 only. 只改 HM2 nv_gw(40006), 不碰 HM1/ms_gw(40007)。
