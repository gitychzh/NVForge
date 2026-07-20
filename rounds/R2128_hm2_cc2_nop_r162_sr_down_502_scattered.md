# R2128 (hm2_cc2) — NOP R162 连续第 97 轮冻结

> 日期 2026-07-21 CST 07:08 / UTC 23:08。本 session 拉取 + 写入。
> 连续第 97 轮 NOP 冻结指数退避 (R1928 冻结 → R1929...R2127/R2128 NOP)。
> 0 改动 0 restart。HM2 only, 不碰 HM1, 不碰 ms_gw。

## 改前数据 (30min 窗口, UTC 22:38→23:08, 拉取时刻 23:08 UTC)

- **nv_gw 30min SR = 44/75 = 58.7%** (200:44 / 502:31)
  - vs R2127 61.8% (47/76): -3.1pp, **延续下滑但降幅收窄** (R2126→R2127 -10.8pp, R2127→R2128 -3.1pp, 斜率趋平)
  - vs R2124 92.2% 稳态核心: -33.5pp, 仍跌出 86-92% 次稳态带
  - 驱动未变: 散布型 NVCF 上游 all_tiers_exhausted 502

- **1min 桶完整轨迹 (UTC, 40min, 22:29→23:09)**:
  - 22:29-36 稳态带 (22:29/31/32/36 SR100%, 22:30/33/34/35 SR50-75%) bad≤1/桶
  - 22:37-44 散布加重 (22:37 bad=2 SR33%, 22:40 bad=2 SR0%单桶, 22:43 bad=2 SR33%, 22:44 bad=1 SR0%单桶) bad≤2/桶
  - 22:45-57 散布收尾 (22:45/50/53/55 SR50%, 22:46/47/56/57 SR67-80%, 22:51 SR100%) bad≤2/桶
  - 22:58-23:09 **回稳带** (22:59/23:00/23:03/23:08/23:09 桶 SR100%, 22:58/23:06 SR67%)
    - 23:04/05 有单桶 SR0% (bad=3+2), 23:07 单桶 SR0% (bad=1) — 仍是单桶散布非簇
  - **全程 bad≤3/桶 (仅 23:04 bad=3 单桶), 无连续多桶 bad≥5 风暴簇**
    (对比 R2120/R2121 风暴主峰 bad 5-10/桶 连续多桶; R2126 22:35-40 bad 5-6/桶)
  - 暂判: 散布期延续, R2126 短簇风暴已收尾, 22:58 后似在回稳 (与 R2127 的 22:45-51 回稳带一致延续)

- **30min 502 = 31 全 NVCF 已知类 0 新可配置类** ✅
  - all_tiers_exhausted ×28 + zombie_empty_completion ×3
  - vs R2127 29 → 31 (+2, 散布非簇, 仍已知类)

- **tier 30min**: pexec_success ×35 + pexec_conn_RemoteDisconnected ×2 + NVCFPexecRemoteDisconnected ×1
  - **429_nv_rate_limit = 0** (不在列表, 第4波 429 仍滚出 30min 窗口) ✅
  - **0 SSLEOFError** ✅
  - vs R2127: pexec_success 39→35 (-4), NVCFPexecRemoteDisconnected 4→0→1 (低位), pexec_conn_RemoteDisconnected 1→2 (+1)
  - tier 层整体量略降, 仍已知类无新可配类

- **NV-CAP-RESET-MSFB = 7 条** (R1818 bug7 cap_origin reset 机制 execute→ms_fb path 正常触发, 全被 ms_fb 兜住 0 真中断)
  - vs R2127 6 → 7 (+1, 散布期持续增多, 但全被兜住)

- **fallback = 7** FALLBACK-OK (0 真中断, 0 fallback 失败):
  - 全 7 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (header/ttfb 75s < chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类)
  - **0 条 120s 跑满类** (持平 R2127) ✅
  - req 样本: 91bf9ac0 (06:51) / 84c57d15 (06:54) / 6d532275 (07:01) / b3dc262c (07:04) + 3
  - vs R2127 6 → 7 (+1)
  - cc4101 `grep -cE "both failed|UPSTREAM-ERROR-SEEN"` 30min = **0** → 0 真中断确认

- **breaker cc4101 PRIMARY-BREAKER-OPEN 30min = 0; nv_gw 30min `grep -cE "BREAKER"` = 0** (state 未 OPEN, 连续第 30 轮) ✅

- **BUG-A 修复 (R1913) 生效确认**: 30min 内 `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **7 次** (vs R2127 6 → 7 +1, 持续复活触发中, 机制真实生效) ✅

- **abs_cap 30min = 0** (grep abs_cap|NV-ABS, 对应 CAP-RESET 机制在另一标记; CAP-RESET 7 条正常) ✅

- **nv_gw /health = ok** (passthrough, 5 keys, kimi_nv/dsv4p_nv/glm5_2_nv, default=dsv4p_nv)
- **docker inspect StartedAt 核实**: nv_gw=18:10:28Z (R2107 后未再漂移, 连续第 17 轮核实 18:10 稳定) / cc4101=12:10:22Z (0 restart 未变)

## 状态变化 (cc2 视角)

nv_gw StartedAt 仍 18:10:28Z (连续第 17 轮核实未漂移), env 仍 peer R2108 改后值 (KEY60/TIER180/MIN_OUTBOUND10), cc2 0 改动 0 restart.

本轮需记录的变化:
1. **30min SR 61.8%→58.7% 延续下滑** (-3.1pp, 降幅收窄 vs R2127 -10.8pp, 仍跌出 86-92% 次稳态带, 散布型 502 延续但 22:58 后似回稳)
2. 502 29→31 (+2, 全 all_tiers_exhausted×28+zombie×3 NVCF 已知类 0 新可配类; bad≤3/桶散布非簇)
3. tier 429_nv_rate_limit=0 持平 (第4波 429 仍滚出)
4. tier pexec_success 39→35 (-4), NVCFPexecRemoteDisconnected 1 (低位), pexec_conn_RemoteDisconnected 2 (+1), 整体量略降
5. fallback 6→7 (+1) 全 75s SKIP-CIRCUIT 被兜 0 真中断 0 失败 0 条 120s 跑满
6. NV-CAP-RESET-MSFB 6→7 (+1) / BUG-A SKIP-PEXEC2 6→7 (+1)
7. breaker/abs_cap 全部未恶化, breaker 仍未 OPEN 连续第 30 轮, StartedAt 未漂移连续第 17 轮

## 解冻判断 (连续第 97 轮冻结仍成立)

STATE 下一步判断线 "30min SR 持续 < 85% **非风暴污染** 且 502 出新可配置类 或 fallback 失败 或 breaker 真 OPEN 切流" 才考虑重新评估解冻.

本轮:
- SR=58.7% < 85% ✓ 但...
- 502 全 NVCF 已知类 (all_tiers_exhausted + zombie) **0 新可配置类** ✓ (不满足)
- 0 真中断 (cc4101 both failed=0) ✓
- 0 fallback 失败 (全 7 条 75s SKIP-CIRCUIT 被 ms_gw 兜住) ✓
- breaker 未 OPEN (连续第 30 轮) ✓

**结论: 不满足解冻条件, 继续 NOP 巡检 (连续第 97 轮冻结).**
本轮问题是 NVCF 上游 all_tiers_exhausted 散布期 (非 429 非软挂), 指数退避链路碰不到此错误类, 延长 chain_budget 反拖 SR (十二轮论证: R2111/2116/2119/2120/2121/2122/2123/2124/2125/2126/2127/2128).

## 验证

0 改动 0 restart, 无需验证改动. 确认 nv_gw /health=ok + docker inspect StartedAt=18:10:28Z 未漂移 (连续第 17 轮) + cc4101 StartedAt=12:10:22Z 未变 + docker ps 正常.

## 仓库与铁律

- 仓库: ~/hm_ps/hermes_improve_self (remote git@github.com:gitychzh/NVForge.git, branch main)
- 本轮 commit: 见 git log
- HM2 only, 不碰 HM1, 不碰 ms_gw (40007 是 restart 窗口热备)
- env NVU_GLM52_EXP_BACKOFF 不在 env 中 = 关, 半成品冻结中 (从未 in-vivo 激活)
- chain_budget 仍 120s, 未升 420
