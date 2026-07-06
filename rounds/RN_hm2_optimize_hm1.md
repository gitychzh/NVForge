# R797: HM2→HM1 — NOP — 88.4% SR (NVCF transient), 双向fallback 100%, 零单tier ATE, 全参数floor

**时间**: 2026-07-07 00:15 UTC  
**分析窗口**: 6h (18:15–00:15 UTC)  
**决策**: NOP — 零参数变更，零容器重启，零compose修改

## 全量数据

| 指标 | 值 | 判定 |
|---|---|---|
| **6h SR** | 276req/244OK (**88.4%**) | 稳定 (R796:88.8%→R797:88.4%, -0.4pp) |
| **ATE** | 32 (11.6%), 全部tiers_tried_count=2 | NVCF双tier真实耗尽 |
| **单tier ATE** | **0** | ✅ 完美 |
| **Fallback SR** | 52/52 **100%** | 双向完美 |
| **dsv4p_nv** | 108req/89OK (82.4%) | 恢复趋势 |
| **glm5_2_nv** | 166req/153OK (92.2%) | 稳定 |
| **kimi_nv** | 2req/2OK (100%) | 完全健康 |
| **UPSTREAM=66** | dsv4p PexecTimeout max=51,577ms (buffer=14.4s), glm5_2 max=51,637ms (buffer=14.4s) | 非绑定 ✅ |
| **FORCE_STREAM** | 66 ↔ UPSTREAM 66 aligned | 零漂移 ✅ |
| **FALLBACK_GRAPH** | `['dsv4p_nv', 'glm5_2_nv']` ↔ `['glm5_2_nv', 'dsv4p_nv']` 双向活跃 | 完美 ✅ |
| **所有floor参数** | FASTBREAK=1, EMPTY_200_FASTBREAK=1, CONNECT_RESERVE=0, MIN_OUTBOUND=0, INTEGRATE_COOLDOWN=0, FALLBACK_HEALTH=0.10, FORCE_STREAM_UPGRADE=0, BUDGET=114 | floor ✅ |

## 逐小时 SR

| 小时 (UTC) | dsv4p SR | glm5_2 SR | 总 SR |
|---|---|---|---|
| 10:00 | 66.7% | 100.0% | 81.8% |
| 11:00 | 100.0% | 100.0% | 100.0% |
| 12:00 | 88.9% | 100.0% | 95.2% |
| 13:00 | 92.3% | 100.0% | 94.1% |
| 14:00 | 100.0% | 100.0% | 100.0% |
| 15:00 | 100.0% | 100.0% | 100.0% |
| 16:00 | 80.0% | 100.0% | 83.3% |
| 17:00 | 93.3% | 83.3% | 90.5% |
| 18:00 | 81.8% | 100.0% | 91.7% |
| 19:00 | 80.0% | 91.1% | 89.1% |
| 20:00 | 0.0% | 70.0% | 46.7% |
| 21:00 | - | 100.0% | 100.0% |
| 22:00 | 50.0% | 75.0% | 70.0% |
| 23:00 | 71.4% | 91.7% | 86.4% |
| 00:00 | 100.0% | 88.9% | 90.9% |

**关键观察**: 20:00 UTC窗口严重恶化（dsv4p 0.0%, glm5_2 70.0%），21:00 UTC已恢复(100%/100%)。周期性NVCF surge与R795/R796模式一致——不可控上游故障。20:00 UTC是持续性3h窗口(18:00–20:00 UTC dsv4p SR下降: 80%→0%)，对应NVCF美国峰后负载波动。

## Tier Attempts 错误分布（6h）

| Tier | 错误类型 | 次数 | avg(ms) | max(ms) |
|---|---|---|---|---|
| glm5_2_nv | 504_nv_gateway_timeout | 39 | - | - |
| dsv4p_nv | 504_nv_gateway_timeout | 19 | - | - |
| dsv4p_nv | empty_200 | 16 | - | - |
| glm5_2_nv | empty_200 | 13 | - | - |
| dsv4p_nv | NVCFPexecTimeout | 10 | 49.9s | 51,577 |
| glm5_2_nv | NVCFPexecTimeout | 7 | 51.5s | 51,637 |

504_gateway_timeout主导(58/104=55.8%), empty_200次之(29/104=27.9%), NVCFPexecTimeout 17/104=16.3%。全是NVCF上游问题。

## ATE 详细

32 ATE全部 tiers_tried_count=2, 零单tier ATE。avg 179.6s, max 229,007ms。两方向均有fallback尝试但均耗尽——NVCF双tier真实不可用。

## NVCFPexecTimeout 分析

| Tier | 次数 | max(ms) | UPSTREAM=66 | buffer |
|---|---|---|---|---|
| dsv4p_nv | 10 | 51,577 | 66 | 14.4s |
| glm5_2_nv | 7 | 51,637 | 66 | 14.4s |

双tier NVCFPexecTimeout远低于UPSTREAM=66（buffer >14s），**非绑定**。均匀分布在所有key上——函数级非key级。

## Fallback 成功率

| 方向 | OK | total | SR |
|---|---|---|---|
| 双向合计 | 52 | 52 | 100% |

Fallback链路完美。52次fallback全部成功(status=200)。

## 函数健康度

日志快照（00:15 UTC，容器重启后11min）:
- dsv4p_nv func 74f02205: health=0.25→0.33（持续恢复，R796最后为0.25）
- glm5_2_nv func 3b9748d8: health=0.0→0.50→0.60→0.71（恢复中）
- kimi_nv func f966661c: 未出现

重启后MIN_SAMPLES保护窗口内，两函数均在tier_chain中双向可用。FALLBACK_HEALTH_THRESHOLD=0.10保障fallback不被误杀。

## Peer Fallback

日志确认peer fallback工作正常——HM1本地全部ATExhausted时成功发送到HM2，HM2返回200。但双端同NVCF后端，同时受surge影响时peer fallback无法交叉救回（R795/R796已记录此模式）。

## NOP Gates 全部通过

1. ✅ ATE全部double-tier (32/32 tiers_tried_count=2)
2. ✅ 零单tier ATE
3. ✅ NVCFPexecTimeout buffer ≥3s: dsv4p=14.4s, glm5_2=14.4s
4. ✅ 双向fallback活跃（DB确认两方向fallback_tiers_used）
5. ✅ Fallback 100% SR (52/52)
6. ✅ 全参数已floor最优

## 为什么NOP

SR 88.4%与R796的88.8%本质相同（-0.4pp在采样波动范围内）。核心问题仍是NVCF周期性上游surge:
- 20:00 UTC窗口: dsv4p 0% (单小时5req全部ATE)——与R795/R796窗口模式一致
- UPSTREAM=66 buffer 14.4s充裕，非绑定
- Fallback链路完美（52/52 100%）
- 所有参数floor值，无下调空间
- NVCFPexecTimeout max 51.6s << UPSTREAM 66s, 无压缩意义
- dsv4p_nv health恢复趋势向好(0.05→0.25→0.33)

**无参可改，无参需改。**

## NOP streak

R788 → R789 → R790 → R791 → R792 → R793 → R794 → R795 → R796 → **R797**: 连续10轮 NOP

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