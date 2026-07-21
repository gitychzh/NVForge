# R2137 (hm2_cc2) — NOP R171 连续第 106 轮冻结

> 铁律:改前必有数据,改后必有验证,聚焦 40006,不碰 40007,写入仓库,改.py 必须 restart, 只改 HM2 不改 HM1.

## 决策: NOP 巡检 (R171, 连续第 106 轮冻结指数退避)

依据 STATE (R2136) "下一轮该做什么" 判断线 8 条全未恶化到解冻阈值:
1. 30min SR 49.4%→48.8% -0.6pp 小幅回落散布期延续 (非 <45% 阈值, 非风暴簇)
2. NVAnth_IncompleteRead 仍连续第 6 轮消失 (R2132-2137, 已确认非新可配类)
3. tier 连接异常整体低位 (pexec_conn_RemoteDisconnected 2→4 +2 低位抬头, 非 500_nv_error/SSLEOFError/empty_200 持续类)
4. tier 429_nv_rate_limit 仍=0 (第4波 429 仍滚出)
5. 502 全 NVCF 已知类 0 新可配置类 (all_tiers_exhausted×39 + zombie×2)
6. fallback 全 75s SKIP-CIRCUIT 被兜 0 失败 0 条 120s 跑满
7. breaker 仍未真 OPEN (连续第 39 轮); StartedAt 仍 18:10:28Z (连续第 26 轮未漂移)
8. NV-CAP-RESET-MSFB 5 条 (持平 R2136, 非 SR 拖低主因)

本轮问题仍是 NVCF 上游连接抖动散布期 (RemoteDisconnected/all_tiers_exhausted), 指数退避链路碰不到此错误类, 延长 chain_budget 反拖 SR → **解冻不对症 (二十一轮论证)**. 0 改动 0 restart.

## 数据 (本 session 拉取, 当前 CST 09:09 / UTC 01:09, 30min 窗口起点 ~00:39 UTC)

### nv_gw 30min 大窗
- SR = 39/80 = **48.8%** (200:39 / 502:41)
  - vs R2136 49.4% → -0.6pp 小幅回落 (散布期延续但本轮降幅收窄至 -0.6pp)
  - vs R2124 92.2% → -43.4pp 仍跌出 86-92% 次稳态带, 由散布型 all_tiers_exhausted 502 驱动非风暴簇

### 1min 桶轨迹 (UTC, 40min, 00:27→01:07)
00:27 桶 1×502 → 00:28 小回稳 (2×200) → 00:29-30 散布 (00:29 桶 2×502) → 00:31-32 回稳 (00:31 桶 4×200, 00:32 桶 3×200+2×502) → 00:33-36 散布 (00:35 桶 1×200+2×502) → 00:38-41 散布 (00:38 桶 2×502, 00:39 桶 2×200+2×502) → 00:42-44 小回稳 (00:42 桶 3×200+1×502, 00:44 桶 3×200+1×502) → 00:45-47 散布 (00:45 桶 1×200+2×502, 00:46 桶 2×502) → 00:48-50 小回稳 (00:48 桶 2×200+1×502) → 00:52-54 散布 (00:52 桶 2×200+2×502, 00:54 桶 1×200+3×502 单峰) → 00:55-57 回稳带 (00:55 桶 3×200+1×502, 00:56 桶 3×200, 00:57 桶 3×200+3×502) → 00:58-01:02 散布 (00:58/59 桶各 1×502, 01:00 桶 2×200+1×502, 01:01 桶 2×502, 01:02 桶 2×502) → 01:03-07 小回稳 (01:03 桶 1×200, 01:05 桶 2×200+3×502 含 2×zombie 单峰, 01:06 桶 1×200+1×502, 01:07 桶 1×200+1×502).
**全程 bad≤3/桶, 无连续多桶 bad≥5 风暴簇** (对比 R2120/R2121 风暴主峰 bad 5-10/桶 连续多桶, R2126 22:35-40 bad 5-6/桶). 暂判散布期延续, 本轮小回落 -0.6pp 降幅收窄, 未确认趋势恶化 (仍散布非簇).

### 502 分类 (30min)
- 502=41: all_tiers_exhausted×39 + **zombie_empty_completion×2** (vs R2136 all_tiers×38 + 0 zombie → 本轮 +1 all_tiers, +2 zombie)
  - zombie 2 条再现: 01:05:00 (req a32528f0) + 01:05:08 (req ae74ff28) — 单一桶 (01:05) 内 2 条单峰, 非连续多桶, 非持续. R2129 亦曾单点 1 条 (23:21), R2130-2136 连续 7 轮消失, 本轮再现 2 条仍非簇非持续. **持续确认 zombie 非新可配持续类** (STATE 下一步重点②已验证).
  - **0 NVAnth_IncompleteRead** (连续第 6 轮消失 R2132-2137, 已确认非新可配类) ✅
  - 全 NVCF 上游已知类, **0 新可配置类** ✅
  - vs R2136 38 → 41 (+3 散布量略增非簇)

### tier 30min (nv_tier_attempts)
- pexec_success×32 (vs R2136 32 持平)
- pexec_conn_RemoteDisconnected×4 (vs R2136 2 → +2 低位抬头)
- **429_nv_rate_limit = 0** (vs R2136 0 持平, 第4波 429 仍滚出 30min 窗口) ✅
- vs R2136: NVCFPexecRemoteDisconnected 1→0 (回落), SSLEOFError 1→0 (回落), pexec_empty_200 1→0 (回落)
- tier 层连接异常整体低位 (仅 pexec_conn_RemoteDisconnected +2), 均 NVCF 上游已知类无新可配置类 (STATE 下一步重点③已验证)

### NV-CAP-RESET-MSFB (30min)
- **5 条** (vs R2136 5 持平, R1818 bug7 已有 cap_origin reset 机制 execute→ms_fb path 正常触发, 全被 ms_fb 兜住 0 真中断) ✅

### fallback (cc4101, 30min)
- **7 条** FALLBACK-OK (0 真中断, 0 fallback 失败): 全 7 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (header/ttfb 75s < chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类)
- **0 条 120s 跑满类** (持平 R2136) ✅
- req 样本 (窗口内): e830c9b2 / 342c79fa / e7cbff80 / 8e32e277 / 4ef07634 (+ 2 条窗口边界)
- R2136 fallback 7 → 本轮 7 持平
- cc4101 `grep -cE "both failed|UPSTREAM-ERROR-SEEN"` 30min = **0** → 0 真中断确认 ✅

### breaker
- cc4101 PRIMARY-BREAKER-OPEN 30min = **0**
- nv_gw NV-Anth-BREAKER-FAIL 30min = **0** (state 未 OPEN, 连续第 39 轮) ✅

### BUG-A 修复 (R1913) 生效确认
- 30min 内 `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **5 次** (vs R2136 5 持平, 持续复活触发中, 机制真实生效) ✅

### abs_cap 30min
- CAP-RESET 5 条, 与 breaker 段持平, 机制正常 ✅

### nv_gw 健康 + StartedAt
- /health = ok (passthrough, 5 keys, kimi_nv/dsv4p_nv/glm5_2_nv, default=dsv4p_nv) ✅
- docker inspect StartedAt 核实: nv_gw=**2026-07-20T18:10:28Z** (R2107 后未再漂移, 连续第 26 轮核实 18:10 稳定) / cc4101=2026-07-19T12:10:22Z (0 restart 未变) ✅

## 状态变化 (cc2 视角)
无. nv_gw StartedAt 仍 18:10:28Z (连续第 26 轮核实未漂移), env 仍 peer R2108 改后值 (KEY60/TIER180/MIN_OUTBOUND10), cc2 0 改动 0 restart. 本轮需记录的变化:
1. **30min SR 49.4%→48.8% 小幅回落** (-0.6pp 降幅收窄, 散布期延续, 仍跌出次稳态带)
2. 502 38→41 (+3: all_tiers 38→39 +1, zombie 0→2 +2 再现非簇, NVAnth 连续第 6 轮消失)
3. tier 429_nv_rate_limit=0 持平 (第4波 429 仍滚出)
4. tier pexec_success 32→32 持平, pexec_conn_RemoteDisconnected 2→4 (+2 低位抬头), NVCFPexecRemoteDisconnected 1→0/SSLEOFError 1→0/pexec_empty_200 1→0 (均回落清零)
5. fallback 7→7 持平 全 75s SKIP-CIRCUIT 被兜 0 真中断 0 失败 0 条 120s 跑满
6. NV-CAP-RESET-MSFB 5→5 持平 / BUG-A SKIP-PEXEC2 5→5 持平
7. breaker/abs_cap 全部未恶化, breaker 仍未 OPEN 连续第 39 轮, StartedAt 未漂移连续第 26 轮

## 解冻判断
本轮不满足解冻条件 (二十一轮论证):
- SR<85% 但 SR 小回落散布非簇 (降幅收窄 -0.6pp) + 502 全 NVCF 已知类 (NVAnth 连续 6 轮消失, zombie 再现 2 条非簇非持续) + 0 真中断 + breaker 未 OPEN
- 解冻不对症: 本轮问题是 NVCF 上游连接抖动散布期 (RemoteDisconnected/all_tiers_exhausted), 指数退避链路碰不到此错误类, 延长 chain_budget 反拖 SR
- 半成品仍冻结 (NVU_GLM52_EXP_BACKOFF 不在 env=关, 从未 in-vivo 激活)

## 执行
0 改动 0 restart. env 与 R2136 完全一致 (peer R2108 改后值, 非 cc2 改). HM2 only.

## 验证
NOP 轮, 无 restart. /health=ok, docker ps nv_gw Up 7 hours (StartedAt 18:10:28Z 核实未漂移). 窗口日志确认 SR 未崩 (48.8% 仍散布非簇), fallback 全被兜 0 真中断.

R2137 (hm2_cc2)
