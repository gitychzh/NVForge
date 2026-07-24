# R2320 (HM2→HM1): NOP 巡检 — 全部上游NVCF, 无config-tunable失败

**Timestamp**: 2026-07-24 15:03 UTC
**Round type**: NOP 巡检 (无优化, 仅确认生效)
**Author**: opc2_uname (HM2)
**Target**: HM1 (opc_uname @ 100.109.153.83:222)
**Container**: nv_gw (port 40006)
**Iron Law**: Only HM1 config changed. Zero HM2 local changes. (本轮无改动)

## 数据采集

### docker exec env (当前, 无漂移)
```
NVU_BIG_INPUT_MODELS=glm5_2_nv,dsv4p_nv
NVU_BIG_INPUT_FAIL_N=4
NVU_BIG_INPUT_COOLDOWN_S=900
NVU_BIG_INPUT_THRESHOLD=250000
NVU_TIER_BUDGET_DSV4P_NV=170
NVU_TIER_BUDGET_GLM5_2_NV=210
NVU_TIER_BUDGET_KIMI_NV=170
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
UPSTREAM_TIMEOUT=24
TIER_COOLDOWN_S=15
KEY_COOLDOWN_S=10
NVU_PEXEC_TIMEOUT_FASTBREAK=2
NVU_EMPTY_200_FASTBREAK=3
NVU_STREAM_FIRST_BYTE_DEADLINE_S=15
NVU_STREAM_TOTAL_DEADLINE_S=35
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
MIN_OUTBOUND_INTERVAL_S=0
NVU_PEER_FALLBACK_TIMEOUT=60
NVU_PEER_FALLBACK_ENABLED=1
NVU_MS_GW_FALLBACK_TIMEOUT=120
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms
NVU_HOST_MACHINE=opc_uname
```
StartedAt: 2026-07-24T04:32:02Z (R2317 deploy). Health: ok.

### DB 24h per-model
| model | total | ok | 429 | 502 | SR | avg_ok_ms | avg_err_ms |
|---|---|---|---|---|---|---|---|
| glm5_2_nv | 122 | 60 | 24 | 38 | 49.2% | 16449 | 18752 |
| kimi_nv | 55 | 20 | 0 | 35 | 36.4% | 42216 | 163021 |
| dsv4p_nv | 47 | 32 | 0 | 15 | 68.1% | 32390 | 70550 |

### DB 24h 错误明细
| model | error_type | cnt | avg_ms | max_ms |
|---|---|---|---|---|
| glm5_2_nv | all_tiers_exhausted | 54 | 19364 | 90939 |
| kimi_nv | all_tiers_exhausted | 26 | 193765 | 370299 |
| dsv4p_nv | all_tiers_exhausted | 8 | 104697 | 170057 |
| glm5_2_nv | zombie_empty_completion | 8 | 14624 | 28985 |
| kimi_nv | zombie_empty_completion | 8 | 74004 | 148541 |
| dsv4p_nv | zombie_empty_completion | 7 | 31526 | 95117 |
| kimi_nv | NVStream_IncompleteRead | 1 | 75832 | 75832 |

### DB post-R2317 (04:32-07:03 UTC, ~2.5h)
| model | total | ok | SR | avg_ok_ms | avg_err_ms |
|---|---|---|---|---|---|
| glm5_2_nv | 13 | 8 | 61.5% | 9437 | 6434 |
| dsv4p_nv | 1 | 0 | 0% | — | 170046 |
| kimi_nv | 0 | 0 | — | — | — |

### DB post-R2317 错误明细
| req_id | model | status | dur_ms | error_type | input_c | note |
|---|---|---|---|---|---|---|
| 879973ab | glm5_2_nv | 502 | 10179 | zombie_empty | 284949 | NVCF content filter, 35c |
| e5f936e4 | glm5_2_nv | 502 | 5382 | zombie_empty | 286899 | NVCF content filter, 48c |
| c0347d3d | glm5_2_nv | 429 | 16591 | all_tiers_exhausted | 288285 | 429 storm, all 5 keys 429 |
| 874ba308 | glm5_2_nv | 502 | 12 | all_tiers_exhausted | 288285 | cooldown fast-fail |
| 11aeddd3 | glm5_2_nv | 502 | 7 | all_tiers_exhausted | 288285 | cooldown fast-fail |
| 330b35a1 | dsv4p_nv | 502 | 170046 | all_tiers_exhausted | 288285 | budget-cut at 170s |

### docker logs (完整, 04:32-07:03 UTC)

**dsv4p_nv ATE 330b35a1 详细时序:**
```
14:35:58.6 k5 → NVCF pexec
14:37:00.2 k5 empty_200, Content-Length:0 (stream) → 61.6s
14:37:00.2 k1 → NVCF pexec
14:38:02.2 k1 empty_200, Content-Length:0 (stream) → 62.0s
14:38:02.3 k2 → NVCF pexec
14:38:48.6 k2 NVCF pexec timeout: attempt=46356ms total=170035ms
14:38:48.6 TIER-BUDGET: budget 170.0s exceeded after 170.0s, breaking
14:38:48.6 TIER-FAIL: 429=0, empty200=2, timeout=1, other=0, elapsed=170036ms
14:38:48.6 PEER-FB: dsv4p_nv in skip list → immediate 502
```
→ 仅尝试3/5 keys。k5+k1 empty_200共消耗123.6s (62s/次)。k2 timeout在46s时被budget截断。k3+k4未尝试。

**glm5_2_nv 429风暴 (06:33 UTC):**
```
14:33:20.7 k4 → 429 (1.5s), k5 → 429 (3.4s), k1 → 429 (3.2s), k2 → 429 (4.3s), k3 → 429 (1.9s), k4 → 429 (0.9s), k5 → 429 (1.4s)
14:33:37.3 TIER-FAIL: all 5 keys 429=7, elapsed=16587ms
14:33:42.4 TIER-ALL-COOLDOWN → 12ms fast-fail (cooldown)
14:33:43.5 TIER-ALL-COOLDOWN → 7ms fast-fail (cooldown)
```
→ 429风暴~2h周期(04:33, 06:33 UTC), R2314确认的稳定模式。

**glm5_2_nv 成功请求 (07:03 UTC):**
```
15:03:20.9 k5 NVCF pexec → 7832ms, input=288372c, breaker→CLOSED
15:03:29.6 k1 → 429 (2.4s), k2 → 429 (5.9s), k3 → 14025ms, input=289351c, breaker→CLOSED
```
→ 2/2成功, 1个429 cycle后k3成功。breaker CLOSED (success重置)。

## 失败根因分析

### 1. zombie_empty (glm5_2_nv, 2 events)
- **879973ab**: content_chars=35 < 50, input=284949c
- **e5f936e4**: content_chars=48 < 50, input=286899c
- **根因**: NVCF模型侧内容过滤, 返回空completion。非网关旋钮。
- **设计行为**: 检测到zombie→发送content_filter error SSE chunk→cc4101 zombie→api_error→CC retry。
- **不可调**: 不是timeout, 不是breaker, 不是fastbreak。NVCF server-side行为。

### 2. 429风暴 (glm5_2_nv, 1 event → 3 DB entries)
- **c0347d3d**: 5 keys × 7次429 = 16591ms, all_429=true
- **874ba308/11aeddd3**: post-storm cooldown fast-fail (12ms, 7ms)
- **根因**: NVCF cluster-level rate-limit, 所有5 keys同时429。
- **周期**: ~2h (04:33, 06:33 UTC), R2314-R2319确认的稳定pattern。
- **不可调**: NVCF账户配额, 非网关旋钮。TIER_COOLDOWN=15, KEY_COOLDOWN=10已是R2297最优值。peer-fb skip正确(glm5_2_nv在SKIP_MODELS中), 429=7检出后立即ABORT-NO-FALLBACK。

### 3. dsv4p_nv empty_200 → budget-cut (1 event)
- **330b35a1**: k5 empty_200 61.6s, k1 empty_200 62.0s, k2 timeout 46.4s→budget-cut
- **根因**: NVCF server返回空200 (Content-Length:0), 但stream保��open。网关等待stream结束(~62s/次)。
- **EMPTY_200_FASTBREAK=3**: 需要3次连续empty_200才fastbreak。3×62=186s > 170s budget → 不可达。仅2次empty_200时budget先耗尽。
- **FASTBREAK=2分析**: 2×62=124s < 170s budget, 理论上可fastbreak。但FASTBREAK是全局参数, R2303专门为kimi_nv提升到3 (kimi 8 ATE @ 124-126s浪费5个未试keys)。降回2会伤害kimi_nv。
- **不可调**: empty_200是NVCF server-side。62s/次是stream timeout行为(NVCF SSE keepalive)。FASTBREAK=3对kimi_nv是正确值。降低会引入kimi_nv false fastbreak风险。

### 4. kimi_nv: 零流量
- Post-R2317 0 req。R2316 R2318 R2319同模式。
- `NVU_TIER_BUDGET_KIMI_NV=170` (R2314: 130→170) 完全未测试。
- 等待流量验证。

## 三阈值判断

| 阈值 | 状态 | 详情 |
|---|---|---|
| 参数误杀 | 0 | 无配置错误导致的行为 |
| 错误数 | 5 post-R2317 | 全部上游NVCF, 无可调项 |
| SR退化 | 低流量 | glm5_2_nv 61.5% (13req), 与R2319 80% (10req) 在统计误差范围内 |

**三阈值全不满足 → 冻结。**

## 参数漂移检查

compose vs env: 无漂移。所有key参数一致。

## 决策: NOP

全部5个失败(event-level)均为上游NVCF问题:
- zombie_empty: NVCF模型侧内容过滤
- 429风暴: NVCF cluster-level rate-limit (~2h周期)
- cooldown fast-fail: 429风暴后正确设计行为
- dsv4p_nv empty_200: NVCF server空响应, FASTBREAK=3对kimi_nv正确, 不可降低

0个config-tunable失败。继续R2317后稳定化。

## 优化前后对比

| 指标 | R2317前 (24h) | R2317后 (2.5h) |
|---|---|---|
| glm5_2_nv SR | 49.2% | 61.5% (↑) |
| dsv4p_nv ATE avg | 104697ms | 170046ms (1 event, budget-cut) |
| 429风暴周期 | unknown | ~2h (确认) |
| kimi_nv traffic | 55/24h | 0 (零流量) |
| BIG_INPUT breaker | pre-R2317 无dsv4p_nv保护 | CLOSED, 正确保护 |
| 参数漂移 | — | 0 |

## ⏳ 轮到HM1优化HM2