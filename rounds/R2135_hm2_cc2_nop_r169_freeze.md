# R2135 (hm2_cc2) — NOP R169, 连续第 104 轮冻结

> 本轮 = 巡检轮。0 改动 0 restart。HM2 only, 不碰 HM1, 不碰 ms_gw。

## 改前数据 (CST 08:43 / UTC 00:43, 窗口起点 ~00:13 UTC)

nv_gw 30min SR = 41/77 = **53.2%** (200:41 / 502:36).
vs R2134 51.3% → **+1.9pp 小回升** (R2132 57.3 / R2133 57.0 / R2134 51.3 / R2135 53.2,
散布期延续但本轮小幅回升, vs R2124 92.2% -39.0pp 仍跌出次稳态带).

**1min 桶完整轨迹 (UTC, 40min, 00:04→00:44)**:
- 00:04-06 散布起 (00:04 桶 1×200, 00:05 桶 2×502, 00:06 桶 1×200)
- 00:07-11 散布加重 (00:07 桶 3×502 单峰, 00:08 桶 3×200+1×502, 00:09-11 各 2×502)
- 00:12-14 小回稳 (00:14 桶 2×200+1×502)
- 00:15-17 回稳带 (00:15 桶 4×200+1×502, 00:16 桶 2×200+1×502, 00:17 桶 4×200)
- 00:18 散布又起 (00:18 桶 3×200+3×502 单峰)
- 00:20-24 散布延续 (00:21 桶 2×502, 00:22 桶 2×200+2×502, 00:23 桶 2×200+1×502, 00:24 桶 1×200+2×502)
- 00:26-27 散布 (00:27 桶 3×502 单峰)
- 00:28-29 小回稳 (00:28 桶 2×200, 00:29 桶 2×502)
- 00:30-32 部分回稳 (00:30 桶 2×200+1×502, 00:31 桶 4×200, 00:32 桶 3×200+2×502)
- 00:33-36 散布 (00:33 桶 1×502, 00:35 桶 1×200+2×502, 00:36 桶 1×200+1×502)
- 00:38-43 散布 (00:38 桶 2×502, 00:39 桶 2×200+2×502, 00:40-41 各 1×502, 00:42 桶 3×200+1×502, 00:43 桶 2×200+2×502)
- 00:44 收尾 (00:44 桶 1×200)
- **全程 bad≤3/桶, 无连续多桶 bad≥5 风暴簇** (对比 R2126 22:35-40 bad 5-6/桶 连续多桶).
  暂判散布期延续 (非风暴簇), 与 R2131-R2134 同一散布期延续, 本轮小幅回升 (+1.9pp) 但未确认趋势反转.

502×36 全 **all_tiers_exhausted×36** (0 zombie, 0 NVAnth_IncompleteRead —
**NVAnth_IncompleteRead 本轮单点消失, 持续确认非新可配类** ✅ STATE 下一步重点②已验证).
0 新可配置类 ✅. vs R2134 37 → 36 (-1, 散布量略降持平).

tier 30min: pexec_success×34 + pexec_conn_RemoteDisconnected×3 + NVCFPexecRemoteDisconnected×1 +
pexec_SSLEOFError×1 + pexec_empty_200×1.
**429_nv_rate_limit = 0** (第4波 429 仍滚出 30min 窗口) ✅.
vs R2134: pexec_success 29→34 (+5), pexec_conn_RemoteDisconnected 5→3 (-2 回落),
NVCFPexecRemoteDisconnected 1→1 持平, SSLEOFError 0→1 (+1 低位), pexec_empty_200 0→1 (+1 低位),
连接异常整体低位均 NVCF 已知类无新可配置类.

**NV-CAP-RESET-MSFB = 6 条** (R1818 bug7 cap_origin reset 机制 execute→ms_fb path **正常触发**,
全被 ms_fb 兜住 0 真中断. vs R2134 8 → 6 -2) ✅.
**BUG-A 修复 (R1913) 生效**: NV-GLM52-CHAIN-SKIP-PEXEC2 触发 **6 次** (vs R2134 8 -2, 持续复活触发中) ✅.

fallback **8** FALLBACK-OK (0 真中断, 0 fallback 失败):
全 8 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (header/ttfb 75s < chain budget 120s,
cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类).
**0 条 120s 跑满类** ✅. req 样本: 9bdef2f0 / 9351ce41 / 1fce4bd7 / eecb40c0 / 03eb76ed (+3).
R2134 fallback 10 → 本轮 8 (-2). cc4101 `grep -cE "both failed|UPSTREAM-ERROR-SEEN"` 30min = **0** → 0 真中断确认.

breaker cc4101 PRIMARY-BREAKER-OPEN 30min = **0**;
nv_gw 30min `grep -cE "NV-Anth-BREAKER-FAIL"` = **0** (state 未 OPEN, 连续第 37 轮) ✅.

**abs_cap 30min 正常** (CAP-RESET 6 条, 与 breaker 段持平) ✅.
nv_gw /health = ok (passthrough, 5 keys, kimi_nv/dsv4p_nv/glm5_2_nv, default=dsv4p_nv).
docker inspect StartedAt 核实 nv_gw = **18:10:28Z** (R2107 后未再漂移, 连续第 24 轮核实稳定) /
cc4101 = 12:10:22Z (0 restart 未变).

## 改动

**0 改动 0 restart** (NOP R169, 连续第 104 轮冻结指数退避).
- env 未变 (peer R2108 改后值 KEY60/TIER180/MIN_OUTBOUND10, 非 cc2 改; NVU_GLM52_EXP_BACKOFF 不在 env = 关, 半成品冻结中; chain_budget 仍 120s 未升 420).
- cc2 本轮 0 改 0 restart, 与 R2129-R2134 一致.

## 决策依据 (为何 NOP)

STATE 下一步判断线 8 条全未恶化:
1. SR 虽低位但本轮小回升 (+1.9pp) 散布非簇 (bad≤3/桶无连续多桶 bad≥5), 非 SR 持续 <85% 风暴污染.
2. 502 全 NVCF 已知类 (all_tiers_exhausted×36), NVAnth_IncompleteRead 单点消失持续确认非新可配类.
3. tier 连接异常整体低位 (pexec_conn_RemoteDisconnected×3, NVCFPexecRemoteDisconnected×1, SSLEOFError×1, pexec_empty_200×1) 均 NVCF 已知类.
4. tier 429_nv_rate_limit=0 (第4波仍滚出).
5. fallback 8 全 75s SKIP-CIRCUIT 被兜住 0 失败, 0 条 120s 跑满.
6. breaker 未 OPEN (连续第 37 轮).
7. StartedAt 未漂移 (连续第 24 轮).
8. NV-CAP-RESET-MSFB 6 条全被 ms_fb 兜住 0 真中断 (R1818 机制正常).

**解冻不对症** (十九轮论证): 本轮问题是 NVCF 上游 all_tiers_exhausted 散布期 (RemoteDisconnected/SSLEOFError/all_tiers_exhausted),
指数退避链路 (per-key 60/120/240 + chain_budget 420) 碰不到此错误类 — all_tiers_exhausted 是
NVCF 上游所有 tier/key 都拒绝/超时的终态, 退避重试无新 key 可换. 延长 chain_budget 120→420 反而
把 502 拖成更慢的 502, 拖低 SR. 故继续冻结.

## 验证结果

- 0 改动 0 restart, 无需回滚.
- nv_gw /health = ok, docker ps 正常.
- 下一窗口 (下一轮拉取) 确认散布期是否收尾或延续.

## 坐标

- 仓库 commit: 本轮 (hm2_cc2 前缀避 peer hm2_optimize_hm1 撞号).
- HM2 only. 不碰 HM1, 不碰 ms_gw (40007 重启窗口热备).
