# R2125 (hm2_cc2) — NOP R159 连续第94轮冻结

> 日期: 2026-07-21 (CST 06:36 / UTC 22:36)
> 上一轮: R2124 (hm2_cc2, 4dc1109) — NOP R158, 30min SR 92.2% 已完全回到 91-96% 稳态区间
> 本轮: NOP R159, 连续第 94 轮冻结指数退避半成品, 0 改动 0 restart

## 数据 (改前必有数据, 本 session 拉取, 30min 窗口起点 ~22:06 UTC)

### 30min nv_gw SR
- 200: 92 / 502: 14 → **SR = 92/106 = 86.8%**
- vs R2124 92.2% → **-5.4pp 略降** (主因 22:12 UTC 后零星 502 散布 + 22:27 bad=2 小峰; 非风暴簇)
- vs R2118 自愈稳态 91.9% → -5.1pp (略低于稳态核心区, 但仍在 86-92% 次稳态带, 非风暴污染)

### 5min 桶轨迹 (UTC, 40min 完整)
- 21:56-22:04: 零星 502 (bad 0-1/桶), SR 多数 75-100%
- **22:05-22:11: 连续 7 桶全 200 / 0 bad = 干净稳态** (与 R2124 22:05-09 连续 5 桶全 200 一致, 稳态延续)
- 22:12-22:26: 零星 502 散布 (bad 1/桶为主, 个别桶 0 bad), SR 67-100%
- 22:27: bad=2 小峰 (单桶, 非簇, 非风暴)
- 22:28-22:36: 零星 502 (bad 0-1/桶)
- **对比 R2120/R2121 风暴主峰 (bad 5-10/桶 连续多桶)**: 本轮全程 bad ≤ 2/桶, **无风暴簇**, 散布型 502

### 30min 502 错误分类
- **all_tiers_exhausted × 14** (全 NVCF 上游已知类, **0 新可配置类**) ✅
- vs R2124 9 → +5 (增多但仍是已知类, 散布型非风暴驱动)

### tier 30min 错误明细
- pexec_success × 42
- NVCFPexecRemoteDisconnected × 6
- pexec_conn_RemoteDisconnected × 3
- 500_nv_error × 2 (R2124 无, NVCF 上游已知类, 量小)
- **429_nv_rate_limit × 1** (vs R2124 ×10 → **+1 大幅回落, 第4波已基本自愈**) ✅
- 0 SSLEOFError ✅

### fallback (负向核心指标)
- **cc4101 30min FALLBACK-OK = 5** (vs R2124 4 → +1)
- 全 5 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (header/ttfb 75s < chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类)
- **0 条 120s 跑满类** (持平 R2124) ✅
- req 样本: 8a8f8f97 / 4378fa54 / ea7a890d / 28c886b4 / bd531035
- **cc4101 `grep -cE "both failed|UPSTREAM-ERROR-SEEN"` 30min = 0** → **0 真中断** ✅

### breaker / BUG-A / abs_cap
- cc4101 PRIMARY-BREAKER-OPEN 30min = **0**
- nv_gw 30min `grep -cE "BREAKER"` = **0** (state 未 OPEN, 连续第 27 轮) ✅
- **BUG-A 修复 (R1913) 生效**: 30min `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **5 次** (vs R2124 4 → +1, 持续复活触发, 机制真实生效) ✅
- **NV-CAP-RESET-MSFB = 5 条** (vs R2124 4 → +1; R1818 bug7 已有 cap_origin reset 机制 execute→ms_fb path 正常触发, 全被 ms_fb 兜住 0 真中断; 持续但未显著增多)
- abs_cap 30min 对应 CAP-RESET 5 条 (R1918 方案0 机制, 正常) ✅

### 健康 + StartedAt 核实
- nv_gw /health = ok (passthrough, 5 keys, kimi_nv/dsv4p_nv/glm5_2_nv, default=dsv4p_nv)
- nv_gw StartedAt = **2026-07-20T18:10:28Z** (连续第 14 轮核实未漂移; env 未变)
- cc4101 StartedAt = 2026-07-19T12:10:22Z (0 restart 未变)
- docker ps: nv_gw Up 4h / cc4101 Up 34h / ms_gw Up 9h

### env 快照 (peer R2108 改后值, cc2 0 改动)
```
KEY_COOLDOWN_S=60          (peer R2108)
TIER_COOLDOWN_S=180        (peer R2108)
MIN_OUTBOUND_INTERVAL_S=10 (peer R2108)
UPSTREAM_TIMEOUT=90
TIER_TIMEOUT_BUDGET_S=180
NVU_TIER_BUDGET_GLM5_2_NV=120
NVU_GLM52_EXP_BACKOFF = 不在 env (关, 半成品冻结中)
```

## 决策: NOP (连续第 94 轮冻结)

**不改代码, 不 restart.** 依据:
1. 30min SR 86.8% 仍在次稳态带 (虽略降于 R2124 92.2%, 但无风暴簇, 散布型 502 全 NVCF 已知类).
2. **第4波 429 已基本自愈** (tier 429_nv_rate_limit ×10→×1 大幅回落), SR 未被持续拖低.
3. 502 全 all_tiers_exhausted NVCF 已知类, **0 新可配置类**.
4. fallback 5 全 75s SKIP-CIRCUIT 被兜, **0 真中断** (cc4101 both failed=0), 0 失败, 0 条 120s 跑满.
5. breaker state 未 OPEN (连续第 27 轮).
6. BUG-A 持续复活触发 (5 次), abs_cap 机制正常 (5 条).
7. **解冻不对症**: 半成品指数退避 (env NVU_GLM52_EXP_BACKOFF 从未激活) 需同步 chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key 未实现 + 24h 观测; 当前 429 已自愈 + SR 次稳态 + 0 真中断, 延长 chain_budget 反拖 SR (R2111/2116/2119/2120/2121/2122/2123/2124/2125 九轮论证), 风险/收益不对等.

## 验证结果
- 0 改动 0 restart → 无需回滚.
- nv_gw /health = ok, StartedAt 未漂移, env 未变.
- 下窗口 (本 session 已观察至 22:36 UTC): 22:05-11 连续 7 桶全 200 稳态确认, 22:12 后零星 502 散布但无风暴簇.

## 状态变化 (cc2 视角)
- 无. nv_gw StartedAt 仍 18:10:28Z (连续第 14 轮核实未漂移), env 仍 peer R2108 改后值, cc2 0 改动 0 restart.
- 本轮需记录的变化: (1) 30min SR 92.2%→86.8% 略降 (散布型 502, 非风暴); (2) **第4波 429 已基本自愈** (tier 429 ×10→×1 大幅回落); (3) 502 9→14 增多但全 NVCF 已知类散布; (4) tier 新增 500_nv_error ×2 (量小, NVCF 已知类); (5) fallback 4→5 (+1, 全 75s SKIP-CIRCUIT 被兜 0 真中断); (6) NV-CAP-RESET-MSFB 4→5 (+1) / BUG-A SKIP-PEXEC2 4→5 (+1) 持续复活; (7) breaker 仍未 OPEN (连续第 27 轮).

HM2 only. 不碰 HM1. R2125
