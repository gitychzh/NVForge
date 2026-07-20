# R2111 (hm2_cc2): NOP R147 巡检 — 30min 急剧恶化事件记录 (连续第 83 轮冻结)

> 本轮不编码、不 restart。**记录连续 82 轮稳态后首次出现的 30min 恶化事件**,
> 供后续 session 评估是否解冻。0 改动 0 restart 0 真中断。

## 数据 (本 session 拉取, 当前 CST 03:12; 30min 干净窗口 02:42-03:12)

### 30min nv_gw (干净窗口, 重启后稳态期, vs R2110 94.4%)

- status: 200×94 / **502×44** / 429×3 → **SR = 94/141 = 66.6%** (vs R2110 94.4% **-27.8pp, 连续 82 轮冻结首次跌破 90%**)
- 502 error_type: **all_tiers_exhausted×44** + zombie_empty_completion×3 (全 NVCF 上游已知类, **0 新可配置类**)
- 429=3 (vs R2110 0) ← NVCF rate limit 显化上浮

### 30min tier (vs R2110 tier 0 个 429 干净 — 恶化核心信号)

- pexec_success×31 / **429_nv_rate_limit×10** / NVCFPexecRemoteDisconnected×9 / pexec_conn_RemoteDisconnected×5 / **pexec_SSLEOFError×4**
- vs R2110 tier (pexec_success×31 / NVCFPexecRemoteDisconnected×9 / pexec_conn_RemoteDisconnected×4, 0 个 429):
  **429_nv_rate_limit 0→10 回归 + pexec_SSLEOFError 新出现×4** → NVCF 上游 rate limit + SSL 抖动 → tier retry 没能全吸收 → 上浮成 all_tiers_exhausted 502。

### 6h (仍含远古风暴污染, 不采信)

- status: 502×1269 / 200×328 / 429×104 → 6h SR 失真 (全 peer R2107 重启前 01:52-02:10 dsv4p 429 风暴期污染; 等 CST 08:10 后 6h 窗口完全滚出风暴期才采信)
- 6h 502 error_type: all_tiers_exhausted×1354 + zombie×16 + stream_absolute_cap×2 + stream_first_byte_timeout×1

### 未恶化部分 (系统在吸收, 没有失控)

- **0 真中断**: cc4101 30min `both failed|ms.*fail|UPSTREAM-ERROR-SEEN` = **0** ✅
- **fallback 7 全兜住**: 全 7 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (header/ttfb timeout 75s < chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类 cc4101 bug3 preempt 层)。**0 条 120s 跑满类** (vs R2110 含 1 条 b4db8071, 本轮已滚出窗口)。req 样本: 50b17a02/26a4741c/9df0b402/79408dc9/21c6763d/957185ef/5729c737。全 7 条被 cc4101 抢断切 ms, ms 救回 → 0 条 fallback 失败 → CC 收 0 真 502。
- **breaker**: cc4101 PRIMARY-BREAKER-OPEN 30min = **0**; nv_gw 30min `BREAKER-FAIL|BREAKER.*OPEN|NV-ANTH-BREAKER-FAIL` = **0**。state CLOSED, count 仍 2 未累积到 OPEN 阈值 = **连续第 19 轮验证未恶化机制正常吸收**。
- **BUG-A 修复 (R1913) 仍生效**: 30min `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **5 次** (vs R2110 5 次持平, 持续复活触发中) ✅
- **abs_cap 30min = 0** (6h=2 全远古偶发非 R1918 cap_origin 失效) ✅

### nv_gw /health + StartedAt

- /health = ok (proxy_role=passthrough, nv_num_keys=5, nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=dsv4p_nv, port=40006)
- nv_gw StartedAt = **2026-07-20T18:10:28Z** (= R2107 首次记录 05:57→18:10 漂移后, 连续第 4 轮核实未再漂移)
- cc4101 StartedAt = 2026-07-19T12:10:22Z (0 restart 未变)
- docker ps: nv_gw Up About an hour (与 StartedAt 18:10:28Z UTC = 02:10:28 CST 到当前 03:12 CST ≈ 62min 吻合)

## 根因分析 (为何本轮恶化但不应改代码)

1. **502 仍全 NVCF 上游已知类 (all_tiers_exhausted + zombie), 0 新可配置类** — 不是网关逻辑 bug, 是上游 NVCF rate limit / SSL 抖动。
2. **恶化的根因在 NVCF 上游 429/SSL, 非网关旋钮**: tier 30min 429_nv_rate_limit×10 + pexec_SSLEOFError×4 → tier retry 没全吸收 → 上浮成 all_tiers_exhausted 502。KEY_COOLDOWN_S=60 / TIER_COOLDOWN_S=180 是 peer R2108 已调高的值, **再调高会进一步压缩可用 key 窗口** (已有 429=3 说明 key 已在 cooldown 边缘), cc2 不碰 peer 改过的旋钮。
3. **系统在吸收没失控**: fallback 7 全兜 0 真中断 0 失败 / breaker 30min recorded=0 未 OPEN / BUG-A 仍触发 5 次 / abs_cap 30min=0 — 所有保险机制正常工作, 0 真中断达成。
4. **此刻不是解冻指数退避半成品的时机**: 429 风暴时延长 chain_budget 120→420 会让单请求在死 key 上挂更久, 反而拖累整体 SR; cc4101 header 60→450 同理。解冻需 in-vivo 验证 + 24h 观测, 当前恶化是上游抖动非逻辑缺陷, 解冻风险/收益不对等。

## 决策: NOP 巡检 + 恶化记录 (连续第 83 轮冻结)

- 0 改动 0 restart。
- 冻结理由 (连续第 83 轮) 仍成立: 半成品未经 in-vivo 验证 (env 开关从未激活) + 激活需同步 chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key 未实现 + 24h 观测窗口。当前恶化是 NVCF 上游 429/SSL 抖动, 非网关逻辑缺陷, 解冻不对症。
- **提高警觉 (本轮新触发)**: 30min SR 首次跌破 90% (66.6%) + tier 429 回归 (0→10) + pexec_SSLEOFError 新出现。下一轮重点看 30min SR 是否回升 (NVCF 上游抖动通常自愈) 还是持续低位; 若持续跌破 90% 且 502 出新可配置类, 需重新评估解冻或动网关旋钮。

## 验证

- 本轮 0 改动 → 无 restart → /health ok + docker ps nv_gw Up About an hour + StartedAt 仍 18:10:28Z 未漂移 = 确认本轮无操作, 系统状态与拉数据时一致。
- "用户诉求可以报错但不能让 cc2 中断" 仍达成 (R2111 0 真中断; 7 条 FALLBACK-OK 全被 ms_gw 兜住, 0 fallback 失败)。

## 状态变化 (cc2 视角)

- nv_gw StartedAt 仍 18:10:28Z (连续第 4 轮核实未漂移), env 仍 peer R2108 改后值 (KEY60/TIER180/MIN_OUTBOUND10), cc2 0 改动 0 restart。
- 本轮需记录的变化: (1) **30min SR 94.4%→66.6% -27.8pp 首次跌破 90%** (连续 82 轮冻结后首次); (2) tier 30min 429_nv_rate_limit 0→10 回归 + pexec_SSLEOFError 新出现×4 (NVCF 上游 429/SSL 抖动); (3) 502 7→44 全 all_tiers_exhausted + zombie×3 NVCF 已知类 0 新可配; (4) fallback 7→7 持平但 120s 跑满类本轮 0 条 (b4db8071 已滚出); (5) breaker/BUG-A/abs_cap 全部未恶化持平。

HM2 only. (cc2 用 R2111 hm2_cc2 前缀避撞号; peer hm2_optimize_hm1/oc2/hermes2 改 HM1/5US 代理不碰 cc2 nv_gw 链路)。
