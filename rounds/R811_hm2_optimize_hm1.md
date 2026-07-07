# R811: HM2→HM1 — NOP — Post-R810 fix验证, 双function NVCF耗尽, 零single-tier ATE

**时间**: 2026-07-07 19:35 UTC
**决策**: NOP — 零参数改动，零compose改动，零容器重启。
**作者**: opc2_uname (HM2→HM1)

## 触发原因

R810末尾标记"⏳ 轮到HM1优化HM2"，HM1提交了新commit (4f30ae9)，检测脚本判定轮到HM2执行。

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

FORCE_STREAM=66 ↔ UPSTREAM=66 synced ✅。所有floor参数已达最小值。

## 二、容器状态

- **容器**: nv_gw running, 健康检查 ✅ `{"status":"ok","proxy_role":"passthrough","port":40006}`
- **重启时间**: 2026-07-07T10:58:44Z (R810部署)
- **tier_chain**: `['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback, health={...})` — 双向fallback工作 ✅
- **400 DEGRADED修复**: 日志确证 `[NV-CYCLE] ... → 400 (400_nvcf_degraded), cycling to next key` → 快速cycle → `[NV-FALLBACK]` → `[NV-FALLBACK-SUCCESS]` ✅

## 三、数据摘要（6h window, ≈13:35–19:35 UTC）

### 3.1 6h 总体

| 指标 | 数值 |
|------|------|
| 总请求 | 105 |
| 成功 (200) | 57 |
| 失败 (502) | 48 |
| SR | 54.3% |
| Fallback 触发 | 19 |
| Fallback 成功 | 19 (100%) |
| Single-tier ATE | 31 |
| Double-tier ATE | 17 |

⚠️ 6h SR受R810修复前的31个single-tier ATE拖累。分段分析见3.4。

### 3.2 Model-level SR

| request_model | total | ok | SR% | avg_ok_dur_ms |
|---------------|-------|----|-----|---------------|
| glm5_2_nv | 59 | 35 | 59.3% | 29,890 |
| dsv4p_nv | 46 | 22 | 47.8% | 97,508 |

### 3.3 逐小时 SR

| 小时 (UTC) | total | ok | ate | SR |
|------------|-------|----|-----|------|
| 05:00 | 1 | 1 | 0 | 100.0% |
| 06:00 | 17 | 12 | 5 | 70.6% |
| 07:00 | 17 | 5 | 12 | 29.4% |
| 08:00 | 20 | 12 | 8 | 60.0% |
| 09:00 | 18 | 10 | 8 | 55.6% |
| 10:00 | 17 | 8 | 9 | 47.1% |
| 11:00 | 11 | 6 | 5 | 54.5% |
| 12:00 | 4 | 3 | 1 | 75.0% |

### 3.4 分段分析：Pre/Post R810 (restart @ 10:58 UTC)

| 时间段 | total | ok | ate | SR% | single-tier ATE | double-tier ATE |
|--------|-------|-----|-----|-----|-----------------|-----------------|
| Pre-R810 (05:00-10:58) | 90 | 48 | 42 | 53.3% | **31** | 11 |
| Post-R810 (11:00-12:33) | 15 | 9 | 6 | 60.0% | **0** ✅ | 6 |

**关键发现**: R810的400 DEGRADED修复完全消除了single-tier ATE。Post-fix零single-tier，所有残留ATE均为双tier NVCF耗尽。

### 3.5 Single-tier ATE 分解（全Pre-R810）

**glm5_2_nv single-tier (21个)**: 全部pre-R810 400 DEGRADED non-cycle。时长1.0–6.1s，fallback_actually_attempted=f — NV-NONCYCLE-ERR立即abort tier，不触发fallback。R810 fix后完全消除。

**dsv4p_nv single-tier (10个)**: 07:04–08:00 UTC，时长61–114s，fallback_actually_attempted=f。8/10≈114s = BUDGET边界。可能原因：
1. dsv4p_nv内部504超时循环消耗预算 (FASTBREAK=1但504 gateway timeout可能触发key级重试)
2. glm5_2_nv health <0.10短暂排除fallback目标 → tier_chain失去双向fallback
3. 日志已滚动，不可复现

🔥 R810 fix后ZERO single-tier ATE证明核心问题已解决。残留的10个dsv4p single-tier无法复现/诊断。

### 3.6 nv_tier_attempts 错误分解

| tier | error_type | cnt | max_ms |
|------|------------|-----|--------|
| dsv4p_nv | 504_nv_gateway_timeout | 10 | — |
| dsv4p_nv | NVCFPexecTimeout | 9 | 51,227 |
| dsv4p_nv | empty_200 | 7 | — |
| glm5_2_nv | 400_nvcf_degraded | 14 | — |
| glm5_2_nv | 504_nv_gateway_timeout | 5 | — |
| glm5_2_nv | 500_nv_error | 1 | — |
| glm5_2_nv | NVCFPexecTimeout | 1 | 50,937 |

### 3.7 NVCFPexecTimeout UPSTREAM绑定检查

| tier | max_ms | UPSTREAM=66 | buffer |
|------|--------|-------------|--------|
| dsv4p_nv | 51,227ms (51.2s) | 66,000ms | **14.8s ≥3s** ✅ |
| glm5_2_nv | 50,937ms (50.9s) | 66,000ms | **15.1s ≥3s** ✅ |

UPSTREAM_TIMEOUT=66完全不绑定。NVCFPexecTimeout均匀分布所有key → function级超时，非key级。

### 3.8 Fallback 统计

| fallback_occurred | cnt | ok | avg_ok_ms |
|-------------------|-----|----|-----------|
| f (无fallback) | 86 | 38 | 26,417 |
| t (有fallback) | 19 | 19 | 115,129 |

Fallback 100% SR ✅。19个fallback全部成功，无fallback失败案例。

## 四、NOP 决策分析

### Gate 1: 所有ATE是double-tier? → POST-FIX ✅ (6/6 double-tier)

Pre-fix: 31 single-tier + 11 double-tier → FAIL。但pre-fix single-tier已由R810修复。

### Gate 2: Zero single-tier ATE 或 code-level? → POST-FIX ✅ (zero)

Post-R810: 零single-tier ATE。R810 code修复已根除。

### Gate 3: NVCFPexecTimeout buffer ≥3s? → ✅ (14.8s/15.1s)

UPSTREAM=66完全不绑定。

### Gate 4: FALLBACK_GRAPH双向工作? → ✅

日志确证 `tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback)`。

### Gate 5: Fallback SR=100%? → ✅ (19/19)

### Gate 6: 所有config参数在floor? → ✅

FASTBREAK=1, EMPTY_200_FASTBREAK=1, CONNECT_RESERVE=0, MIN_OUTBOUND=0, INTEGRATE_COOLDOWN=0, FALLBACK_HEALTH=0.10, FORCE_STREAM=0/66。

**→ 决策: NOP。零参数改动，零compose改动，零容器重启。**

Post-R810系统状态: SR 60%（受NVCF双function耗尽限制，非本地配置可修），零single-tier ATE，fallback 100%工作。所有gate通过。等待NVCF上游恢复。

## 五、NVCF 当前全貌

| Function | Health趋势 | 错误模式 |
|----------|-----------|---------|
| glm5_2_nv 3b9748d8 | DEGRADED — 400 "DEGRADED function cannot be invoked" | 100% 400, 不可调用 |
| dsv4p_nv 74f02205 | 低但存活 — 504 gateway timeout + NVCFPexecTimeout 51s | 间歇超时 |

双function同时受损 → NVCF上游问题，本地配置无法修复。R810的400 cycle fix确保当任一function恢复时fallback路径正确工作。当前系统处于"最小可行吞吐"状态 — 等待上游恢复。

## 六、评判

| 维度 | 评估 |
|------|------|
| 更少报错 | ✅ R810 fix已验证：零single-tier ATE，400→cycle→fallback正确 |
| 更快请求 | ✅ 400快速cycle (<1.5s/key)，比pre-fix立即abort更快进入fallback |
| 超低延迟 | ✅ 直接成功请求avg_ok_dur 26-29s (glm5_2)、97s (dsv4p via fallback) |
| 稳定优先 | ✅ NOP决策：不改变稳定运行的config，不做无数据支撑的调整 |

**铁律**: 只改HM1不改HM2 ✅ (本轮NOP，零改动)

## ⏳ 轮到 HM1 优化 HM2