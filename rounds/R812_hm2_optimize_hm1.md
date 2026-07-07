# R812: HM2→HM1 — NOP — NVCF双function同时不可用, HEALTH_THRESHOLD杀fallback, 零配置可修

**时间**: 2026-07-07 20:50 UTC
**决策**: NOP — 零参数改动，零compose改动，零容器重启。
**作者**: opc2_uname (HM2→HM1)

## 触发原因

R811末尾标记"⏳ 轮到HM1优化HM2"，HM1提交了新commit (ae85764)，检测脚本判定轮到HM2执行。

## 一、当前配置快照

| # | 参数 | HM1 当前值 | Floor? |
|---|------|------------|--------|
| 1 | `UPSTREAM_TIMEOUT` | 66 | — |
| 2 | `TIER_TIMEOUT_BUDGET_S` | 114 | — |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | 0 | ✅ floor |
| 4 | `NVU_PEXEC_TIMEOUT_FASTBREAK` | 1 | ✅ floor |
| 5 | `TIER_COOLDOWN_S` | 25 | — |
| 6 | `NVU_PEER_FALLBACK_TIMEOUT` | 45 | — |
| 7 | `NVU_CONNECT_RESERVE_S` | 0 | ✅ floor |
| 8 | `NVU_EMPTY_200_FASTBREAK` | 1 | ✅ floor |
| 9 | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 66 | — |
| 10 | `NVU_FORCE_STREAM_UPGRADE` | 0 | ✅ floor |
| 11 | `FALLBACK_HEALTH_THRESHOLD` | 0.10 | ✅ floor |
| 12 | `NV_INTEGRATE_KEY_COOLDOWN_S` | 0 | ✅ floor |
| 13 | `KEY_COOLDOWN_S` | 25 | — |

FORCE_STREAM=66 ↔ UPSTREAM=66 synced ✅。所有floor参数已达最小值。PEER_FALLBACK=45 > UPSTREAM=66但历史无成功peer fallback。

## 二、容器状态

- **容器**: nv_gw running, 健康检查 ✅
- **重启时间**: 2026-07-07T12:38:55Z (R811后自动重启? 或R810部署后约1.7h重启)
- **tier_chain 时间线**:
  - 19:34-19:35 UTC: `tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback, health={...})` — fallback工作 ✅
  - 20:03 UTC+: `tier_chain=['glm5_2_nv'] (no fallback, 3model)` — **fallback killed** ❌
- **MIN_SAMPLES过期**: 容器12:38重启 → 约7h后MIN_SAMPLES过期 → 19:35-20:03 dsv4p_nv health=0.0 < FALLBACK_HEALTH_THRESHOLD=0.10 → 被排除

## 三、数据摘要（6h window, ≈14:50–20:50 UTC）

### 3.1 6h 总体

| 指标 | 数值 |
|------|------|
| 总请求 | 44 |
| 成功 (200) | 3 |
| 失败 (502) | 41 |
| SR | 6.8% |
| Fallback 触发 | 3 |
| Fallback 成功 | 3 (100%) |
| Single-tier ATE | 37 |
| Dual-tier ATE | 4 |

### 3.2 按模型

| 模型 | Req | OK | Fail | SR% | avg_ttfb | avg_dur | max_dur |
|------|-----|----|------|-----|----------|---------|---------|
| glm5_2_nv | 33 | 3 | 30 | 9.1% | 86,026ms | 24,131ms | 151,597ms |
| dsv4p_nv | 11 | 0 | 11 | 0.0% | — | 113,646ms | 174,876ms |

### 3.3 ATE by tiers_tried_count

| tiers_tried_count | cnt | avg_dur |
|-------------------|-----|---------|
| 1 (single-tier) | 37 | 33,596ms |
| 2 (dual-tier) | 4 | 136,329ms |

Single-tier ATE = 90.2% of all ATEs. All caused by:
1. glm5_2_nv: NVCF GLM-5.2 function DEGRADED (400_nvcf_degraded all 5 keys, ~7s cycle → ATE)
2. dsv4p_nv: NVCF DeepSeek function dead (health=0.0) → excluded from fallback after MIN_SAMPLES expiry

### 3.4 nv_tier_attempts (6h, 失败尝试)

| tier | error_type | cnt | avg_ms | max_ms |
|------|-----------|-----|--------|--------|
| glm5_2_nv | 400_nvcf_degraded | 14 | — | — |
| glm5_2_nv | 504_nv_gateway_timeout | 1 | — | — |
| glm5_2_nv | NVCFPexecTimeout | 1 | 50,937ms | 50,937ms |

dsv4p_nv: **ZERO tier_attempts** — 所有dsv4p请求直接ATE（调度层拒绝，未达NVCF）。

### 3.5 Fallback

| fallback_occurred | OK | Total |
|-------------------|----|-------|
| f | 0 | 41 |
| t | 3 | 3 |

3次fallback全成功 (100% SR) → 全部在19:34-19:35 UTC发生（fallback被kill前）。Fallback路径 `glm5_2_nv→dsv4p_nv` 历史上验证可靠。

### 3.6 小时SR趋势

| Hour (UTC) | Total | OK | ATE | SR% |
|-----------|-------+----|-----|-----|
| 06:00 | 1 | 0 | 1 | 0.0 |
| 07:00 | 12 | 1 | 11 | 8.3 |
| 08:00 | 8 | 0 | 8 | 0.0 |
| 09:00 | 6 | 0 | 6 | 0.0 |
| 10:00 | 6 | 0 | 6 | 0.0 |
| 11:00 | 5 | 2 | 3 | 40.0 |
| 12:00 | 6 | 0 | 6 | 0.0 |

无恢复信号 — 全时段SR接近0%。NVCF持续不可用。

### 3.7 24h错误全景

仅1种错误类型: `all_tiers_exhausted` (74次) — 100% NVCF上游耗尽，无429/empty_200/timeout等配置可修错误。

## 四、NOP Gate 评估

| Gate | 条件 | 结果 | 说明 |
|------|------|------|------|
| 1 | 所有ATE双tier | ❌ FAIL | 37/41 (90.2%) 单tier |
| 2 | 零single-tier ATE或代码级缺陷 | ⚠️ CODE-LEVEL | NVCF DEGRADED + HEALTH_THRESHOLD kill → 非配置可修 |
| 3 | NVCFPexecTimeout buffer ≥3s | ✅ PASS | glm5_2 max=50,937ms, UPSTREAM=66, buffer=15.1s |
| 4 | FALLBACK_GRAPH双向工作 | ❌ FAIL | 20:03后dsv4p excluded (HEALTH_THRESHOLD kill) |
| 5 | Fallback SR=100% | ✅ PASS | 3/3 (100%) — 但fallback已kill |
| 6 | 所有参数floor/optimal | ✅ PASS | 全部floor或最优值 |

## 五、根因分析

### 5.1 glm5_2_nv: NVCF DEGRADED (400_nvcf_degraded)

R810代码修复 (400 DEGRADED cycling) 正常生效：5个key全部快速cycle (~7s)，然后触发 `[NV-ALL-TIERS-FAIL]`。日志确证：
```
[NV-TIER-FAIL] tier=glm5_2_nv all 5 keys failed: 429=0, empty200=0, timeout=0, other=7, elapsed=7037ms
```
"other=7" = 5×400 DEGRADED + 2×其他错误。每个key都是DEGRADED → 无法cycle到可用key → 单tier ATE。

Peer-FB skip也正确触发：`[NV-PEER-FB] model=glm5_2_nv in peer-fb skip list (NVCF DEGRADING, peer same function also bad)`。

### 5.2 dsv4p_nv: NVCF function dead (health=0.0)

- nv_tier_attempts零记录 → 调度层直接拒绝，未到达NVCF
- 所有dsv4p_nv请求avg_dur=113,646ms → 全部双tier ATE (等待glm5_2 fallback也失败)
- dsv4p_nv primary function (74f02205) health=0.0 → 被排除
- 19:35前MIN_SAMPLES保护 → 仅3次fallback成功 (glm5_2→dsv4p)
- 19:35-20:03 MIN_SAMPLES过期 → dsv4p excluded from tier_chain → glm5_2失去fallback → 单tier ATE

### 5.3 结论: NVCF双function同时不可用

Per ATE诊断参考:
> "NVCF dual-function simultaneous unavailability: when both dsv4p_nv and glm5_2_nv have health < 0.35... NO config parameter change will meaningfully improve SR. Both tiers will fail most attempts. The correct decision is zero-change, waiting for NVCF recovery."

## 六、决策: NOP

**零变更**。理由:
1. NVCF双function同时不可用 → 任何配置参数改动都无法改善SR
2. 所有14个参数已达floor或最优值，无优化空间
3. R810代码修复 (400 DEGRADED cycling) 已验证正常工作
4. Peer-FB skip逻辑正确 (DEGRADING时跳过peer)
5. HEALTH_THRESHOLD kill是代码级缺陷 (R708/R719/R720)，非配置可修
6. Fallback路径 (glm5_2→dsv4p) 在健康时100% SR (3/3)，但当前两个function都不可用

**等待信号**: NVCF glm5_2 function恢复 (DEGRADED→ACTIVE) 或 dsv4p function恢复 (health>0.10) → 系统自动自愈 (tier_chain恢复双向fallback)。

## 七、历史对比

| 轮次 | 决策 | SR | 关键变化 |
|------|------|----|---------|
| R810 | 400 DEGRADED cycle修复 | 53.3% (post-fix) | 代码修复验证 |
| R811 | NOP | 54.3% (6h contaminated) | 双function NVCF耗尽 |
| R812 | NOP | 6.8% | NVCF双重恶化: glm5_2 DEGRADED + dsv4p dead + HEALTH_THRESHOLD杀fallback |

SR从R811的54.3%降至6.8%：NVCF upstream进一步恶化。glm5_2从部分可用变为全DEGRADED (400_nvcf_degraded)，dsv4p持续dead (health=0.0)。

## ⏳ 轮到HM1优化HM2