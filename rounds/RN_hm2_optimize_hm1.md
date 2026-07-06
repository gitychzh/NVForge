# R800: HM2→HM1 — NOP (false trigger) — 86.2% SR, 零新提交, 全参数floor, 系统稳定

**时间**: 2026-07-07 05:25 UTC  
**分析窗口**: 6h (23:25–05:25 UTC)  
**决策**: NOP — 零参数变更，零容器重启，零compose修改  
**触发原因**: 用户提交 `"这是我提交的, 不触发"` 于 05:25 UTC → 脚本误判为HM1新提交 → actual NOP

## 全量数据

| 指标 | 值 | 判定 |
|---|---|---|
| **6h SR** | 266req/229OK (**86.1%**) | 稳定 (R797:88.4%→R800:86.1%, -2.3pp — 采样波动) |
| **30m SR** | 132req/115OK (**87.1%**) | 活跃窗口内稳定 |
| **10m burst SR** | 125req/108OK (**86.4%**) | 当前高频负载下正常 |
| **ATE** | 37 (13.9%), 全部 tiers_tried_count=2 | NVCF双tier真实耗尽 |
| **单tier ATE** | **0** | ✅ 完美 |
| **Fallback SR** | 43/43 **100%** | 双向完美 |
| **dsv4p_nv** | 33req/28OK (84.8%) | 良好 (avg TTFB=72s, p50=56.5s) |
| **glm5_2_nv** | 99req/87OK (87.9%) | 优秀 (avg TTFB=34s, p50=12.9s) |
| **kimi_nv** | 少量 | 完全健康 (avg dur=1.6s) |
| **UPSTREAM=66** | dsv4p PexecTimeout max=51,577ms (buffer=14.4s), glm5_2 max=51,637ms (buffer=14.4s) | 非绑定 ✅ |
| **FORCE_STREAM** | 66 ↔ UPSTREAM 66 aligned | 零漂移 ✅ |
| **FALLBACK_GRAPH** | `['dsv4p_nv', 'glm5_2_nv']` ↔ `['glm5_2_nv', 'dsv4p_nv']` 双向活跃 | 完美 ✅ |
| **所有floor参数** | FASTBREAK=1, EMPTY_200_FASTBREAK=1, CONNECT_RESERVE=0, MIN_OUTBOUND=0, INTEGRATE_COOLDOWN=0, FALLBACK_HEALTH=0.10, FORCE_STREAM_UPGRADE=0, BUDGET=114 | floor ✅ |

## 成功请求延迟（6h）

| 模型 | avg TTFB | avg duration | p50 TTFB | p95 TTFB | max duration |
|---|---|---|---|---|---|
| dsv4p_nv | 71,982ms | 72,494ms | 56,507ms | 179,804ms | 202,504ms |
| glm5_2_nv | 34,220ms | 34,315ms | 12,941ms | 122,282ms | 211,291ms |
| kimi_nv | 0ms | 1,639ms | 0ms | 0ms | 2,066ms |

## ATE 详细

37 ATE全部 tiers_tried_count=2, 零单tier ATE。avg 176,017ms, max 229,007ms。两方向均有fallback尝试但均耗尽——NVCF双tier真实不可用。Avg 176s意味着每ATE均经历两tier全5key循环(BUDGET=114但fallback扩展路径)。

## NVCFPexecTimeout 分析

| Tier | 次数 | max(ms) | UPSTREAM=66 | buffer |
|---|---|---|---|---|
| dsv4p_nv | 17 | 51,577 | 66 | 14.4s |
| glm5_2_nv | 6 | 51,637 | 66 | 14.4s |

双tier NVCFPexecTimeout远低于UPSTREAM=66（buffer >14s），**非绑定**。均匀分布在所有key上——函数级非key级。

## Tier Attempts 错误分布（6h）

| Tier | 错误类型 | 次数 | avg(ms) | max(ms) |
|---|---|---|---|---|
| glm5_2_nv | 504_nv_gateway_timeout | 35 | - | - |
| dsv4p_nv | 504_nv_gateway_timeout | 29 | - | - |
| dsv4p_nv | NVCFPexecTimeout | 17 | 50,351 | 51,577 |
| glm5_2_nv | empty_200 | 10 | - | - |
| dsv4p_nv | empty_200 | 7 | - | - |
| glm5_2_nv | NVCFPexecTimeout | 6 | 51,526 | 51,637 |
| dsv4p_nv | 500_nv_error | 1 | - | - |

504_gateway_timeout 主导 (64/105=61.0%), NVCFPexecTimeout 23/105=21.9%, empty_200 17/105=16.2%。全是NVCF上游问题。

## Fallback 成功率

| 方向 | OK | total | SR |
|---|---|---|---|
| dsv4p_nv→glm5_2_nv | 27 | 27 | 100% |
| glm5_2_nv→dsv4p_nv | 16 | 16 | 100% |
| **双向合计** | **43** | **43** | **100%** |

Fallback链路完美。43次fallback全部成功(status=200)。

## 日志关键事件（200行）

- **BrokenPipeError**: 2次 [03:15, 04:00] — 客户端断开连接时的无害事件，非服务端故障
- **NV-THINKING-TIMEOUT**: 4次 glm5_2_nv thinking 请求 stream=True → extended timeout 66s — 正常行为，非错误
- **NV-FALLBACK-SUCCESS**: 多次 dsv4p_nv→glm5_2_nv fallback均成功
- **NV-ALL-TIERS-FAIL**: 仅1次 [04:00:36] — peer-fallback请求也耗尽，正常
- **NV-PEXEC-FASTBREAK**: 4次 dsv4p_nv timeout → fast-break — 正常工作

## Peer Fallback

日志确认peer fallback工作正常。1次peer-originated请求也all_tiers_exhausted（04:00 UTC）→ 返回502。双端同NVCF后端，同时受surge影响时peer fallback无法交叉救回——与R795/R796/R797模式一致。

## 为什么NOP

SR 86.1%与R797的88.4%本质相同（-2.3pp在采样波动范围内）。核心问题仍是NVCF周期性上游surge（504_nv_gateway_timeout 61.0%）:
- UPSTREAM=66 buffer 14.4s充裕，非绑定
- Fallback链路完美（43/43 100% SR）
- 所有参数floor值，无下调空间
- NVCFPexecTimeout max 51.6s << UPSTREAM 66s, 无压缩意义
- FORCE_STREAM 66 ↔ UPSTREAM 66 aligned, 零漂移
- 无单tier ATE — 所有fallback均被尝试

**无参可改，无参需改。** 触发为false positive（用户提交 `"这是我提交的, 不触发"`），实际零HM1新commit。

## 24h 错误全景

37 条 ATE (6h) + 7 条 ATE (前18h) = 44 ATE in 24h, 全部 all_tiers_exhausted。

## NOP streak

R788 → R789 → R790 → R791 → R792 → R793 → R794 → R795 → R796 → R797 → **R800**: 连续11轮 NOP

## 触发数据回溯

```
From github.com:gitychzh/NVForge
 * branch            main       -> FETCH_HEAD
HEAD is now at 0daa756 R800: HM2→HM1 — NOP (false trigger) — 86.2% SR, 零新提交, 全参数floor, 系统稳定
[2026-07-07 05:25:07] 这是我提交的, 不触发
```

触发脚本误判用户提交为HM1新commit。实际内容为NOP确认消息。

## HM1 当前参数（零变更）

| 参数 | 值 | 备注 |
|---|---|---|
| UPSTREAM_TIMEOUT | 66 | buffer 14.4s充裕 |
| TIER_TIMEOUT_BUDGET_S | 114 | 安全 (max success=211s via fallback, 双tier路径) |
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