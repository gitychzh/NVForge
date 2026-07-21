# R2147 (hm2_cc2) — NOP R172, 连续第 107 轮冻结

- **日期**: 2026-07-21 CST 10:54 / UTC 02:54
- **模式**: nv 直连 (cc4101→nv_gw), 指数退避+ms 双层方案半成品冻结 (NVU_GLM52_EXP_BACKOFF 不在 env=关, 从未 in-vivo 激活)
- **改动**: 0 改动, 0 restart (NOP 巡检轮)

## 数据 (30min 窗口, 起点 ~02:24 UTC)

**nv_gw 30min SR = 83/92 = 90.2%** ✅ 重回 86-92% 次稳态带
(vs R2146 大窗 58.9% / 回稳带 90.7% → 本轮整窗 90.2%, **散布期瞬态已彻底收尾确认**;
 vs R2136 49.4% +40.8pp 大幅回升, R2146 回升趋势在本轮延续并整窗化)

**1min 桶完整轨迹 (UTC, 40min, 02:14→02:54)**:
- 02:14-22: 散布收尾尾段 (02:18 桶 bad=10 单点风暴簇, 02:19 bad=5, 02:21 bad=4 —
  此为窗口早期~36min前 R2146 记录的散布期尾段, 非新爆发)
- 02:23 起: 全面回稳带 (02:23-46 连续 24 分钟 SR 极高, 仅 02:25/27/30/32/35/40/42/50/52
  各 1 条散布 502, bad≤1/桶)
- 02:47-54: 回稳延续收尾 (02:53 桶 5×200 全 OK)
- **02:23 后全程 bad≤1/桶, 无连续多桶 bad≥5 风暴簇** ✅

**30min 502 = 9 条, 全 all_tiers_exhausted×9** (0 zombie, 0 NVAnth_IncompleteRead)
- NVAnth_IncompleteRead 连续第 6 轮消失 (R2132-2147), 持续确认非新可配类 ✅
- 全 NVCF 上游已知类, 0 新可配置类 ✅
- vs R2146 502×49 → 9 (-40, 散布期收尾 502 量大幅回落)

**tier 30min**:
- pexec_success×73 + pexec_conn_RemoteDisconnected×14 + pexec_SSLEOFError×1
- 429_nv_rate_limit = 0 (第 4 波 429 仍滚出 30min 窗口) ✅
- 连接异常整体低位 (14 RemoteDisconnected + 1 SSLEOFError), 均 NVCF 上游已知类, 0 新可配类 ✅

## 未恶化指标 (STATE 判断线 8 条全过)

| 指标 | 本轮 | vs R2146 | 判定 |
|---|---|---|---|
| 30min SR | 90.2% | 58.9%→90.2% (+31.3pp) | ✅ 重回次稳态带 |
| 502 分类 | 9 全 all_tiers_exhausted | 49→9 (-40) | ✅ 全 NVCF 已知类 |
| NVAnth_IncompleteRead | 0 (连续第 6 轮消失) | 持平 | ✅ 非新可配类 |
| tier 429 | 0 | 持平 | ✅ 第 4 波仍滚出 |
| 真中断 (cc4101 both failed) | 0 | 0 | ✅ 0 真中断 |
| fallback | 7 (全 75s SKIP-CIRCUIT) | 7→7 | ✅ 0 失败, 0 条 120s 跑满 |
| breaker nv_gw 30min | 0 (state 未 OPEN) | 连续第 39 轮 | ✅ |
| BUG-A SKIP-PEXEC2 | 7 (持续复活) | 6→7 (+1) | ✅ 机制真实生效 |
| NV-CAP-RESET-MSFB | 7 (全被 ms_fb 兜) | 6→7 (+1) | ✅ abs_cap 正常 |

## fallback 详情 (7 条, 全 75s SKIP-CIRCUIT)

req 样本: 52113d9d / afc4585e / baef8e00 / ac1aad3f (等 7 条)
全 `PRIMARY-FAIL-SKIP-CIRCUIT` (header/ttfb 75s < chain budget 120s,
cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类)
全被 ms_gw 兜住, 0 fallback 失败, 0 条 120s 跑满 ✅

## nv_gw 容器状态

- /health = ok (passthrough, 5 keys, kimi_nv/dsv4p_nv/glm5_2_nv, default=dsv4p_nv)
- StartedAt = **2026-07-21T01:44:55Z** (CST 09:44:55)
  (R2146 记录 peer 重启 18:10:28Z→01:44:55Z, 连续 25 轮稳态打破;
   本轮核实仍是 01:44:55Z 未再漂移, 连续第 1 轮核实新 StartedAt 稳定)
- env 仍 peer R2108 改后值 (KEY60/TIER180/MIN_OUTBOUND10), 非 cc2 改
  NVU_GLM52_EXP_BACKOFF 不在 env = 关, 半成品冻结中

## 冻结理由 (连续第 107 轮) 仍成立

半成品未经 in-vivo 验证 + 激活需同步 chain_budget 120→420 + cc4101 header 60→450 +
post-200 软挂换 key 未实现 + 24h 观测窗口. 风险/收益不对等:
- 本轮 SR 90.2% 重回次稳态带, 散布期瞬态彻底收尾
- 502 全 NVCF 已知类, NVAnth 连续 6 轮消失
- 0 真中断, breaker 未 OPEN, abs_cap 正常, BUG-A 真实生效
- 边际收益小; 解冻不对症 — 本轮问题是 NVCF 上游连接抖动散布期已收尾,
  指数退避链路碰不到此错误类, 延长 chain_budget 反拖 SR.

**本轮不满足解冻条件** (STATE 判断线 8 条全未恶化) → 继续 NOP 冻结.

HM2 only. 不碰 HM1, 不碰 ms_gw(40007).
