# R2123 (hm2_cc2) — NOP R157 连续第 92 轮冻结; 第 4 波 429 早期信号出现 (tier +4)

> HM2 only. cc2 视角. 巡检轮 (0 改动 0 restart).
> 本轮 git pull 看到 peer 最新 d312181 = R2121 (hm2_optimize_hm1, HM1 侧 KEY_COOLDOWN 68→66 walk-back).
> peer 在我 R2122 (c0fc1a5) 之后又推了一个 HM1 侧轮, 抢号很快. cc2 用 hm2_cc2 前缀 + R2123 避撞号.

## 数据 (本 session 拉取, CST 06:05 / UTC 22:05, 窗口起点 21:31 UTC)

### 30min 大窗
- nv_gw 30min SR = 83/111 = **74.8%** (200:83 / 502:28)
  - vs R2122 78.5% → **-3.7pp 略降** (大窗仍被 21:35-21:47 尖峰簇 + 22:00 后零星 502 拖累, 未回 91-96% 稳态)
  - vs R2118 自愈稳态 91.9% 仍低 -17.1pp

### 小窗 (last N min)
- last3 = 84.6% (11/13)
- last5 = 90.9% (20/22)
- last10 = 89.7% (35/39) — **已回 89-90% 稳态区间边缘**
- last15 = 90.0% (45/50)
- last20 = 84.1% (58/69)

### 5min 桶完整轨迹 (UTC)
| bucket | tot | ok | bad | SR% |
|---|---|---|---|---|
| 21:30 | 11 | 10 | 1 | 90.9 (稳态尾段) |
| **21:35** | 23 | 13 | 10 | **56.5** (主峰起) |
| **21:40** | 20 | 10 | 10 | **50.0** (主峰持续, bad=10) |
| 21:45 | 13 | 10 | 3 | 76.9 (回落) |
| 21:50 | 15 | 14 | 1 | 93.3 (**回稳态**) |
| 21:55 | 20 | 19 | 1 | 95.0 (**稳态**) |
| 22:00 | 19 | 16 | 3 | 84.2 (零星 502 又起, bad=3) |
| 22:05 | 1 | 1 | 0 | 100 (起步) |

**轨迹判读**: 21:35-21:47 是 13min 的 502 集中簇 (23 条), vs R2122 判断的"21:35-36 单点尖峰". 本轮数据更完整, 实际是**两桶主峰** (21:35/21:40 SR 56.5/50.0). 21:50-21:55 回到 93-95 稳态. 但 22:00 又起零星 502 (bad=3), 配合 tier 429 重现, 是**第 4 波风暴早期信号**.

### 502 错误分类 (30min, status!=200)
- all_tiers_exhausted = **28** (全 NVCF 上游已知类, **0 新可配置类**) ✅
- (R2122 拆分 all_tiers×18+NVAnth_IncompleteRead×1+zombie×1, 本轮统一显示 all_tiers_exhausted, 实质相同 NVCF 已知类族)

### tier 30min
- pexec_success = 35
- NVCFPexecRemoteDisconnected = 9
- pexec_conn_RemoteDisconnected = 5
- **429_nv_rate_limit = 4** ⚠️ (vs R2122 = 0, **+4 回升**)
- empty_200 = 1
- 0 SSLEOFError

**⚠️ tier 429 时间分布** (确认是新出现而非历史残留):
- 21:58 UTC ×1
- 21:59 UTC ×1
- 22:02 UTC ×1
- 22:04 UTC ×1
全在最近 7min 内 (21:58-22:04 UTC = CST 05:58-06:04). R2122 拉时 (21:37 UTC) tier 429=0 完全滚出; 本轮 30min 已滚进 4 条新 429. **第 4 波风暴早期信号确认** (但极弱, vs R2120 高峰 ×23, 当前 ×4).

## fallback / 真中断 / breaker / BUG-A

### fallback (cc4101 30min)
- FALLBACK-OK = **4 条** (vs R2122 = 5, **-1**)
- 全 4 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (header/ttfb 75s < chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类)
- **0 条 120s 跑满类** ✅ (持平 R2122)
- 0 fallback 失败, 0 真中断
- req 样本: c9e5ab47 (05:33) / 9b5dbd0a (05:41) / 7de29905 (05:44) / 9fddb416 (05:47)

### 真中断确认
- cc4101 `grep -cE "both failed|UPSTREAM-ERROR-SEEN"` 30min = **0** → 0 真中断 ✅

### breaker
- cc4101 PRIMARY-BREAKER-OPEN 30min = **0**
- nv_gw 30min `grep -cE "BREAKER"` = **0** (连 R2122 那条 `[NV-ANTH-BREAKER-FAIL] state=CLOSED` 单点 recorded 都没了)
- **state 未达 OPEN 阈值 = 连续第 25 轮验证未恶化机制正常吸收非恶化** ✅

### BUG-A 修复 (R1913) 生效确认
- 30min 内 `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **4 次** (vs R2122 = 5, -1, 持续复活触发中, 机制真实生效) ✅

### NV-CAP-RESET-MSFB (chain_budget 耗尽类)
- 30min = **4 条** (vs R2122 = 5, **-1**)
- 时间: 05:34 / 05:42 / 05:45 / 05:48 CST (total_elapsed_pre_reset=121-125s)
- R1818 bug7 已有 cap_origin reset 机制 (execute→ms_fb path) **正常触发**, 全被 ms_fb 兜住 0 真中断
- **非恶化**: 数量持平略减, 持续约 14min (vs R2122 24min 范围略缩), 半稳态期 chain_budget 120s 仍偶被耗尽走 ms_fb 正常兜底

### abs_cap
- 30min `grep -cE "abs_cap|ABS-CAP"` = **0** ✅ (R1918 方案 0 持续)

## 健康与参数

- nv_gw /health = ok (passthrough, 5 keys, kimi_nv/dsv4p_nv/glm5_2_nv, default=dsv4p_nv)
- docker inspect StartedAt:
  - nv_gw = **2026-07-20T18:10:28Z** (连续第 12 轮核实未漂移, R2107 后稳定)
  - cc4101 = 2026-07-19T12:10:22Z (0 restart 未变)
- env (peer R2108 改后值, 非 cc2 改):
  - KEY_COOLDOWN_S=60 / TIER_COOLDOWN_S=180 / MIN_OUTBOUND_INTERVAL_S=10
  - UPSTREAM_TIMEOUT=90 / TIER_TIMEOUT_BUDGET_S=180
  - NVU_GLM52_EXP_BACKOFF 不在 env 中 = 关 (半成品冻结中)
  - chain_budget 仍 120s, 未升 420

## 状态变化 (cc2 视角, 本轮需记录)

1. **第 4 波 429 风暴早期信号出现**: tier 429_nv_rate_limit 从 R2122 的 0 回升到 4 (全在 21:58-22:04 UTC 最近 7min). 延续周期性 ~1h 模式 (R2111 02:45→R2116 03:45→R2119 04:45→本轮 22:00 UTC ≈ 06:00 CST, 间隔约 1h). 但极弱 (×4 vs R2120 高峰 ×23), 尚未爆发.
2. 30min SR 74.8% (vs R2122 78.5% -3.7pp 略降), 主因 21:35-21:47 尖峰簇 + 22:00 后零星 502 拖累. last10/15 已回 89-90% 稳态边缘.
3. 502 全 all_tiers_exhausted NVCF 已知类, 0 新可配置类 ✅
4. fallback 5→4 全 75s SKIP-CIRCUIT 被兜住 0 失败 0 条 120s 跑满 ✅
5. CAP-RESET 5→4 持续 14min 非纯风暴驱动 (持平略减)
6. breaker/BUG-A(4次)/abs_cap(0) 全部未恶化持平
7. nv_gw StartedAt 仍 18:10:28Z (连续第 12 轮核实未漂移), env 仍 peer R2108 改后值, cc2 0 改动 0 restart

## 冻结理由 (连续第 92 轮) 仍成立

- 半成品未经 in-vivo 验证 (env 开关从未激活)
- 激活需同步 chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key 未实现 + 24h 观测窗口
- 风险/收益不对等: 本轮 0 真中断 / 0 fallback 失败 / 0 新可配类 / breaker 未真 OPEN / abs_cap 0; 429 第 4 波仅早期信号 ×4 极弱, 解冻不对症 (429 风暴延长 chain_budget 反拖 SR, R2111/2116/2119/2120/2121/2122/2123 七轮论证)
- 用户诉求 "可以报错但不能让 cc2 中断" 仍达成 (0 真中断, 4 条 fallback 全被 ms_gw 兜住)

## 本轮动作

- **0 改动 0 restart** (NOP 巡检轮)
- 仅拉数据 + 记录第 4 波 429 早期信号 + 写 round 文件 + 覆写 STATE.md
- HM2 only, 不碰 ms_gw, 不碰 HM1

## 下一轮该做什么

- **继续 NOP 巡检 (R158, 连续第 93 轮冻结)**: 重点是确认第 4 波 429 是否爆发.
  1. tier 429_nv_rate_limit 是否从 4 扩大 (若到 ×10+ 即第 4 波正式爆发, 沿 R2111/R2119 模式).
  2. 30min SR 是否进一步被拖低 (当前 74.8%, 若跌破 70% 持续则可能进入风暴期).
  3. 502 分类是否仍全 NVCF 已知类 0 新可配类.
  4. fallback 是否仍全 75s SKIP-CIRCUIT 被兜住 0 失败; 120s 跑满类是否再现.
  5. breaker 30min recorded 是否仍非真 OPEN (连续第 26 轮); nv_gw StartedAt 是否仍 18:10:28Z (连续第 13 轮).
  6. CAP-RESET 是否持续 (本轮 4 条, 若稳态期持续增多需评估 chain_budget 是否过长耗 SR).
- **若持续恶化才考虑动**: 任一指标恶化 (30min SR 持续<70% 非风暴污染 + 502 新可配类, 或 fallback 失败, 或 breaker 真 OPEN 切流) 才考虑重新评估解冻. 本轮不满足.
- **若未来要解冻**: 需先 in-vivo 验证 NVU_GLM52_EXP_BACKOFF (env 激活 + chain_budget 120→420 + cc4101 PRIMARY_HEADER_TIMEOUT 60→450 同步), 且实现 post-200 软挂换 key, 再 24h 观测. 当前不动.
- **轮号**: 下一轮 git pull 看最新; cc2 用 R2124 或更大 hm2_cc2 前缀避撞号.
