# R801: HM2→HM1 — NOP (false trigger) — 86.0% SR, 零新提交, 全参数floor, 系统稳定

**时间**: 2026-07-07 05:30 UTC  
**分析窗口**: 6h (23:30–05:30 UTC)  
**决策**: NOP — 零参数变更，零容器重启，零compose修改  
**触发原因**: cron脚本误判R800的NOP提交(commit `8d1c6a4`:"这是我提交的, 不触发")为HM1新commit → actual NOP

## 全量数据

| 指标 | 值 | 判定 |
|---|---|---|
| **6h SR** | 265req/228OK (**86.0%**) | 稳定 (R800:86.1%→R801:86.0%, -0.1pp — 零波动) |
| **ATE** | 37 (14.0%), 全部 tiers_tried_count=2 | NVCF双tier真实耗尽 |
| **单tier ATE** | **0** | ✅ 完美 |
| **Fallback SR** | 43/43 **100%** | 双向完美 |
| **dsv4p_nv** | 92req/75OK (81.5%) | 良好 |
| **glm5_2_nv** | 172req/152OK (88.4%) | 优秀 |
| **kimi_nv** | 2req/2OK (100%) | 完全健康 |

## 成功请求延迟（6h）

| 模型 | avg TTFB | avg duration | p50 TTFB | p95 TTFB | max duration |
|---|---|---|---|---|---|
| dsv4p_nv | 71,982ms | 72,494ms | 56,507ms | 179,804ms | 202,504ms |
| glm5_2_nv | 34,220ms | 34,315ms | 12,941ms | 122,282ms | 211,291ms |
| kimi_nv | 0ms | 1,639ms | 0ms | 0ms | 2,066ms |

## ATE 详细

37 ATE全部 tiers_tried_count=2，零单tier ATE。avg 176,017ms，max 229,007ms。两方向均有fallback尝试但均耗尽——NVCF双tier真实不可用。

## NVCFPexecTimeout 分析

| Tier | 次数 | max(ms) | UPSTREAM=66 | buffer |
|---|---|---|---|---|
| dsv4p_nv | 17 | 51,577 | 66 | 14.4s |
| glm5_2_nv | 6 | 51,637 | 66 | 14.4s |

双tier NVCFPexecTimeout远低于UPSTREAM=66（buffer >14s），**非绑定**。均匀分布在所有key上——函数级非key级。

## Tier Attempts 错误分布（6h）

| Tier | 错误类型 | 次数 | max(ms) |
|---|---|---|---|
| glm5_2_nv | 504_nv_gateway_timeout | 35 | - |
| dsv4p_nv | 504_nv_gateway_timeout | 29 | - |
| dsv4p_nv | NVCFPexecTimeout | 17 | 51,577 |
| glm5_2_nv | empty_200 | 10 | - |
| dsv4p_nv | empty_200 | 7 | - |
| glm5_2_nv | NVCFPexecTimeout | 6 | 51,637 |
| dsv4p_nv | 500_nv_error | 1 | - |

504_gateway_timeout 主导 (64/105=61.0%), NVCFPexecTimeout 23/105=21.9%, empty_200 17/105=16.2%。全是NVCF上游问题。

## Fallback 成功率

| 方向 | OK | total | SR |
|---|---|---|---|
| dsv4p_nv→glm5_2_nv | 27 | 27 | 100% |
| glm5_2_nv→dsv4p_nv | 16 | 16 | 100% |
| **双向合计** | **43** | **43** | **100%** |

Fallback链路完美。43次fallback全部成功(status=200)。

## 日志关键事件（100行）

- `BrokenPipeError`: 2次 — 客户端断开连接无害事件
- `NV-THINKING-TIMEOUT`: 4次 glm5_2_nv stream=True → extended timeout 66s — 正常行为
- `NV-FALLBACK-SUCCESS`: 多次 dsv4p_nv→glm5_2_nv fallback成功
- `NV-TIER-FAIL`: 1次 [04:18] `429=0, empty200=0, timeout=1, other=1` → fallback成功
- `NV-TIER-FAIL`: 1次 [05:18] `429=0, empty200=1, timeout=0, other=0` → fallback成功
- FALLBACK_GRAPH 双向活跃: `['dsv4p_nv', 'glm5_2_nv']` ↔ `['glm5_2_nv', 'dsv4p_nv']`
- dsv4p_nv health 恢复趋势: 0.3 → 0.35 → 0.4 → 0.45 → 0.5 (5h窗口持续爬升)
- glm5_2_nv health: 0.9 (稳定)

## Peer Fallback

peer fallback工作正常。双端同NVCF后端，同时受surge影响时peer fallback无法交叉救回——与R795-R800模式一致。

## NOP 六门判定

| 门 | 检查 | 结果 |
|---|---|---|
| Gate 1: 全部双tier ATE | 37/37 tiers_tried_count=2 | ✅ |
| Gate 2: 零单tier ATE | 0 rows | ✅ |
| Gate 3: PexecTimeout buffer ≥3s | dsv4p 14.4s, glm5_2 14.4s | ✅ |
| Gate 4: FALLBACK_GRAPH双向活跃 | 双向 `dynamic fallback` | ✅ |
| Gate 5: Fallback SR 100% | 43/43 status=200 | ✅ |
| Gate 6: 全参数floor | FASTBREAK=1, EMPTY_200=1, CONNECT_RESERVE=0, MIN_OUTBOUND=0, INTEGRATE_COOLDOWN=0, FALLBACK_HEALTH=0.10, FORCE_STREAM_UPGRADE=0 | ✅ |

## 为什么NOP

SR 86.0%与R800的86.1%本质相同（0.1pp差异 = 零波动）。核心问题仍是NVCF周期性上游surge:
- UPSTREAM=66 buffer 14.4s充裕，非绑定
- Fallback链路完美（43/43 100% SR）
- 所有参数floor值，无下调空间
- NVCFPexecTimeout max 51.6s << UPSTREAM 66s，无压缩意义（NVCFPexecTimeout 仅为总错误的21.9%，主导是504_gateway_timeout 61.0%）
- FORCE_STREAM 66 ↔ UPSTREAM 66 aligned，零漂移
- 无单tier ATE — 所有fallback均被尝试
- dsv4p_nv health 恢复趋势（0.3→0.5）为正向信号

**无参可改，无参需改。** 触发为false positive（cron误判R800 NOP提交为HM1新commit）。

## 429 分布分析

| dsv4p_nv key | total 429s | glm5_2_nv key | total 429s |
|---|---|---|---|
| k0 | 11 | k0 | 18 |
| k1 | 8 | k1 | 5 |
| k2 | 19 | k2 | 5 |
| k3 | 12 | k3 | 14 |
| k4 | 7 | k4 | 6 |

dsv4p_nv k2偏高(19)但fallback SR=100% → 429-affected请求均被fallback救回。FASTBREAK=1已floor，429非瓶颈。

## 24h 错误全景

37 ATE (6h) + 7 ATE (前18h) = 44 ATE in 24h，全部 all_tiers_exhausted。

## NOP streak

R788 → R789 → R790 → R791 → R792 → R793 → R794 → R795 → R796 → R797 → R800 → **R801**: 连续12轮 NOP

## 触发数据回溯

```
From github.com:gitychzh/NVForge
 * branch            main       -> FETCH_HEAD
HEAD is now at 8d1c6a4 R800: HM2→HM1 — NOP (false trigger) — 86.2% SR, 零新提交, 全参数floor, 系统稳定
[2026-07-07 05:30:06] 这是我提交的, 不触发
```

cron脚本fetch到R800 NOP提交后判定"轮到HM2执行优化"。实际commit message `"这是我提交的, 不触发"` 为用户明确NOP标记 → 脚本误判。

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
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | aligned with UPSTREAM |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| KEY_COOLDOWN_S | 25 | standard |
| TIER_COOLDOWN_S | 25 | standard |

## ⏳ 轮到HM1优化HM2