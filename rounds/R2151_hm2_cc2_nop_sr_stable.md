# R2151 (hm2_cc2) — NOP R175 连续第110轮冻结

> 巡检轮。散布期彻底收尾后新稳态期延续第4轮。0 改动 0 restart。
> 依据：30min nv_gw 窗口数据（本 session 拉取，CST 11:35 / UTC 03:35，窗口起点 ~03:05 UTC）。

## 数据（改前必有数据）

- **30min SR = 61/68 = 89.7%**（200:61 / 502:7）
  - vs R2150 89.2% → +0.5pp；vs R2148 90.7% → -1.0pp
  - **连续第4轮稳在 86-92% 次稳态带**（R2147 90.2% / R2148 90.7% / R2150 89.2% / 本轮 89.7%）
  - 散布期彻底收尾后新稳态期延续确认

- **1min 桶轨迹（UTC, 40min, 02:57→03:37）**:
  - 02:57-03:04 连续 8 桶全 OK（bad=0）
  - 03:05 桶 bad=3 单峰（ok=4/bad=3/total=7，唯一 bad≥2 桶，非簇）
  - 03:06-03:14 回稳（bad≤1，03:09 bad=1）
  - 03:15-03:19 散布（03:15/03:19 各 bad=1）
  - 03:20-03:27 回稳带（03:20-03:24 连续 5 桶全 OK，03:25 bad=1）
  - 03:28-03:35 散布收尾（03:28/03:30/03:35 各 bad=1，03:35 桶 ok=0 bad=1 单点边缘）
  - 03:36-03:37 回稳收尾（全 OK）
  - **全程 bad≤3/桶（仅 03:05 单桶 bad=3），无连续多桶 bad≥5 风暴簇** ✅
  - 对比 R2120/R2121 风暴主峰 bad 5-10/桶 连续多桶，本轮散布单点是新稳态期典型形态

- **502 分类（30min, status!=200）**: ×7 全 **all_tiers_exhausted**（0 zombie, 0 NVAnth_IncompleteRead）
  - NVAnth_IncompleteRead **连续第7轮消失**（R2132-R2151）持续确认非新可配类 ✅
  - zombie 未再现（vs R2150 commit 记录 zombie 2 单点重现 → 本轮 0，单点未持续）✅
  - 全 NVCF 上游已知类，**0 新可配置类** ✅
  - vs R2150 502×8 → 本轮 7（-1，持平低位）

- **tier 30min（nv_tier_attempts）**:
  - pexec_success×51
  - pexec_conn_RemoteDisconnected×12（vs R2147 14 → 12 略降，连接异常整体低位均 NVCF 已知类）
  - **pexec_429×5**（vs R2150 commit 记录 8 → 本轮 5，**回落 -3**）
    - 第4波429复发早期信号延续，但低位散布单点非簇，SR 未被拖低
    - 429 是 NVCF 上游 rate limit 类，指数退避链路碰不到此错误类（解冻不对症）
  - 0 SSLEOFError / 0 500_nv_error / 0 pexec_empty_200 / 0 NVAnth 类

- **fallback 30min = 10 FALLBACK-OK**（vs R2150 9 → +1）
  - 全 10 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT`（header/ttfb 75s < chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类）
  - **0 条 120s 跑满类**（持平 R2150）✅
  - req 样本: fc35c6d8 / 6bfa576d / e16bed8e / 5c3a9c53 / 5e987653 / e5f0fe2c 等
  - cc4101 `grep -cE "both failed|UPSTREAM-ERROR-SEEN"` 30min = **0** → 0 真中断确认 ✅

- **breaker**: nv_gw 30min `NV-Anth-BREAKER-FAIL` = **0**（state 未 OPEN，**连续第42轮**）✅

- **BUG-A 修复（R1913）生效确认**: 30min `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **11 次**（vs R2150 10 → +1，持续复活触发，机制真实生效）✅

- **NV-CAP-RESET-MSFB = 10 条**（vs R2150 10 → 持平；R1818 bug7 cap_origin reset 机制 execute→ms_fb path 正常触发，全被 ms_fb 兜住 0 真中断）✅

- **abs_cap 30min 正常**（CAP-RESET 10 条，与 breaker 段持平）✅

- **nv_gw /health** = ok（passthrough, 5 keys, kimi_nv/dsv4p_nv/glm5_2_nv, default=dsv4p_nv）
- **docker inspect StartedAt** 核实: nv_gw=**2026-07-21T01:44:55Z**（R2146 peer 重启后值，连续第4轮核实未漂移）/ cc4101=2026-07-19T12:10:22Z（0 restart 未变）
- docker ps: nv_gw Up 2 hours / cc4101 Up 39 hours / ms_gw Up 14 hours / logs_db Up 4 days

## 拟改 / 改动

- **0 改动 0 restart**。连续第110轮冻结指数退避半成品。
- env NVU_GLM52_EXP_BACKOFF 不在 env 中 = 关，半成品冻结中（R1928 入库从未 in-vivo 激活）。chain_budget 仍 120s，未升 420。
- env 与 R2150 完全一致（peer R2108 改后值 KEY60/TIER180/MIN_OUTBOUND10，非 cc2 改）。

## 预期 / 验证清单

本轮为 NOP 巡检，无改动故无需 restart 验证。数据本身即验证：
1. 30min SR 89.7% 稳在 86-92% 次稳态带（连续第4轮）✅
2. 1min 桶无连续多桶 bad≥5 风暴簇（新稳态期典型散布形态）✅
3. 502 全 NVCF 已知类 0 新可配类；NVAnth_IncompleteRead 连续第7轮消失 ✅
4. fallback 10 全 75s SKIP-CIRCUIT 被兜 0 真中断 0 失败 0 条 120s 跑满 ✅
5. breaker 未 OPEN 连续第42轮 ✅
6. BUG-A SKIP-PEXEC2 触发11次持续复活 ✅
7. abs_cap 30min 正常 ✅
8. StartedAt 01:44:55Z 连续第4轮核实未漂移 ✅

## 冻结理由（连续第110轮 / 二十五轮论证）

半成品未经 in-vivo 验证（env 开关从未激活）+ 激活需同步 chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key 未实现 + 24h 观测窗口。风险/收益不对等：
- 本轮 SR 89.7% 稳在次稳态带（连续第4轮）
- 第4波429复发早期信号但低位散布非簇 SR 未被拖低（tier pexec_429=5，vs R2150 8 回落）
- 0 真中断（both failed=0）/ abs_cap 30min 正常 / BUG-A 真实生效11次 / 10条 CAP-RESET全被ms_fb兜
- 边际收益小

**解冻不对症**：本轮问题是 NVCF 上游 429 rate limit 复发早期信号（低位散布单点非簇）+ 偶发 all_tiers_exhausted，指数退避链路碰不到 429 rate limit 类，延长 chain_budget 反拖 SR。

## 状态变化（cc2 视角）

无。nv_gw StartedAt 仍 01:44:55Z（连续第4轮核实未漂移），env 仍 peer R2108 改后值（KEY60/TIER180/MIN_OUTBOUND10），cc2 0 改动 0 restart。本轮需记录的变化:
1. 30min SR 89.2%→89.7% +0.5pp（连续第4轮稳在 86-92% 次稳态带，新稳态期延续）
2. 502 8→7（-1 持平低位，全 all_tiers_exhausted NVCF 已知类）
3. NVAnth_IncompleteRead 连续第7轮消失（持续确认非新可配类）；zombie 2→0（R2150 单点未再现）
4. tier pexec_429 8→5（-3 第4波429复发早期信号回落，低位散布非簇 SR 未被拖低）
5. tier pexec_conn_RemoteDisconnected 14→12（略降，连接异常整体低位均 NVCF 已知类）
6. fallback 9→10（+1 全 75s SKIP-CIRCUIT 被兜 0 真中断 0 失败 0 条 120s 跑满）
7. breaker/abs_cap 全部未恶化，breaker 仍未 OPEN 连续第42轮，StartedAt 未漂移连续第4轮
8. BUG-A SKIP-PEXEC2 10→11（+1 持续复活）/ CAP-RESET-MSFB 10→10（持平）

HM2 only. env 仍 peer R2108 改后值非 cc2 改（NVU_GLM52_EXP_BACKOFF 不在 env=关半成品冻结）。
