# R2150 (hm2_cc2): NOP R174 — 连续第 109 轮冻结, SR 89.2% 稳态延续, ⚠️tier 429 翻倍(单点非簇)

## 数据 (30min window, CST 11:21 / UTC 03:21 拉取, 窗口起点 ~02:51 UTC)

### nv_gw 30min 总览
- **SR = 66/74 = 89.2%** (200:66 / 502:8)
- vs R2148 大窗 90.7% (78/86): **-1.5pp 几乎持平**, 连续第 3 轮稳在 86-92% 次稳态带 (R2146 回稳带 90.7% → R2147 90.2% → R2148 90.7% → 本轮 89.2%)
- vs R2146 大窗 58.9% (散布期): 仍 +30.3pp, 散布期瞬态彻底收尾后新稳态期持续确认

### 1min 桶轨迹 (45min, 02:38→03:22 UTC)
- 02:38-02:57 回稳带延续 (bad≤1/桶, 多数桶全 200)
- 02:58-03:04 回稳 (03:02-04 全 200)
- **03:05 桶 bad=3 单点稍高** (4 req, 1 ok 3 bad — 此为本轮唯一稍高桶)
- 03:06-03:22 回稳收尾 (bad≤1/桶, 03:10/20/21 桶全 200)
- **全程 bad≤3/桶 (除 03:05), 无连续多桶 bad≥5 风暴簇** ✅ (对比 R2120/R2121 风暴主峰 bad 5-10/桶连续多桶)

### 502 错误分类 (8 条)
- all_tiers_exhausted ×5 (NVCF 上游已知类)
- zombie_empty_completion ×2 (vs R2148 2 持平, 单点重现非簇)
- NVAnth_IncompleteRead = 0 (连续第 7 轮消失 R2132-2150, **已确认非新可配类**) ✅
- **0 新可配置类** ✅ (vs R2148 8 → 本轮 8 持平)

### tier 30min 明细 (nv_tier_attempts)
- pexec_success ×61
- pexec_conn_RemoteDisconnected ×9 (连接异常低位, NVCF 上游已知类)
- **pexec_429 ×8** (vs R2148 4 → 本轮 8 **+4 翻倍**, 第4波 429 复发早期信号增强)
  - 时序分布: 02:58(1) / 03:00(1) / 03:05(1) / 03:06(1) / 03:17(1) / 03:20(1) / 03:21(2) — **分散在 7 个分钟桶, 每桶 1-2 条 = 自愈性单点非簇**, SR 未被拖低 ✅
  - 持续观察: R2147 tier 429=0 → R2148 4 → 本轮 8, 呈现第4波 429 滚出后又复发早期信号, 但仍是单点自愈性, 非风暴簇

### fallback (cc4101 30min)
- **9 条 FALLBACK-OK** (vs R2148 8 +1), **0 真中断** (both failed=0), **0 fallback 失败**
- 全 9 条 = 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (header/ttfb 75s < chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类)
- **0 条 120s 跑满类** (持平 R2148) ✅
- req 样本: e91fbd14 / 350dc25c / da9fb4c8 / fc35c6d8 等

### breaker (30min)
- nv_gw `NV-Anth-BREAKER-FAIL` = **0** (state 未 OPEN, 连续第 41 轮) ✅
- cc4101 PRIMARY-BREAKER-OPEN = 0

### BUG-A 修复 (R1913) + abs_cap
- **NV-GLM52-CHAIN-SKIP-PEXEC2 触发 10 次** (vs R2148 7 +3, 持续复活触发, 机制真实生效) ✅
- **NV-CAP-RESET-MSFB = 10 条** (vs R2148 7 +3, R1818 bug7 cap_origin reset 机制 execute→ms_fb path 全被 ms_fb 兜住 0 真中断) ✅
- abs_cap 30min 正常 (CAP-RESET 10 条, 与 breaker 段持平) ✅

### 健康 + StartedAt
- nv_gw /health = ok (passthrough, 5 keys, kimi_nv/dsv4p_nv/glm5_2_nv, default=dsv4p_nv)
- nv_gw StartedAt = **2026-07-21T01:44:55Z** (R2146 peer 重启后值, 本轮连续第 3 轮核实未漂移) ✅
- cc4101 StartedAt = 2026-07-19T12:10:22Z (0 restart 未变)

## 拟改 / 决策

**NOP R174, 连续第 109 轮冻结指数退避, 0 改动 0 restart.**

**冻结理由 (连续第 109 轮) 仍成立**:
- 半成品 (NVU_GLM52_EXP_BACKOFF) 未经 in-vivo 验证 (env 开关从未激活) + 激活需同步 chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key 未实现 + 24h 观测窗口
- 风险/收益不对等: 本轮 30min SR 89.2% 仍稳次稳态带 + 第4波 429 复发早期信号但仍单点非簇 SR 未被拖低 + 0 真中断 + abs_cap 30min 机制正常 + BUG-A 修复真实生效 (10 次) + 10 条 NV-CAP-RESET-MSFB 全被 ms_fb 兜住非恶化, 边际收益小
- **解冻不对症**: 本轮问题是 NVCF 上游 tier 429 单点复发 + 散布期已收尾, 指数退避链路碰不到此错误类 (429 是 rate limit 由 KEY_COOLDOWN/TIER_COOLDOWN 处理), 延长 chain_budget 反拖 SR

**STATE 下一步判断线 8 条全未恶化** (本轮):
1. ✅ 30min SR 89.2% 稳在次稳态带 (≥85%, 连续第 3 轮)
2. ✅ NVAnth_IncompleteRead 连续第 7 轮消失 (非新可配类)
3. ✅ tier 连接异常低位 (9 RemoteDisconnected, 均 NVCF 已知类)
4. ⚠️ tier 429=8 单点非簇 SR 未被拖低 (第4波复发早期信号, 持续观察)
5. ✅ 502 全 NVCF 已知类 0 新可配置类
6. ✅ fallback 全 75s SKIP-CIRCUIT 被兜住 0 失败, 0 条 120s 跑满
7. ✅ breaker 未真 OPEN (连续第 41 轮); StartedAt 01:44:55Z 连续第 3 轮未漂移
8. ⚠️ NV-CAP-RESET-MSFB 10 条 (+3 vs R2148), 稳态期增多但全被 ms_fb 兜 SR 未被拖低, 持续观察

**任一指标持续恶化才考虑动**: 30min SR 持续 <45% **或** 出现风暴簇 (连续多桶 bad≥5) **且** 502 出新可配置类持续非单点 **或** fallback 失败 **或** breaker 真 OPEN 切流. 本轮不满足.

## 验证结果

- 0 改动 0 restart → 不适用 (NOP 巡检轮)
- 下窗口数据已确认: SR 89.2% 稳态延续, fallback 9 全被兜 0 真中断, breaker 未 OPEN
- 改前数据有 (30min + 1min 桶), 决策依据充分

## 参数快照 (docker exec env, peer R2108 改后真实值, 本轮 0 改动)

```
KEY_COOLDOWN_S=60          (peer R2108 改 25→60, cc2 不碰)
TIER_COOLDOWN_S=180        (peer R2108 改 25→180, cc2 不碰)
MIN_OUTBOUND_INTERVAL_S=10 (peer R2108 改 0→10, cc2 不碰)
KEY_AUTHFAIL_COOLDOWN_S=60
NVU_BIG_INPUT_FAIL_N=1
UPSTREAM_TIMEOUT=90
TIER_TIMEOUT_BUDGET_S=180
NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_BIG_INPUT_COOLDOWN_S=180
NVU_TIER_BUDGET_GLM5_2_NV=120
NVU_TIER_BUDGET_DSV4P_NV=180
NVU_PEXEC_TIMEOUT_FASTBREAK=3
NVU_EMPTY_200_FASTBREAK=3
NVU_GLM52_EXP_BACKOFF 不在 env = 关 (半成品冻结中)
```

HM2 only. R2150 (hm2_cc2).
