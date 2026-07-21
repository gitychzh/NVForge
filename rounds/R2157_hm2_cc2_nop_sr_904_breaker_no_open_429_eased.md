# R2157 (hm2_cc2) — NOP R180 连续第115轮冻结, SR 90.4% 连续第3轮回带, breaker 未 OPEN, tier 429 大幅回落

> 日期: 2026-07-21 (CST 12:43 / UTC 04:43)
> 前轮: R2155 (commit cbcf816, SR 90.9%, breaker 未 OPEN, tier 429=23)
> 本轮: **NOP 巡检轮, 0 改动 0 restart, 连续第 115 轮冻结指数退避半成品**
> 轮号: R2156 已被 peer hm2_optimize_hm1 占用, cc2 用 R2157 hm2_cc2 前缀避撞号

## 数据 (30min 窗口, 当前 CST 12:43 / UTC 04:43, 窗口起点 ~04:13 UTC)

### nv_gw 30min 成功率
- status: 200×75 / 502×8
- **SR = 75/83 = 90.4%** (-0.5pp vs R2155 90.9%, 连续第 3 轮稳在 86-92% 次稳态带)

### 502 错误分类 (全 NVCF 已知类 0 新可配置类 ✅)
- all_tiers_exhausted ×7
- stream_absolute_cap ×1 (R1918 abs_cap 30min 机制, 设计行为)
- **0 NVAnth_IncompleteRead** (连续第 2 轮消失, vs R2154 有 1)

### tier 30min 错误分类
- pexec_success ×71
- **pexec_429 ×10** (vs R2155 23, **-13 大幅回落**, 第4波 429 显著回落仅 tier 层)
- pexec_conn_RemoteDisconnected ×8 (vs R2155 5, +3 略抬)
- pexec_SSLEOFError ×1 (vs R2155 0, +1 新现单点)
- tier 层 SR = 71/90 = 78.9% (vs R2155 68.9%, +10pp), 但 nv_gw 最终 SR 90.4% → tier 层 429/conn 被 nv_gw retry+key rotation 兜住, 没传导到最终 502 ✅

### 1min 桶轨迹 (UTC, 40min, 04:01→04:39)
- 04:01-05 连续 5 桶全 OK 回稳带 (1+1+3+3+1)
- 04:06 bad=1 散布 → 04:07-08 全 OK → 04:09 bad=1 散布 → 04:10 全 OK
- 04:11-14 连续 4 桶全 OK 回稳带 (5+4+3+2)
- 04:15 bad=1 散布 (5 total) → 04:16-17 全 OK → 04:18 bad=1 散布 → 04:20-21 全 OK
- 04:22 bad=1 散布 (4 total) → 04:23-24 全 OK → 04:25 bad=1 散布 (4 total)
- 04:26-30 连续 5 桶全 OK 回稳带 (5+3+3+3+3)
- 04:31 bad=1 散布 → 04:32 全 OK (5) → 04:34 bad=1 散布 (4 total) → 04:35 全 OK (4) → 04:36 bad=1 散布 (3 total) → 04:37 全 OK (5) → 04:38 bad=1 散布 (2 total) → 04:39 全 OK (3)
- **全程 bad≤1/桶, 无任何桶 bad≥2, 无连续多桶 bad≥5 风暴簇** ✅ (与 R2155 一样干净)

### fallback (负向核心指标)
- **6 FALLBACK-OK** (vs R2155 5, +1)
- 全 6 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (header/ttfb 75s < chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类)
- **0 条 120s 跑满类** (连续第 2 轮 0, 持平 R2155) ✅
- req 样本: b3599830 / bc7e74e8 / 4a6bf2bb / a6b6266e / 78ca6ca7 / 451b4a40 等 6 条
- cc4101 `grep -cE "both failed|UPSTREAM-ERROR-SEEN"` 30min = **0** → 0 真中断 ✅

### breaker
- **⚠️ nv_breaker 本轮全程未真 OPEN** (grep NV-MS-FB-BREAKER-OPEN = 0, 连续第 2 轮未 OPEN)
  - 1 条 `NV-ANTH-BREAKER-FAIL` (req=bb95a62c, stream_absolute_cap 触发 mid-stream 软挂, state=('CLOSED',4,0) — fail 计数累积到 4 但未推 OPEN 阈值, 与 R2155 同一条事件落在两窗口交叠区)
  - **vs R2154 的 OPEN→自愈, 连续 2 轮未真 OPEN, 设计行为平息正向确认** ✅
- breaker cc4101 PRIMARY-BREAKER-OPEN 30min = **0**
- breaker nv_gw 30min `grep -cE "NV-ANTH-BREAKER-FAIL"` = **1** (单点 fail 记录, state 仍 CLOSED 未持续 OPEN)

### 兜底机制计数
- **NV-CAP-RESET-MSFB = 7** (vs R2155 8, -1), 全被 ms_fb 兜住 0 真中断 ✅
- **BUG-A (R1913) SKIP-PEXEC2 = 7** (vs R2155 8, -1), 持续复活触发, 机制真实生效 ✅

### 容器/参数核实
- nv_gw /health = ok (passthrough, 5 keys, kimi_nv/dsv4p_nv/glm5_2_nv, default=dsv4p_nv)
- docker inspect StartedAt: nv_gw=**2026-07-21T01:44:55Z** (连续第 9 轮核实未漂移) / cc4101=2026-07-19T12:10:22Z (0 restart 未变)
- env 仍 peer R2108 改后值 (KEY60/TIER180/MIN_OUTBOUND10), cc2 0 改动 0 restart
- `NVU_GLM52_EXP_BACKOFF` 不在 env 中 = 关, 半成品冻结中

## 状态变化 (cc2 视角)
- (1) **30min SR 90.9%→90.4% -0.5pp 连续第 3 轮稳在次稳态带** (新稳态期延续, 小波动收尾)
- (2) **502 7→8 (+1)**: 7 all_tiers_exhausted + 1 stream_absolute_cap (abs_cap 设计), **0 NVAnth** (连续第 2 轮消失)
- (3) **tier pexec_429 23→10 (-13) 大幅回落** 第4波 429 显著回落仅 tier 层未传导到最终 502; pexec_conn_RemoteDisconnected 5→8 (+3) 略抬; pexec_SSLEOFError 0→1 (+1) 新现单点
- (4) **⚠️ nv_breaker 本轮未真 OPEN** (连续第 2 轮; R2154 的短暂 OPEN→自愈已平息, fail 计数仍停在 4 未达 OPEN 阈值)
- (5) fallback 5→6 (+1) 全 75s SKIP-CIRCUIT 被兜 0 真中断 0 失败 0 条 120s 跑满
- (6) NV-CAP-RESET-MSFB 8→7 / BUG-A SKIP-PEXEC2 8→7 均小幅回落
- (7) StartedAt 01:44:55Z 连续第 9 轮未漂移, env 未变

## 决策: 继续冻结 + NOP 巡检 (连续第 115 轮)

**本轮不满足解冻判断线** (需 30min SR 持续 < 45% 或出现连续多桶 bad≥5 风暴簇 且 502 出新可配类持续非单点 或 fallback 失败 或 breaker 真 OPEN 持续切流不自愈):
- SR 90.4% 连续第 3 轮稳在回带 + bad≤1/桶全文无风暴簇
- nv_breaker 本轮未真 OPEN (连续第 2 轮, R2154 的短暂 OPEN→自愈已平息, 设计行为正向确认)
- tier 429 大幅回落 (23→10) 仅 tier 层未传导到最终 502
- 0 真中断 0 fallback 失败 0 条 120s 跑满
- 502 全 NVCF 已知类 0 新可配类

**解冻不对症**: 指数退避链路碰不到 429 类 (本轮问题仍是 NVCF 上游 tier 429 + conn 略抬 + abs_cap 单点, 429 已大幅回落), 延长 chain_budget (120→420) 反而会拖低 SR (让 75s 能跑满到 420s 才 fallback, 增加 P95 延迟和数据空洞). 风险/收益不对等, 边际收益小.

**冻结理由 (连续第 115 轮) 仍成立**: 半成品未经 in-vivo 验证 (env 开关从未激活) + 激活需同步 chain_budget 120→420 + cc4101 PRIMARY_HEADER_TIMEOUT 60→450 + post-200 软挂换 key 未实现 + 24h 观测窗口.

## 下一轮该做什么
- 继续 NOP 巡检 (R181, 连续第 116 轮冻结), 重点看:
  1. 30min SR 是否稳在 86-92% 次稳态带 (本轮 90.4% 连续第 3 轮回带; 若下一轮 ≥86% 则确认新稳态期延续; 若 <86% 需观察是否仍散布; 若 <45% 或出现连续多桶 bad≥5 风暴簇则需重新评估)
  2. **⚠️⚠️ nv_breaker 是否再现 OPEN** (本轮未 OPEN 连续第 2 轮是正向; 这是关键观测点 — 若仅偶发短暂 OPEN 后自愈则持续确认是设计行为 (R1719 nv_breaker 在上游连断压力下正确切流); **若频繁 OPEN 持续切流或 OPEN 后不自愈 HALF_OPEN 失败**则需评估是否 NVCF 上游进入新不稳定期, 可能需重新评估解冻判断线)
  3. tier pexec_429 是否继续回落 (本轮 10 大幅回落) 或再抬头; pexec_conn_RemoteDisconnected/SSLEOFError 是否延续 (本轮 8+1) 或回落; 是否开始传导到最终 502 (本轮未传导 SR)
  4. NVAnth_IncompleteRead 是否仍消失 (本轮 0, 连续第 2 轮) 或再现
  5. 502 分类是否仍全 NVCF 已知类 0 新可配类 (本轮 8 = 7 all_tiers + 1 abs_cap)
  6. fallback 是否仍全 75s SKIP-CIRCUIT 被兜住 0 失败; **关注 120s 跑满类是否再现增多** (本轮 0 条, 连续第 2 轮)
  7. breaker (cc4101 PRIMARY / nv_gw NV-ANTH) 是否仍非持续性 OPEN; nv_gw StartedAt 是否仍 01:44:55Z (连续第 10 轮核实)
  8. NV-CAP-RESET-MSFB 是否持续增多 (本轮 7 回落; 若稳态期持续增多且 SR 被拖低需评估 chain_budget 是否过长)
- 轮号: 下一轮 git pull 看最新, peer 抢号很快 (R2156 已被 peer 占); cc2 用 R2158 或更大 hm2_cc2 前缀不撞号
- 若未来要解冻: 需先 in-vivo 验证 NVU_GLM52_EXP_BACKOFF (env 激活 + chain_budget 120→420 + cc4101 PRIMARY_HEADER_TIMEOUT 60→450 同步), 且实现 post-200 软挂换 key, 再 24h 观测. 当前不动.

HM2 only. 不碰 ms_gw (40007 热备). 只改 HM2 不改 HM1.
