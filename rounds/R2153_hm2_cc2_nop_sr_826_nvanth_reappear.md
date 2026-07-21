# R2153 (hm2_cc2): NOP R177 — 连续第 112 轮冻结, 30min SR 82.6% 散布期延续, NVAnth_IncompleteRead 时隔 7 轮再现 1 条单点

## 数据 (本 session 拉取, 当前 CST 11:59 / UTC 03:59, 窗口起点 ~03:29 UTC)

- **nv_gw 30min SR = 57/69 = 82.6%** (200:57 / 502:12, vs R2152 84.1% -1.5pp 小幅回落, 仍略低于 86-92% 次稳态带下沿; vs R2151 89.7% -7.1pp 连续第 2 轮略低于带下沿但散布非簇).
- **1min 桶完整轨迹 (UTC, 40min, 03:19→03:59)**: 03:19 单点 bad=1 散布起 → 03:20-24 连续 5 桶全 OK 回稳带 → 03:25-30 散布 (bad 各 1, 单点) → 03:32-34 回稳 → 03:35-40 散布加重 (03:39/03:40 两桶 bad=2 连续小簇) → 03:41-48 回稳带 → 03:49-55 散布 (bad 各 1-2 单点散布) → 03:56-59 连续 4 桶全 OK 回稳收尾 (03:56 3×200 / 03:57 3×200 / 03:58 5×200 / 03:59 3×200). **全程 bad≤2/桶无连续多桶 bad≥5 风暴簇** ✅ (03:39-40 两桶 bad=2 连续仅为小簇非风暴规模, 对比 R2120/R2121 风暴主峰 bad 5-10/桶 连续多桶, R2147 散布期 bad≤1/桶). 散布期瞬态收尾后新稳态期延续但本轮出现单点小簇, 整体仍非风暴.
- **30min 502=12 全 NVCF 已知类 0 新可配置类** ✅: all_tiers_exhausted×11 + **NVAnth_IncompleteRead×1 (时隔 7 轮再现单点非簇, R2132-R2152 连续消失, R2153 重现 1 条)**. (vs R2152 502×11 全 all_tiers_exhausted, 本轮 +1 条 NVAnth_IncompleteRead).
- **tier 30min**: pexec_success×45 + **pexec_429×9** (+6 vs R2152 的 3, 第4波 429 复发早期信号抬头但分散多桶单点非簇, SR 未被拖低) + pexec_conn_RemoteDisconnected×3 (连接异常整体低位均 NVCF 已知类).
- **fallback 9 FALLBACK-OK (vs R2152 10 -1)**: 全 9 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (header/ttfb 75s < chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类). **0 条 120s 跑满类** (持平 R2152). req 样本: 354d31c7 / 7a63a4dc / 6041a4be / d8375e28 / 4561175d / 5e987653 / aab8dd6f / c10bd7c5 / e5f0fe2c 等 9 条. cc4101 `grep -cE "both failed|UPSTREAM-ERROR-SEEN"` 30min = **0** → 0 真中断确认.
- **breaker**: cc4101 PRIMARY-BREAKER-OPEN 30min = **0**; nv_gw 30min `grep -cE "NV-Anth-BREAKER-FAIL"` = **0** (state 未 OPEN, 连续第 44 轮) ✅.
- **NV-CAP-RESET-MSFB = 13 条** (nv_gw 侧, R1818 bug7 cap_origin reset execute→ms_fb path 正常触发, 全被 ms_fb 兜住 0 真中断; vs R2152 13 持平).
- **BUG-A 修复 (R1913) 生效确认**: nv_gw 30min `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **12 次** (vs R2152 12 持平, 持续复活触发中, 机制真实生效) ✅.
- nv_gw /health = ok (passthrough, 5 keys, kimi_nv/dsv4p_nv/glm5_2_nv, default=dsv4p_nv).
- **docker inspect StartedAt 核实**: nv_gw=**01:44:55Z** (R2146 peer 重启后值, 连续第 6 轮核实未漂移) / cc4101=12:10:22Z (0 restart 未变).

## 决策: NOP R177, 连续第 112 轮冻结指数退避, 0 改动 0 restart

依据 STATE 下一步判断线 8 条全未恶化到解冻触发线:
1. 30min SR 82.6% 略低于次稳态带下沿但散布单点非簇无连续多桶 bad≥5 (未持续 <45% 也无风暴簇).
2. NVAnth_IncompleteRead 时隔 7 轮再现但仅 1 条单点非簇 (未演变为持续/风暴簇).
3. tier 连接异常 (3 RemoteDisconnected) 整体低位均 NVCF 已知类.
4. tier 429_nv_rate_limit (pexec_429) = 9 低位散布多桶单点非簇 (第4波 429 复发早期信号抬头但 SR 未被拖低).
5. 502 全 NVCF 已知类 0 新可配置类 (11 all_tiers_exhausted + 1 NVAnth_IncompleteRead).
6. fallback 全 75s SKIP-CIRCUIT 被兜住 0 失败; 0 条 120s 跑满类再现.
7. breaker 仍非真 OPEN (连续第 44 轮); nv_gw StartedAt 仍 01:44:55Z (连续第 6 轮核实未漂移).
8. NV-CAP-RESET-MSFB 13 条持平全被 ms_fb 兜 (稳态期未持续增多且 SR 未被此拖低).

**冻结理由 (连续第 112 轮) 仍成立**: 半成品未经 in-vivo 验证 (env 开关从未激活) + 激活需同步 chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key 未实现 + 24h 观测窗口. 风险/收益不对等 (本轮 30min SR 82.6% 散布非簇 + 502 全 NVCF 已知类 NVAnth 再现单点非簇 + 0 真中断 + breaker 未 OPEN + abs_cap 正常 + BUG-A 真实生效); **解冻不对症** — 本轮问题 (SR 小幅回落 + NVAnth 单点再现 + tier 429 低位抬头) 是 NVCF 上游连接抖动散布期延续, 指数退避链路碰不到此错误类, 延长 chain_budget 反拖 SR.

## 状态变化 (cc2 视角)

- nv_gw StartedAt 仍 **01:44:55Z** (R2146 peer 重启后值, 连续第 6 轮核实未漂移).
- env 仍 peer R2108 改后值 (KEY60/TIER180/MIN_OUTBOUND10), cc2 0 改动 0 restart.
- 本轮需记录的变化:
  (1) **30min SR 84.1%→82.6% -1.5pp 小幅回落** (仍略低于 86-92% 次稳态带下沿, 散布期瞬态收尾后新稳态期延续但本轮出现单点小簇, 1min 桶全程 bad≤2 无风暴簇).
  (2) **502 11→12 (+1)**: 11 all_tiers_exhausted + **NVAnth_IncompleteRead×1 时隔 7 轮再现单点** (R2132-R2152 连续消失, R2153 重现, 但仅 1 条非簇, 非新可配类持续爆发).
  (3) tier pexec_429 3→9 (+6 第4波 429 复发早期信号抬头) 但分散多桶单点非簇 SR 未被拖低; pexec_conn_RemoteDisconnected 低位.
  (4) fallback 10→9 (-1) 全 75s SKIP-CIRCUIT 被兜 0 真中断 0 失败 0 条 120s 跑满.
  (5) NV-CAP-RESET-MSFB 13→13 持平 / BUG-A SKIP-PEXEC2 12→12 持平持续复活.
  (6) breaker/abs_cap 全部未恶化, breaker 仍未 OPEN 连续第 44 轮, StartedAt 01:44:55Z 连续第 6 轮未漂移.

## 验证

- 0 改动 0 restart (NOP), 无需验证改动; nv_gw /health=ok, docker inspect StartedAt=01:44:55Z 未漂移确认容器状态稳定.
- 本轮核心指标全部在已知类范围内: 502 全 NVCF 已知类 (all_tiers_exhausted + NVAnth_IncompleteRead), tier 错误全 NVCF 已知类 (pexec_429 + pexec_conn_RemoteDisconnected), fallback 全 75s SKIP-CIRCUIT 已知类被 ms_gw 兜住.

## 下一轮该做什么

- **继续 NOP 巡检 (R178, 连续第 113 轮冻结)**: 重点看:
  1. **30min SR 是否能重回 86-92% 次稳态带** (本轮 82.6% 略低于带下沿散布非簇; 若下一轮 ≥86% 则确认散布期延续中的小波动; 若持续 <86% 多轮需观察是否进入新波动期; 若 <45% 或出现连续多桶 bad≥5 风暴簇则需重新评估).
  2. **⚠️ NVAnth_IncompleteRead 是否从再现演变为持续/风暴簇** (本轮时隔 7 轮再现 1 条单点非簇; 若下轮仍消失或单点则持续确认非新可配类; 若再现并爆发为簇需重新评估解冻判断线).
  3. tier 连接异常 (pexec_conn_RemoteDisconnected/SSLEOFError/500_nv_error/pexec_empty_200) 是否延续低位或再抬头 (本轮 3 RemoteDisconnected).
  4. **tier pexec_429 是否仍低位散布或抬头成簇** (本轮 9 低位分散多桶单点非簇; 第4波 429 复发早期信号抬头, 若成簇持续需观察是否拖低 SR).
  5. 502 分类是否仍全 NVCF 已知类 0 新可配置类 (本轮 12 = 11 all_tiers_exhausted + 1 NVAnth_IncompleteRead).
  6. fallback 是否仍全 75s SKIP-CIRCUIT 被兜住 0 失败; **关注 120s 跑满类是否再现增多** (本轮 0 条).
  7. breaker 是否仍非真 OPEN (连续第 45 轮); nv_gw StartedAt 是否仍 01:44:55Z (连续第 7 轮核实).
  8. NV-CAP-RESET-MSFB 是否持续增多 (本轮 13 持平; 若稳态期持续增多且 SR 被拖低需评估 chain_budget 是否过长).
- **若持续恶化才考虑动**: 任一指标恶化 (30min SR 持续 <45% **或出现风暴簇** 且 502 出新可配类持续非单点 或 fallback 失败 或 breaker 真 OPEN 切流) 才考虑重新评估解冻. 本轮不满足.
- **轮号**: 下一轮 git pull 看最新, peer hm2_optimize_hm1 抢号很快; cc2 用 R2154 或更大 hm2_cc2 前缀不撞号.
- **若未来要解冻**: 需先 in-vivo 验证 NVU_GLM52_EXP_BACKOFF (env 激活 + chain_budget 120→420 + cc4101 PRIMARY_HEADER_TIMEOUT 60→450 同步), 且实现 post-200 软挂换 key, 再 24h 观测. 当前不动.

HM2 only. 不碰 ms_gw. cc2 用 hm2_cc2 前缀.
