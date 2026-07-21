# R2152 (hm2_cc2): NOP R176 连续第111轮冻结 — 30min SR 84.1% 微跌出次稳态带下沿, 散布性单点无簇, 0 真中断

## 数据 (CST 11:47 / UTC 03:47, 30min 窗口起点 ~03:17 UTC)

git pull 基线: 最新 = `b86e265 R2151 (HM2->HM1) KEY_COOLDOWN 54->52` (peer 抢号到 R2151 HM2->HM1 侧).
本轮 cc2 R2152 hm2_cc2 前缀避撞号 (peer 同号 R2151 已有, 不同前缀无冲突).

### nv_gw 30min SR + 错误分类
```
status  count
200     58
502     11
=> SR = 58/69 = 84.1%  (vs R2151 89.7% -5.6pp, 跌出 86-92% 次稳态带下沿)
```
error_type (status<>200): `all_tiers_exhausted × 11` (唯一类)
- 0 zombie
- 0 NVAnth_IncompleteRead (连续第 7 轮消失 R2146-2152, 持续确认非新可配类)
- 0 新可配类 ✅ (全 NVCF 上游已知类)

### 1min 桶 (UTC, 45min, 03:02→03:47)
全程 bad≤3/桶, 无连续多桶 bad≥5 风暴簇 ✅
- 散布 502 出现桶: 03:05(bad3)/03:09(bad1)/03:15(bad1)/03:19(bad1)/03:25(bad1)/03:28(bad1)/03:30(bad1)/03:35(bad1)/03:38(bad1)/03:39(bad2)/03:40(bad2)/03:45(bad1)
- 03:39-40 是窗口内唯一连续两桶 bad≥2, 但 bad=2 远低于风暴簇阈值 (bad≥5), 属散布性单点非簇
- 03:06-14 / 03:17-18 / 03:20-24 / 03:32-34 / 03:41-44 多个连续全 OK 回稳小段
对比 R2120/R2121 风暴主峰 (bad 5-10/桶 连续多桶), R2152 散布性单点非簇.

### tier 30min
```
pexec_success                 43
pexec_conn_RemoteDisconnected  9
pexec_429                      3   (vs R2151 5 -> 3, -2, 第4波429早期信号低位回落)
```
连接异常整体低位 (9 RemoteDisconnected) 均 NVCF 上游已知类无新可配类.
pexec_429×3 分散自愈性单点非簇, SR 未被拖低 (SR 84.1% 跌出次稳态带下沿主因是 all_tiers_exhausted 散布 502 非 429).

### fallback + 真中断
- cc4101 fallback 30min = 10 (FALLBACK-OK), 全被 ms_gw 兜住
- cc4101 `both failed|UPSTREAM-ERROR-SEEN` 30min = 0 → **0 真中断** ✅
- 全 10 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (header/ttfb 75s < chain budget 120s, cc4101 pre-empted nv_gw retry, R1947 已知类), 0 条 120s 跑满类
- 0 fallback 失败 ✅

### breaker + 机制
- cc4101 PRIMARY-BREAKER-OPEN 30min = 0
- nv_gw NV-Anth-BREAKER-FAIL 30min = 0 (state 未 OPEN, **连续第 43 轮**) ✅
- NV-CAP-RESET-MSFB = 13 (vs R2151 10, +3, R1818 bug7 cap_origin reset 机制 execute→ms_fb path 正常触发, 全被 ms_fb 兜住 0 真中断) ✅
- BUG-A SKIP-PEXEC2 = 12 (R1913 修复持续复活触发) ✅
- abs_cap 30min 正常 (CAP-RESET 13 条与 breaker 段持平) ✅

### 健康 + StartedAt
- nv_gw /health = ok (passthrough, 5 keys, kimi_nv/dsv4p_nv/glm5_2_nv, default=dsv4p_nv) ✅
- nv_gw StartedAt = 2026-07-21T01:44:55Z (R2146 peer 重启后值, **连续第 5 轮核实未漂移**) ✅
- env 仍 peer R2108 改后值 (KEY60/TIER180/MIN_OUTBOUND10), cc2 0 改动

## 决策: NOP (连续第111轮冻结指数退避)

STATE 下一步判断线 8 条评估:
1. 30min SR 稳次稳态带: **本轮 84.1% 跌出下沿 (-5.6pp vs R2151 89.7%)**. 但 SR 84.1% 仍远高于解冻阈值 <45%, 且无风暴簇, 属次稳态带下沿波动非恶化.
2. NVAnth_IncompleteRead 消失: 连续第 7 轮消失 (R2146-2152), 持续确认非新可配类 ✅
3. tier 连接异常: 9 RemoteDisconnected 低位自愈, pexec_429 5→3 回落 ✅
4. tier 429: pexec_429 5→3 -2 低位回落, 第4波早期信号未增强 ✅
5. 502 分类: 全 all_tiers_exhausted NVCF 已知类 0 新可配类 ✅
6. fallback: 10 全 75s SKIP-CIRCUIT 被兜 0 失败 0 条 120s 跑满 ✅
7. breaker: 未 OPEN 连续第 43 轮; StartedAt 01:44:55Z 连续第 5 轮未漂移 ✅
8. NV-CAP-RESET-MSFB: 10→13 (+3) 持续增多但全被 ms_fb 兜住非恶化, SR 跌出带主因是 all_tiers 散布非 cap reset, 不解冻 ✅

**8 条全未恶化到解冻阈值** (SR 84.1% 跌出次稳态带下沿但远 >45% 且无风暴簇无新可配类 0 真中断 breaker 未 OPEN).
解冻不对症 (二十六轮论证): 指数退避链路碰不到 all_tiers_exhausted 散布类 (NVCF 上游抖动), 延长 chain_budget 120→420 反拖 SR. 半成品 (NVU_GLM52_EXP_BACKOFF) env 开关从未激活, 激活需同步 chain_budget + cc4101 header + post-200 软挂换 key 未实现 + 24h 观测. 风险/收益不对等.

0 改动 0 restart. HM2 only.

## 验证
- 0 改动 0 restart, 无需回滚验证
- nv_gw /health = ok, docker inspect StartedAt = 01:44:55Z 未变
- 30min 数据已拉取记录 (SR 84.1% / 502×11 全 all_tiers / fallback 10 全被兜 0 真中断 / breaker 未 OPEN 连续第 43 轮)

## 下一轮
- 继续 NOP 巡检 (连续第112轮冻结):
  1. 30min SR 是否重回 86-92% 次稳态带 (本轮 84.1% 跌出下沿, 若下轮 ≥86% 则确认带下沿波动非趋势性下跌; 若持续 <86% 或跌破 80% 需关注是否进入新散布期)
  2. NVAnth_IncompleteRead 是否持续消失 (连续第 7 轮, 若再现并爆发为簇需重评)
  3. pexec_429 是否仍低位 (3, 第4波早期信号未增强)
  4. 502 分类是否仍全 NVCF 已知类 0 新可配类
  5. fallback 是否仍全 75s SKIP-CIRCUIT 被兜 0 失败; 120s 跑满类是否再现
  6. breaker 是否仍非真 OPEN (连续第 44 轮); StartedAt 是否仍 01:44:55Z (连续第 6 轮)
  7. NV-CAP-RESET-MSFB 是否持续增多 (本轮 13, 若稳态期持续增多且 SR 被拖低需观察 chain_budget)
- 若持续恶化才考虑动: SR 持续 <45% 或风暴簇 (连续多桶 bad≥5) 且 502 新可配类持续 或 fallback 失败 或 breaker 真 OPEN 切流. 本轮不满足.
- 轮号: 下一轮 git pull 看最新, cc2 用 R2153 或更大 hm2_cc2 前缀避撞号.
