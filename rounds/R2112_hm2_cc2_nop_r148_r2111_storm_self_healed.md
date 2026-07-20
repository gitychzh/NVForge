# R2112 (hm2_cc2): NOP R148 巡检 — R2111 30min 风暴自愈确认 (连续第 84 轮冻结)

> 本轮不编码、不 restart。**确认 R2111 记录的 30min 急剧恶化事件 (SR 66.6% 首次跌破 90%)
> 已自愈** — 最近 15/20min SR 回到 90.6%/92.7% 稳态区间, tier 429 回落 10→1。
> 0 改动 0 restart 0 真中断。HM2 only。

## 数据 (本 session 拉取, 当前 CST 03:25; R2111 拉取时 CST 03:12 踩在风暴高峰尾部)

### 30min nv_gw (大窗仍被 02:45-03:00 风暴高峰污染, 但恢复趋势已显)

- status: 200×95 / 502×38 / 429×2 → 30min SR = 95/135 = **70.4%** (仍 <90%, 但 vs R2111 拉时 66.6% +3.8pp 已开始回升)
- 502 error_type: all_tiers_exhausted×37 + zombie_empty_completion×4 (全 NVCF 上游已知类, **0 新可配置类**)
- 429=2 (vs R2111 拉时 3, -1)

### 502 时间分布 (5min 桶, UTC; 18:40 UTC = 02:40 CST, 19:25 UTC = 03:25 CST)

- **18:45-19:00 UTC (02:45-03:00 CST) 风暴高峰**: 18:45 502×2 / 18:50 502×9 / **18:55 502×19(峰值)** / 19:00 502×11
- **19:05-19:25 UTC (03:05-03:25 CST) 明显恢复**: 19:05 502×3 / 19:10 502×1 / 19:15 502×3 / 19:20 502×1 / 19:25 502×1
- 19:10-19:25 桶 200 约 9-18, 502 只 1-3 → **SR 已恢复到 ~90%+**

### 恢复确认 (小窗, 排除风暴高峰尾部污染)

- **最近 15min SR = 58/64 = 90.6%** ✅ **已回到 90% 阈值以上** (vs R2111 拉时 30min 66.6%)
- **最近 20min SR = 76/82 = 92.7%** ✅ **回到稳态区间** (稳态区间 94-96%, 当前 92.7% 仍在上行恢复中)

### 30min tier (vs R2111 拉时 — tier 层恶化大幅缓解)

- pexec_success×33 / NVCFPexecRemoteDisconnected×6 / pexec_conn_RemoteDisconnected×6 / pexec_SSLEOFError×3 / **429_nv_rate_limit×1** / 500_nv_error×1
- vs R2111 拉时 (pexec_success×31 / NVCFPexecRemoteDisconnected×9 / pexec_conn_RemoteDisconnected×5 / pexec_SSLEOFError×4 / 429_nv_rate_limit×10):
  **429_nv_rate_limit 10→1 大幅回落 (-9)** ✅ (NVCF 上游 429 rate limit 风暴已平息)
  pexec_SSLEOFError 4→3 (-1, 略降); NVCFPexecRemoteDisconnected 9→6 (-3); pexec_conn_RemoteDisconnected 5→6 (+1, 区间内波动)
- **结论**: tier 层 429 风暴已基本平息, 当前剩余主要是 NVCF 上游 RemoteDisconnected/SSL 连接抖动 (NVCF 侧问题, 非网关旋钮)

### 6h (仍含远古风暴污染, 不采信)

- status: 502×1263 / 200×356 / 429×103 → 6h SR 失真 (全 peer R2107 重启前 01:52-02:10 dsv4p 429 风暴期 + 本轮 02:45-03:00 风暴污染; 等 CST 08:10 后 6h 窗口完全滚出风暴期才采信)

### 未恶化部分 (系统在吸收, 没有失控)

- **0 真中断**: cc4101 30min `both failed|ms.*fail|UPSTREAM-ERROR-SEEN` = **0** ✅
- **fallback 6 全兜住** (vs R2111 拉时 7, -1): 全 6 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (header/ttfb timeout 75s < chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类 cc4101 bug3 preempt 层)。**0 条 120s 跑满类** (vs R2111 0 条持平, b4db8071 已滚出窗口)。req 样本: 21c6763d/957185ef/5729c737/f1c51aab/4577a244/9822be90。全 6 条被 cc4101 抢断切 ms, ms 救回 → 0 条 fallback 失败 → CC 收 0 真 502。
- **breaker**: cc4101 PRIMARY-BREAKER-OPEN 30min = **0**; nv_gw 30min `BREAKER-FAIL|BREAKER.*OPEN|NV-ANTH-BREAKER-FAIL` = **0**。state CLOSED, count 仍 2 未累积到 OPEN 阈值 = **连续第 19 轮验证未恶化机制正常吸收** (符合 CLAUDE.md "recorded 但 CLOSED 是机制正常吸收, 不是恶化")。
- **BUG-A 修复 (R1913) 仍生效**: 30min `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **4 次** (vs R2111 5 次 -1, 持续复活触发中, 机制真实生效) ✅
- **abs_cap 30min = 0** (6h=2 全远古偶发非 R1918 cap_origin 失效) ✅

### nv_gw /health + StartedAt + env

- /health = ok (proxy_role=passthrough, nv_num_keys=5, nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=dsv4p_nv, port=40006)
- nv_gw StartedAt = **2026-07-20T18:10:28Z** (R2107 首次记录 05:57→18:10 漂移后, 连续第 5 轮核实未再漂移)
- cc4101 StartedAt = 2026-07-19T12:10:22Z (0 restart 未变)
- env 仍 peer R2108 改后值 (KEY_COOLDOWN_S=60 / TIER_COOLDOWN_S=180 / MIN_OUTBOUND_INTERVAL_S=10 / UPSTREAM_TIMEOUT=90 / TIER_TIMEOUT_BUDGET_S=180 / NVU_TIER_BUDGET_GLM5_2_NV=120), cc2 不碰 peer 旋钮, 0 改动 0 restart
- NVU_GLM52_EXP_BACKOFF 不在 env 中 = 半成品仍冻结

## 根因分析 (为何 R2111 恶化但本轮已自愈 + 不应改代码)

1. **R2111 的 30min 急剧恶化是瞬态 NVCF 上游 429/SSL 抖动风暴, 已自愈**:
   - R2111 在 CST 03:12 拉数据时正好踩在 02:45-03:00 风暴高峰尾部 (18:55 桶 502×19 峰值主导 30min 大窗)
   - 本轮 CST 03:25 拉数据, 30min 大窗仍含 02:45-03:00 高峰 (70.4%), 但最近 15/20min 小窗已恢复到 90.6%/92.7% 稳态区间, tier 429 回落 10→1
2. **502 仍全 NVCF 上游已知类 (all_tiers_exhausted + zombie), 0 新可配置类** — 不是网关逻辑 bug, 是上游 NVCF rate limit / SSL 抖动。
3. **恶化的根因在 NVCF 上游 429/SSL, 非网关旋钮**: tier 30min 429_nv_rate_limit×1 + pexec_SSLEOFError×3 (vs R2111 风暴期 429×10 + SSL×4) → tier retry 已基本吸收 → 当前剩余主要是 RemoteDisconnected 连接抖动。KEY_COOLDOWN_S=60 / TIER_COOLDOWN_S=180 是 peer R2108 已调高的值, cc2 不碰 peer 改过的旋钮。
4. **系统在吸收没失控**: fallback 6 全兜 0 真中断 0 失败 / breaker 30min recorded=0 未 OPEN / BUG-A 仍触发 4 次 / abs_cap 30min=0 — 所有保险机制正常工作, 0 真中断达成。
5. **此刻不是解冻指数退避半成品的时机**: 429 风暴时延长 chain_budget 120→420 会让单请求在死 key 上挂更久, 反而拖累整体 SR; cc4101 header 60→450 同理。解冻需 in-vivo 验证 + 24h 观测, 当前恶化是上游抖动非逻辑缺陷, 解冻不对症。

## 决策: NOP 巡检 + R2111 风暴自愈确认 (连续第 84 轮冻结)

- 0 改动 0 restart。
- 冻结理由 (连续第 84 轮) 仍成立: 半成品未经 in-vivo 验证 (env 开关从未激活) + 激活需同步 chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key 未实现 + 24h 观测窗口。R2111 的瞬态恶化已自愈, 非网关逻辑缺陷, 解冻不对症。
- **本轮关键确认**: R2111 记录的"连续 82 轮冻结后首次跌破 90%"事件是**瞬态风暴非持续恶化** — 最近 15/20min SR 已回到 90.6%/92.7%, tier 429 回落 10→1。下一轮重点看 30min SR 是否完全回到 94-96% 稳态区间 (风暴完全滚出 30min 窗口需 CST 03:30 后)。

## 验证

- 本轮 0 改动 → 无 restart → /health ok + docker inspect StartedAt 仍 18:10:28Z 未漂移 = 确认本轮无操作, 系统状态与拉数据时一致。
- "用户诉求可以报错但不能让 cc2 中断" 仍达成 (R2112 0 真中断; 6 条 FALLBACK-OK 全被 ms_gw 兜住, 0 fallback 失败)。

## 状态变化 (cc2 视角)

- nv_gw StartedAt 仍 18:10:28Z (连续第 5 轮核实未漂移), env 仍 peer R2108 改后值 (KEY60/TIER180/MIN_OUTBOUND10), cc2 0 改动 0 restart。
- 本轮需记录的变化: (1) **R2111 风暴已自愈** — 最近 15/20min SR 回到 90.6%/92.7% (vs R2111 30min 66.6%), 30min 大窗仍 70.4% 因含 02:45-03:00 高峰污染; (2) tier 30min 429_nv_rate_limit 10→1 大幅回落 + pexec_SSLEOFError 4→3 (NVCF 上游 429/SSL 风暴平息); (3) 502 44→40 (30min, 全 all_tiers+zombie NVCF 已知类 0 新可配); (4) fallback 7→6 全兜 0 真中断 0 失败 0 条 120s 跑满 (持平); (5) breaker/BUG-A/abs_cap 全部未恶化持平。

HM2 only. (cc2 用 R2112 hm2_cc2 前缀避撞号; peer hm2_optimize_hm1 改 HM1 KEY_COOLDOWN 75→77/TIER_COOLDOWN 68→70/EMPTY_200_FASTBREAK 1→2 不碰 cc2 nv_gw 链路)。
