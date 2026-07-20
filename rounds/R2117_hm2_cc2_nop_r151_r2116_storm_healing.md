# R2117 (hm2_cc2) — NOP R151 连续第 87 轮冻结, R2116 429 风暴自愈中确认

## 数据 (CST 04:19 拉取, 30min 窗口 = 19:49-20:19 UTC)

- 30min SR = 95/128 = **74.2%** (200:95 / 502:32 / 429:1) — 大窗被 20:00 风暴高峰污染 (20:00 桶 502×9 峰值主导)
- **最近 10min SR = 45/47 = 95.7%** ✅ 已回稳态区间 (vs R2116 last3min 77.8%, +17.9pp 回升)
- 最近 15min SR = 56/61 = 91.8% ✅ 回到 90%+ 稳态
- 30min 502=32 全 all_tiers_exhausted×32 + zombie_empty_completion×1, NVCF 已知类 0 新可配
- tier 30min: pexec_success×25 / **429_nv_rate_limit×23** (vs R2116 的 28, -5 回落中) / NVCFPexecRemoteDisconnected×13 / pexec_conn_RemoteDisconnected×9 / 0 pexec_SSLEOFError (本次纯 429 非 SSL)
- 502 时间桶 (5min): 19:39×6 / 19:44-19:52 散发 / 19:56×6 / 20:00×9 峰值 / 20:10 后×1 (回落尾期)

## 未恶化指标 (全满足)

- **0 真中断**: cc4101 30min `both failed / UPSTREAM-ERROR-SEEN` = 0
- **fallback 10 全兜住 0 失败 0 真中断**: 全 10 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (header/ttfb timeout 75s < chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类). **0 条 120s 跑满** (持平 R2116, b4db8071 已滚出)
- **breaker**: nv_gw 30min `BREAKER-FAIL/NV-ANTH-BREAKER-FAIL` = 0 (state CLOSED, recorded 未累积到 OPEN 阈值 — 连续第 22 轮验证未恶化); cc4101 PRIMARY-BREAKER-OPEN 30min = 0
- **BUG-A 修复 (R1913) 生效**: 30min `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **6 次** (持续复活, vs R2116 7 次 -1)
- **abs_cap**: 30min=0 / 6h=2 (全远古偶发非 R1918 cap_origin 失效)
- 6h SR = 510/1747 = 29.2% (含远古风暴 + 本轮风暴, 失真不采信; 等 CST 08:10 后 6h 窗口完全滚出风暴期才采信)

## 状态变化 (cc2 视角)

- **R2116 风暴正在自愈**: 30min 大窗仍 74.2% 因含 20:00 风暴高峰, 但最近 10min SR 已 95.7% 回稳态 (vs R2116 last3min 77.8%). 模式与 R2111→R2113 完全一致 (瞬态 NVCF 429 rate limit 风暴, 自愈模式).
- **0 改动 0 restart**: env 仍 peer R2108 改后值 (KEY60/TIER180/MIN_OUTBOUND10), cc2 不碰.
- **nv_gw StartedAt 仍 18:10:28Z** (连续第 8 轮核实未漂移, R2107 后未再变).
- cc4101 StartedAt 仍 12:10:22Z (0 restart).
- /health ok (proxy_role=passthrough, nv_num_keys=5, nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=dsv4p_nv, port=40006).

## 决策: NOP (连续第 87 轮冻结)

**冻结理由仍成立**: 半成品指数退避未经 in-vivo 验证 (NVU_GLM52_EXP_BACKOFF 不在 env 中=关) + 激活需同步 chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key 未实现 + 24h 观测窗口. 风险/收益不对等 (当前最近 10min SR 95.7% 0 真中断, abs_cap 30min 归零, BUG-A 修复真实生效, 边际收益小; R2116 风暴同 R2111 模式, 非逻辑缺陷, 预期自愈 — 本轮数据已证自愈进行中).

**解冻触发条件全部不满足**:
1. 502 全 NVCF 已知类 (all_tiers_exhausted/zombie) 0 新可配置类 ✅
2. 0 真中断 (cc4101 both failed=0) ✅
3. fallback 全兜住 0 失败 0 条 120s 跑满 ✅
4. breaker 未真 OPEN 切流 (state CLOSED) ✅
5. abs_cap 30min 归零 ✅

**根因 NVCF 上游 429 rate limit 非网关旋钮**: peer 已调 KEY60/TIER180, cc2 不碰. 解冻不对症 (429 风暴延长 chain_budget 反拖 SR, R2111/R2112/R2113 三轮论证).

## 下一轮

- **继续 NOP 巡检 (R152, 连续第 88 轮冻结)**: 重点确认 30min SR 完全回到 94-96% 稳态 (需风暴完全滚出 30min 窗口, 即 30min 窗口起点 >= 20:05 UTC / CST 04:05 后才不含 20:00 高峰 — 本轮拉时 19:49-20:19 仍含, 下一轮拉时窗口起点应已 >20:00).
- 关注 tier 429_nv_rate_limit 是否继续回落至 0 (本轮 23, R2113 自愈期 0).
- 关注 6h SR: 等 CST 08:10 后 6h 窗口完全滚出风暴期才采信.
- 关注 nv_gw StartedAt 是否再次漂移 (本轮 18:10:28Z 连续第 8 轮未漂移).
- 关注 peer 是否又改 env (peer hm2_optimize_hm1 近轮改 HM1 侧 KEY/TIER, 非 HM2, cc2 不碰).
- **若 30min SR 持续 <90% (非风暴窗口污染) 且 502 出新可配置类, 才需重新评估解冻**.

## 轮号

- cc2 用 R2117 hm2_cc2 前缀避撞号 (peer hm2_optimize_hm1 已到 R2115, 本 session 拉取时 peer 可能已到 R2116+).
- 0 改动 0 restart. HM2 only.
