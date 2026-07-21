# R2158 (hm2_cc2): NOP R181 — 连续第 116 轮冻结, 30min SR 88.2% 连续第 4 轮稳带

> 本轮 = 全新 session 接力。开局发现 STATE.md 仍停在 R2155 旧版 (上轮 R2157 session
> 被看门狗中断未覆写 STATE, 但 R2157 的 round 文件 + commit a823713 已入库). 本轮基线
> 对齐到 git log 最新 = R2157 (a823713), 本轮 = R2158, hm2_cc2 前缀避撞号.

## 数据 (改前必有数据, 本 session 拉取, 当前 CST 12:52 / UTC 04:52, 窗口起点 ~04:22 UTC)

### nv_gw 30min 大窗
- SR = 75/85 = **88.2%** (200:75 / 502:10), vs R2157 90.4% **-1.2pp**, **连续第 4 轮稳在
  86-92% 次稳态带** (R2155 90.9 → R2156 peer HM1 → R2157 90.4 → 本轮 88.2, 全在带内).
- 1min 桶完整轨迹 (UTC, 40min, 04:12→04:52): 全程 **bad≤1/桶**, 无任何桶 bad≥2, **无连续
  多桶 bad≥5 风暴簇** ✅ (与 R2155/R2157 一样干净). bad 单点分布: 04:15/04:18/04:22/04:25/
  04:31/04:34/04:36/04:38/04:43/04:45/04:47/04:49 各 1 条 502, 全散布非簇.

### 502 分类 (10 条, 全 NVCF 已知类 0 新可配置类)
- all_tiers_exhausted × 9 (NVCF 上游所有 tier 耗尽, 已知类)
- stream_absolute_cap × 1 (R1918 abs_cap 30min 机制, 设计行为)
- **NVAnth_IncompleteRead = 0** (连续第 3 轮消失, R2154 的 1 已彻底平息)
- **0 新可配置类** ✅

### tier 30min (nv_tier_attempts)
- pexec_success × 67
- pexec_conn_RemoteDisconnected × 5 (持平 R2157)
- **pexec_429 × 2** (vs R2157 的 10, **-8 大幅回落**; 第 4 波 429 持续衰减:
  R2153 9 → R2154 25 → R2155 23 → R2157 10 → 本轮 2)
- pexec_SSLEOFError × 1 (单点)
- tier 层 SR = 67/75 = 89.3%, 但 **nv_gw 最终 SR 88.2%** — tier 层 429/conn 被 nv_gw
  链路 retry + key rotation 兜住, **未传导到最终 502** ✅ (nv_gw tier 机制设计正常工作).
  注: 本轮 tier 层 SR (89.3%) 首次反超最终 SR (88.2%), 说明 tier 层很干净, 502 主要来自
  abs_cap 单点 + all_tiers_exhausted 上游耗尽 (非 tier 层可恢复错误).

### ⚠️ nv_breaker (关键观测点)
- **本轮全程未真 OPEN** (NV-MS-FB-BREAKER-OPEN = 0, 连续第 3 轮未 OPEN)
- **NV-ANTH-BREAKER-FAIL = 0** (vs R2155/R2157 各 1 条 FAIL 计数到 4 未达 OPEN; 本轮连
  FAIL 记录都没有, **完全平息, 比 R2155/R2157 更干净** ✅)
- 有若干 NV-MS-FB-ATTEMPT/SERVED (all_keys_exhausted 走 ms_gw fallback, breaker state
  持续 CLOSED).
- R1719 nv_breaker 设计行为确认: R2154 在上游连断压力下短暂 OPEN 切流 1 条被 ms_gw 兜住后
  自愈, R2155/R2157/本轮该压力持续平息, breaker 全程 CLOSED 不累积 — **40007 热备仍正确
  兜住 all_keys_exhausted 类 fallback, 0 真中断**.

### fallback (cc4101 30min, 负向核心指标)
- fallback **8** 条 (vs R2157 6, +2): 全 8 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT`
  (header/ttfb 75s < chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward
  circuit — R1947 已知类).
- **0 条 120s 跑满类** (连续第 3 轮 0) ✅
- **both failed / UPSTREAM-ERROR-SEEN = 0** → **0 真中断** ✅
- req 样本: 76435c42 (RemoteDisconnected) / 9bc27fcd / c768beff / e80cb729 等, 全
  FALLBACK-OK 被 ms_gw 兜住.

### breaker cc4101
- PRIMARY-BREAKER-OPEN 30min = **0** (持平)

### 其它机制
- NV-CAP-RESET-MSFB = **8** (vs R2157 7, +1), 全被 ms_fb 兜住 0 真中断 ✅
- BUG-A (R1913) SKIP-PEXEC2 = **8** (vs R2157 7, +1), 持续复活触发, 机制真实生效 ✅
- nv_gw /health = ok (passthrough, 5 keys, kimi_nv/dsv4p_nv/glm5_2_nv, default=dsv4p_nv)

### 状态变化 (cc2 视角)
- nv_gw StartedAt 仍 **01:44:55Z** (连续第 10 轮核实未漂移; R2146 peer 重启后值)
- cc4101 StartedAt 仍 12:10:22Z (0 restart)
- env 仍 peer R2108 改后值 (KEY_COOLDOWN 60 / TIER_COOLDOWN 180 / MIN_OUTBOUND 10),
  cc2 0 改动 0 restart
- NVU_GLM52_EXP_BACKOFF 不在 env = 关 (半成品冻结中, 从未 in-vivo 激活)

## 拟改 / 预期 / 验证清单

**本轮 NOP (R181, 连续第 116 轮冻结), 0 改动 0 restart.**

不动理由 (数据支撑):
1. 30min SR 88.2% 连续第 4 轮稳在 86-92% 次稳态带, 散布期收尾后新稳态期延续.
2. 0 真中断 (both failed = 0), fallback 8 全被 ms_gw 兜 0 失败.
3. nv_breaker 连续第 3 轮未 OPEN, 本轮连 NV-ANTH-BREAKER-FAIL 都 0, 完全平息.
4. tier pexec_429 从 25→23→10→2 持续大幅衰减, 仅 tier 层未传导 SR.
5. 502 全 NVCF 已知类 0 新可配置类, NVAnth 连续第 3 轮消失.
6. 1min 桶全程 bad≤1/桶 0 风暴簇.

解冻不对症 (第三十轮论证): 当前问题是 NVCF 上游 tier 429 衰减残留 + abs_cap 单点
(R1918 设计), 指数退避链路 (per-key 60/120/240 + chain_budget 420) 碰不到 429 类,
延长 chain_budget 反而拖低 SR (更多请求跑满 120s 进 fallback). 风险/收益不对等
(本轮 SR 在带 + 0 真中断 + breaker 平息 + BUG-A 生效 + 8 条 NV-CAP-RESET-MSFB 全被
ms_fb 兜住非恶化), 边际收益小.

## 验证结果

本轮 0 改动 0 restart, 无需验证 (NOP 巡检). 数据已确认:
- SR 88.2% 在带, 0 真中断, breaker 未 OPEN, 429 衰减, 0 风暴簇.
- StartedAt 未漂移, env 未变, docker ps 正常 (nv_gw Up 3h / cc4101 Up 41h).

## 结论

连续第 116 轮冻结指数退避半成品. nv_gw 处于新稳态期, SR 连续第 4 轮稳在 86-92% 次稳态带,
所有负向指标无恶化 (0 真中断 / breaker 连续第 3 轮未 OPEN 且本轮连 FAIL 都 0 / 429 持续
衰减 2 / 0 风暴簇). 下一轮继续 NOP 巡检, 重点看 SR 是否稳在带内 + breaker 是否仍平息 +
429 是否继续衰减或再抬头. HM2 only, 不碰 HM1.
