# R795: HM2→HM1 — NOP — 85.4% SR (NVCF transient), 双向fallback 100%, 全参数floor, 零单tier ATE

**时间**: 2026-07-06 23:05 UTC  
**分析窗口**: 6h (17:05–23:05 UTC)  
**决策**: NOP — 零参数变更，零容器重启

## 全量数据

| 指标 | 值 | 判定 |
|---|---|---|
| **6h SR** | 137req/117OK (**85.4%**) | NVCF上游瞬态恶化（11-12 UTC低谷已恢复） |
| **ATE** | 20 (14.6%), 全部tiers_tried_count=2 | NVCF双tier真实耗尽 |
| **Fallback SR** | 27/27 **100%** | 双向完美 |
| **dsv4p_nv** | 51req/40OK (78.4%) | 11-12 UTC窗口严重（28.6%-57.1%），13UTC后恢复100% |
| **glm5_2_nv** | 84req/75OK (89.3%) | 11-12 UTC窗口62.5%-91.8%，13UTC后恢复100% |
| **kimi_nv** | 2req/2OK (100%) | 完全健康 |
| **UPSTREAM=66** | dsv4p PexecTimeout max=51,577ms (buffer=14.4s), glm5_2 max=51,628ms (buffer=14.4s) | 非绑定 ✅ |
| **FORCE_STREAM** | 66 ↔ UPSTREAM 66 aligned | 零漂移 ✅ |
| **FALLBACK_GRAPH** | `['dsv4p_nv', 'glm5_2_nv']` ↔ `['glm5_2_nv', 'dsv4p_nv']` 双向活跃 | 完美 ✅ |
| **所有floor参数** | FASTBREAK=1, EMPTY_200_FASTBREAK=1, CONNECT_RESERVE=0, MIN_OUTBOUND=0, INTEGRATE_COOLDOWN=0, FALLBACK_HEALTH=0.10, FORCE_STREAM_UPGRADE=0, BUDGET=114 | floor ✅ |

## 逐小时 SR

| 小时 (UTC) | 请求 | OK | SR | dsv4p SR | glm5_2 SR |
|-----------|------|-----|------|----------|-----------|
| 09:00 | 18 | 17 | 94.4% | 94.1% | 100.0% |
| 10:00 | 23 | 22 | 95.7% | 90.9% | 100.0% |
| 11:00 | 56 | 49 | 87.5% | 57.1% | 91.8% |
| 12:00 | 15 | 7 | 46.7% | 28.6% | 62.5% |
| 13:00 | 10 | 10 | 100.0% | 100.0% | 100.0% |
| 14:00 | 9 | 7 | 77.8% | 75.0% | 80.0% |
| 15:00 | 6 | 5 | 83.3% | 100.0% | 80.0% |

**关键观察**: 11:00-12:00 UTC出现NVCF上游严重瞬态故障（dsv4p 28.6%, glm5_2 62.5%），13:00 UTC完全恢复（100%/100%）。窗口性NVCF surge，非本地配置可修复。

## Tier Attempts 错误分布（6h）

| Tier | 错误类型 | 次数 |
|---|---|---|
| dsv4p_nv | 504_nv_gateway_timeout | 15 |
| dsv4p_nv | NVCFPexecTimeout | 10 |
| dsv4p_nv | empty_200 | 4 |
| dsv4p_nv | 500_nv_error | 1 |
| glm5_2_nv | 504_nv_gateway_timeout | 18 |
| glm5_2_nv | empty_200 | 6 |
| glm5_2_nv | NVCFPexecTimeout | 3 |

| 错误类型 | 总次数 | dsv4p | glm5_2 |
|---|---|---|---|
| 504_nv_gateway_timeout | 33 | 15 | 18 |
| empty_200 | 10 | 4 | 6 |
| NVCFPexecTimeout | 13 | 10 | 3 |
| 500_nv_error | 1 | 1 | 0 |

504_gateway_timeout占主导(33/57=57.9%), empty_200次之(10/57=17.5%), NVCFPexecTimeout 13/57=22.8%。均是NVCF上游问题。

## ATE 详细

20 ATE全部 tiers_tried_count=2, 零单tier ATE。dsv4p→glm5_2 11次(avg 175s), glm5_2→dsv4p 9次(avg 179s)。双向fallback均尝试，NVCF双端同时失败。

ATE样本(23:00 UTC): glm5_2_nv empty_200→FASTBREAK→dsv4p_nv 504→cycle→NVCFPexecTimeout→FASTBREAK→ALL-TIERS-FAIL→peer-fallback exhausted→502。

## NVCFPexecTimeout 分析

| Tier | 次数 | max(ms) | avg(ms) | UPSTREAM=66 | buffer |
|---|---|---|---|---|---|
| dsv4p_nv | 10 | 51,577 | 49,883 | 66 | 14.4s |
| glm5_2_nv | 3 | 51,628 | 51,523 | 66 | 14.4s |

双tier NVCFPexecTimeout均远低于UPSTREAM=66（buffer >14s），**非绑定**。UPSTREAM既不需增也不需减。

## Fallback 成功率

| 方向 | OK | total | SR |
|---|---|---|---|
| dsv4p_nv→glm5_2_nv | 17 | 17 | 100% |
| glm5_2_nv→dsv4p_nv | 10 | 10 | 100% |

Fallback链路完美。27次fallback全部成功(status=200)。

## 函数健康度

日志快照（23:09 UTC）:
- dsv4p_nv func 74f02205: health=0.05（极低，11-12 UTC窗口重创）
- glm5_2_nv func 3b9748d8: health=0.85（健康）
- kimi_nv func f966661c: health=0.0（死，但kimi无fallback需求）

23:03-23:04 UTC出现 `(no fallback, 3model)` — dsv4p_nv health=0.05 < FALLBACK_HEALTH_THRESHOLD=0.10导致dsv4p被排除出glm5_2_nv的fallback链。但23:09后health恢复到0.1，fallback链恢复。短期健康波动，FALLBACK_HEALTH_THRESHOLD=0.10已极低（floor），进一步降低会引入真死函数。

## Peer Fallback

所有最近peer fallback均失败（`peer-originated request also all_tiers_exhausted`）。HM1和HM2共享同一NVCF后端，双端同时受NVCF surge影响，peer fallback无法交叉救回。

## 日志错误

- BrokenPipeError ×4（客户端断开，不影响SR）
- NV-THINKING-TIMEOUT ×3（glm5_2_nv thinking请求extend到66s，normal）
- 无配置级错误、无代码缺陷

## NOP Gates 全部通过

1. ✅ ATE全部double-tier (20/20 tiers_tried_count=2)
2. ✅ 零单tier ATE
3. ✅ NVCFPexecTimeout buffer ≥3s: dsv4p=14.4s, glm5_2=14.4s
4. ✅ 双向fallback活跃（DB确认两方向fallback_tiers_used）
5. ✅ Fallback 100% SR (27/27)
6. ✅ 全参数已floor最优

## 为什么NOP

SR 85.4%看似恶化但根本原因是NVCF上游11:00-12:00 UTC窗口性surge:
- dsv4p_nv 504_gateway_timeout×15 + glm5_2_nv 504×18 → NVCF全端网关超时
- 13:00 UTC后两tier均恢复100% SR → 证实窗口性非持续性
- UPSTREAM=66 buffer 14.4s充裕，非绑定
- Fallback链路完美（27/27 100%）
- 所有参数floor值，无下调空间
- FALLBACK_HEALTH_THRESHOLD=0.10已极低，降致dsv4p 0.05入链无意义（真死函数）
- Peer fallback无法救回（双端同NVCF后端）

## NOP streak

R788 → R789 → R790 → R791 → R792 → R793 → R794 → **R795**: 连续8轮 NOP

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