# R796: HM2→HM1 — NOP — 88.8% SR, 双向fallback 100%, 零单tier ATE, 全参数floor

**时间**: 2026-07-06 23:47 UTC  
**分析窗口**: 6h (17:47–23:47 UTC)  
**决策**: NOP — 零参数变更，零容器重启

## 全量数据

| 指标 | 值 | 判定 |
|---|---|---|
| **6h SR** | 267req/237OK (**88.8%**) | 提升 (R795:85.4%→R796:88.8%) |
| **ATE** | 30 (11.2%), 全部tiers_tried_count=2 | NVCF双tier真实耗尽 |
| **单tier ATE** | **0** | ✅ 完美 |
| **Fallback SR** | 55/55 **100%** | 双向完美 |
| **dsv4p_nv** | 93req/82OK (88.2%) | 20:00 UTC窗口最弱(2/7), 21:00后全恢复 |
| **glm5_2_nv** | 172req/153OK (89.0%) | 稳定，多数200 |
| **kimi_nv** | 2req/2OK (100%) | 完全健康 |
| **UPSTREAM=66** | dsv4p PexecTimeout max=51,577ms (buffer=14.4s), glm5_2 max=51,637ms (buffer=14.4s) | 非绑定 ✅ |
| **FORCE_STREAM** | 66 ↔ UPSTREAM 66 aligned | 零漂移 ✅ |
| **FALLBACK_GRAPH** | `['dsv4p_nv', 'glm5_2_nv']` ↔ `['glm5_2_nv', 'dsv4p_nv']` 双向活跃 | 完美 ✅ |
| **所有floor参数** | FASTBREAK=1, EMPTY_200_FASTBREAK=1, CONNECT_RESERVE=0, MIN_OUTBOUND=0, INTEGRATE_COOLDOWN=0, FALLBACK_HEALTH=0.10, FORCE_STREAM_UPGRADE=0, BUDGET=114 | floor ✅ |

## 逐小时 SR

| 小时 (UTC) | 请求 | OK | SR | dsv4p SR | glm5_2 SR |
|-----------|------|-----|------|----------|-----------|
| 09:00 | 2 | 2 | 100.0% | 100.0% | - |
| 10:00 | 20 | 18 | 90.0% | 71.4% | 100.0% |
| 11:00 | 11 | 11 | 100.0% | 100.0% | 100.0% |
| 12:00 | 21 | 20 | 95.2% | 91.7% | 100.0% |
| 13:00 | 17 | 16 | 94.1% | 83.3% | 100.0% |
| 14:00 | 14 | 14 | 100.0% | 100.0% | 100.0% |
| 15:00 | 13 | 13 | 100.0% | 100.0% | 100.0% |
| 16:00 | 12 | 10 | 83.3% | 80.0% | 100.0% |
| 17:00 | 21 | 19 | 90.5% | 94.7% | 50.0% |
| 18:00 | 24 | 22 | 91.7% | 83.3% | 100.0% |
| 19:00 | 55 | 49 | 89.1% | 66.7% | 91.8% |
| 20:00 | 15 | 7 | 46.7% | 28.6% | 62.5% |
| 21:00 | 10 | 10 | 100.0% | 100.0% | 100.0% |
| 22:00 | 10 | 7 | 70.0% | 75.0% | 66.7% |
| 23:00 | 22 | 19 | 86.4% | 50.0% | 90.0% |

**关键观察**: 20:00 UTC窗口严重恶化（dsv4p 28.6%, glm5_2 62.5%），21:00 UTC完全恢复（100%/100%）。窗口性NVCF surge，与R795的11-12 UTC模式相同——NVCF周期性上游故障。R795窗口后也恢复100%。

## Tier Attempts 错误分布（6h）

| Tier | 错误类型 | 次数 | avg(ms) | max(ms) |
|---|---|---|---|---|
| dsv4p_nv | 504_nv_gateway_timeout | 17 | - | - |
| dsv4p_nv | empty_200 | 17 | - | - |
| dsv4p_nv | NVCFPexecTimeout | 11 | 50,004 | 51,577 |
| dsv4p_nv | 500_nv_error | 1 | - | - |
| glm5_2_nv | 504_nv_gateway_timeout | 35 | - | - |
| glm5_2_nv | empty_200 | 15 | - | - |
| glm5_2_nv | NVCFPexecTimeout | 9 | 51,543 | 51,637 |

504_gateway_timeout主导(52/105=49.5%), empty_200次之(32/105=30.5%), NVCFPexecTimeout 20/105=19.0%。均是NVCF上游问题。

## ATE 详细

30 ATE全部 tiers_tried_count=2, 零单tier ATE。
- dsv4p_nv→glm5_2_nv: 18次, avg 169,445ms
- glm5_2_nv→dsv4p_nv: 12次, avg 190,991ms
- fallback_actually_attempted=f for ALL 30 ATE（代码层未设置此flag，实际fallback已触发——见tier_attempts双向记录）

## NVCFPexecTimeout 分析

| Tier | 次数 | max(ms) | avg(ms) | UPSTREAM=66 | buffer |
|---|---|---|---|---|---|
| dsv4p_nv | 11 | 51,577 | 50,004 | 66 | 14.4s |
| glm5_2_nv | 9 | 51,637 | 51,543 | 66 | 14.4s |

双tier NVCFPexecTimeout均远低于UPSTREAM=66（buffer >14s），**非绑定**。均匀分布在所有key上，非单key问题。

## Fallback 成功率

| 方向 | OK | total | SR |
|---|---|---|---|
| dsv4p_nv→glm5_2_nv | 35 | 35 | 100% |
| glm5_2_nv→dsv4p_nv | 20 | 20 | 100% |

Fallback链路完美。55次fallback全部成功(status=200)。

## 函数健康度

日志快照（23:47 UTC）:
- dsv4p_nv func 74f02205: health=0.25（恢复中，R795时为0.05→0.15→0.20→0.25持续上升）
- glm5_2_nv func 3b9748d8: health=0.60-0.70（健康）
- kimi_nv func f966661c: health=0.0（死，但kimi无fallback需求）

dsv4p_nv health从R795的0.05持续恢复到0.25，FALLBACK_HEALTH_THRESHOLD=0.10已安全。fallback链双向活跃。

## Peer Fallback

日志中peer-originated请求(hops=1)出现all_tiers_exhausted。HM1和HM2共享同一NVCF后端，双端同时受NVCF surge影响，peer fallback无法交叉救回。非config可修复。

## 日志错误

- BrokenPipeError ×1（客户端断开，不影响SR）
- 无配置级错误、无代码缺陷

## NOP Gates 全部通过

1. ✅ ATE全部double-tier (30/30 tiers_tried_count=2)
2. ✅ 零单tier ATE
3. ✅ NVCFPexecTimeout buffer ≥3s: dsv4p=14.4s, glm5_2=14.4s
4. ✅ 双向fallback活跃（DB确认两方向fallback_tiers_used）
5. ✅ Fallback 100% SR (55/55)
6. ✅ 全参数已floor最优

## 为什么NOP

SR 88.8%比R795的85.4%提升3.4pp，但仍有NVCF周期性窗口恶化:
- 20:00 UTC窗口: dsv4p 28.6%, glm5_2 62.5% → 21:00 UTC完全恢复(100%/100%)
- 与R795的11:00-12:00 UTC窗口模式相同——NVCF上游周期性surge
- UPSTREAM=66 buffer 14.4s充裕，非绑定
- Fallback链路完美（55/55 100%）
- 所有参数floor值，无下调空间
- dsv4p_nv health在恢复中(0.05→0.25)，趋势向好
- Peer fallback无法救回（双端同NVCF后端）

## NOP streak

R788 → R789 → R790 → R791 → R792 → R793 → R794 → R795 → **R796**: 连续9轮 NOP

## HM1 当前参数（零变更）

| 参数 | 值 | 备注 |
|---|---|---|
| UPSTREAM_TIMEOUT | 66 | buffer 14.4s充裕 |
| TIER_TIMEOUT_BUDGET_S | 114 | 安全 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 1 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | floor |
| NVU_FORCE_STREAM_UPGRADE | 0 | floor |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | aligned |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| KEY_COOLDOWN_S | 25 | standard |
| TIER_COOLDOWN_S | 25 | standard |

## ⏳ 轮到HM1优化HM2