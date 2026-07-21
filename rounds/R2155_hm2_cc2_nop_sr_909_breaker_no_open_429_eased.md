# R2155 (hm2_cc2) — NOP R179 连续第114轮冻结, SR 90.9% 回带, breaker 未 OPEN, tier 429 略回落

> 日期: 2026-07-21 (CST 12:26 / UTC 04:26)
> 前轮: R2154 (commit 715b441, SR 90.1%, nv_breaker 短暂真 OPEN 1 次自愈, tier 429=25)
> 本轮: **NOP 巡检轮, 0 改动 0 restart, 连续第 114 轮冻结指数退避半成品**

## 数据 (30min 窗口, 当前 CST 12:26 / UTC 04:26, 窗口起点 ~03:56 UTC)

### nv_gw 30min 成功率
- status: 200×70 / 502×7
- **SR = 70/77 = 90.9%** (+0.8pp vs R2154 90.1%, 连续第 2 轮稳在 86-92% 次稳态带)

### 502 错误分类 (全 NVCF 已知类 0 新可配置类 ✅)
- all_tiers_exhausted ×6
- stream_absolute_cap ×1 (R1918 abs_cap 30min 机制, 设计行为)
- **0 NVAnth_IncompleteRead** (vs R2154 有 1, 本轮消失)

### tier 30min 错误分类
- pexec_success ×62
- **pexec_429 ×23** (vs R2154 25, -2 略回落, 第4波 429 仍高位但仅 tier 层)
- pexec_conn_RemoteDisconnected ×5 (持平 R2154)
- tier 层 SR = 62/90 = 68.9%, 但 nv_gw 最终 SR 90.9% → tier 层 429/conn 被 nv_gw retry+key rotation 兜住, 没传导到最终 502 ✅

### 1min 桶轨迹 (UTC, 40min, 03:47→04:27)
- 03:47-48 全 OK (2/2, 2/2)
- 03:49-55 散布 (bad 各 1 单点: 03:49/53/54/55)
- 03:56-04:00 连续 5 桶全 OK 回稳带 (03:56-04:00)
- 04:01-15 散布 (bad 各 1 单点: 04:01/06/09/15, 04:11-14 回稳 5×200/4×200/3×200/2×200)
- 04:16-27 散布 (bad 各 1 单点: 04:18/22/25, 04:26 回稳 5×200)
- **全程 bad≤1/桶, 无任何桶 bad≥2, 无连续多桶 bad≥5 风暴簇** ✅ (比 R2154 的 bad≤2/桶更干净)

### fallback (负向核心指标)
- **5 FALLBACK-OK** (vs R2154 7, -2)
- 全 5 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (header/ttfb 75s < chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类)
- **0 条 120s 跑满类** (持平 R2154) ✅
- req 样本: 89c7497c / 8089aa2c / b3599830 / bc7e74e8 / 4a6bf2bb 等 5 条
- cc4101 `grep -cE "both failed|UPSTREAM-ERROR-SEEN"` 30min = **0** → 0 真中断 ✅

### breaker
- **⚠️ nv_breaker 本轮全程未真 OPEN** (grep NV-MS-FB-BREAKER-OPEN = 0)
  - 有若干 NV-MS-FB-ATTEMPT/SERVED (all_keys_exhausted 走 ms_gw fallback, breaker state 持续 CLOSED)
  - 1 条 `NV-ANTH-BREAKER-FAIL` (req=bb95a62c, stream_absolute_cap 触发 mid-stream 软挂, state=('CLOSED',4,0) — fail 计数累积到 4 但未推 OPEN 阈值)
  - **vs R2154 的 OPEN→自愈, 本轮是 fail 累积但阈突未达 OPEN, 更稳** ✅
- breaker cc4101 PRIMARY-BREAKER-OPEN 30min = **0**
- breaker nv_gw 30min `grep -cE "NV-Anth-BREAKER-FAIL"` = **1** (单点 fail 记录, state 仍 CLOSED 未持续 OPEN)

### 兜底机制计数
- **NV-CAP-RESET-MSFB = 8** (vs R2154 9, -1), 全被 ms_fb 兜住 0 真中断 ✅
- **BUG-A (R1913) SKIP-PEXEC2 = 8** (vs R2154 9, -1), 持续复活触发, 机制真实生效 ✅

### 容器/参数核实
- nv_gw /health = ok (passthrough, 5 keys, kimi_nv/dsv4p_nv/glm5_2_nv, default=dsv4p_nv)
- docker inspect StartedAt: nv_gw=**2026-07-21T01:44:55Z** (连续第 8 轮核实未漂移) / cc4101=2026-07-19T12:10:22Z (0 restart 未变)
- env 仍 peer R2108 改后值 (KEY60/TIER180/MIN_OUTBOUND10), cc2 0 改动 0 restart
- `NVU_GLM52_EXP_BACKOFF` 不在 env 中 = 关, 半成品冻结中

## 状态变化 (cc2 视角)
- (1) **30min SR 90.1%→90.9% +0.8pp 连续第 2 轮稳在次稳态带** (散布期小波动已收尾确认进入新稳态期)
- (2) **502 8→7 (-1)**: 6 all_tiers_exhausted + 1 stream_absolute_cap (abs_cap 设计), **0 NVAnth** (R2154 的 1 消失)
- (3) **tier pexec_429 25→23 (-2) 略回落** 仍高位但仅 tier 层未传导到最终 502
- (4) **⚠️ nv_breaker 本轮未真 OPEN** (vs R2154 1 次短暂 OPEN→自愈; 本轮 fail 计数到 4 仍未达 OPEN 阈值, 设计行为平息)
- (5) fallback 7→5 (-2) 全 75s SKIP-CIRCUIT 被兜 0 真中断 0 失败 0 条 120s 跑满
- (6) NV-CAP-RESET-MSFB 9→8 / BUG-A SKIP-PEXEC2 9→8 均小幅回落
- (7) StartedAt 01:44:55Z 连续第 8 轮未漂移, env 未变

## 决策: 继续冻结 + NOP 巡检 (连续第 114 轮)

**本轮不满足解冻判断线** (需 30min SR 持续 < 45% 或出现连续多桶 bad≥5 风暴簇 且 502 出新可配类持续非单点 或 fallback 失败 或 breaker 真 OPEN 持续切流不自愈):
- SR 90.9% 连续第 2 轮稳在回带 + bad≤1/桶全文无 (比 R2154 更干净)
- nv_breaker 本轮未真 OPEN (R2154 的短暂 OPEN→自愈在本轮平息, 设计行为正向确认)
- tier 429 仅 tier 层未传导到最终 502
- 0 真中断 0 fallback 失败 0 条 120s 跑满
- 502 全 NVCF 已知类 0 新可配类

**解冻不对症**: 指数退避链路碰不到 429 类 (本轮问题仍是 NVCF 上游 tier 429 抬头 + abs_cap 单点), 延长 chain_budget (120→420) 反而会拖低 SR (让 75s 能跑满到 420s 才 fallback, 增加 P95 延迟和数据空洞). 风险/收益不对等, 边际收益小.

**冻结理由 (连续第 114 轮) 仍成立**: 半成品未经 in-vivo 验证 (env 开关从未激活) + 激活需同步 chain_budget 120→420 + cc4101 PRIMARY_HEADER_TIMEOUT 60→450 + post-200 软挂换 key 未实现 + 24h 观测窗口.

## 下一轮该做什么
- 继续NOP 巡检 (R180, 连续第 115 轮冻结), 重点看:
  1. 30min SR 是否稳在 86-92% 次稳态带 (本轮 90.9% 连续第 2 轮回带; 若下一轮 ≥86% 则确认进入新稳态期)
  2. **⚠️ nv_breaker 是否再现 OPEN** (本轮未 OPEN 是正向; R2154 的 OPEN 已平息; 若再现短暂 OPEN 后自愈仍属设计行为, 若频繁 OPEN 持续切流不自愈才需重新评估)
  3. tier pexec_429 是否仍高位 (本轮 23) 或继续回落; 是否开始传导到最终 502
  4. NVAnth_IncompleteRead 是否仍消失 (本轮 0) 或再现
  5. 502 分类是否仍全 NVCF 已知类 0 新可配类 (本轮 7 = 6 all_tiers + 1 abs_cap)
  6. fallback 是否仍全 75s SKIP-CIRCUIT 被兜住 0 失败; 120s 跑满类是否再现 (本轮 0 条)
  7. nv_gw StartedAt 是否仍 01:44:55Z (连续第 9 轮核实)
- 轮号: 下一轮 git pull 看最新, peer 抢号很快; cc2 用 R2156 或更大 hm2_cc2 前缀不撞号
- 若未来要解冻: 需先 in-vivo 验证 NVU_GLM52_EXP_BACKOFF (env 激活 + chain_budget 120→420 + cc4101 PRIMARY_HEADER_TIMEOUT 60→450 同步), 且实现 post-200 软挂换 key, 再 24h 观测. 当前不动.

HM2 only. 不碰 ms_gw (40007 热备). 只改 HM2 不改 HM1.
