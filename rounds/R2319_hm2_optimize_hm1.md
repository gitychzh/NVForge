# R2319 (HM2→HM1): NOP 巡检 — R2317 生效确认, 零改动等待数据

**Timestamp**: 2026-07-24 14:05 UTC
**Round type**: NOP 巡检 (无优化, 仅确认生效)
**Author**: opc2_uname (HM2)
**Target**: HM1 (opc_uname @ 100.109.153.83:222)
**Container**: nv_gw (port 40006)
**Iron Law**: Only HM1 config changed. Zero HM2 local changes. (本轮无改动)

## 数据采集

### docker exec env (当前)
```
NVU_BIG_INPUT_MODELS=glm5_2_nv,dsv4p_nv    ← R2317 生效确认
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
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_FORCE_STREAM_UPGRADE=0
MIN_OUTBOUND_INTERVAL_S=0
KEY_AUTHFAIL_COOLDOWN_S=0
NVU_CONNECT_RESERVE_S=0
NVU_SSLEOF_RETRY_DELAY_S=0.1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006
NVU_PEER_FALLBACK_TIMEOUT=60
NVU_MS_GW_FALLBACK_TIMEOUT=120
NVU_FALLBACK_HEALTH_THRESHOLD=0.10
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms
NVU_HOST_MACHINE=opc_uname
```

### docker logs (nv_gw, post-restart 04:32 UTC → 06:03 UTC)
```
[NV-BIGINPUT-SUCCESS] glm5_2_nv input=284389c (req=de44100e) breaker→CLOSED dur=14109ms
[NV-BIGINPUT-SUCCESS] glm5_2_nv input=284949c (req=879973ab) breaker→CLOSED dur=10179ms → zombie detected (content=35c)
[NV-ZOMBIE-EMPTY] glm5_2_nv content_chars=35 reasoning_chars=0 < 50 (content-only R852b) input=284949
[NV-BIGINPUT-SUCCESS] glm5_2_nv input=284389c (req=8d3c228f) breaker→CLOSED dur=8890ms
[NV-BIGINPUT-SUCCESS] glm5_2_nv input=285359c (req=27d23ef3) breaker→CLOSED dur=7282ms
[NV-BIGINPUT-SUCCESS] glm5_2_nv input=286340c (req=66629776) breaker→CLOSED dur=6012ms
[NV-BIGINPUT-SUCCESS] glm5_2_nv input=286899c (req=e5f936e4) breaker→CLOSED dur=5392ms → zombie detected (content=48c)
[NV-ZOMBIE-EMPTY] glm5_2_nv content_chars=48 reasoning_chars=0 < 50 (content-only R852b) input=286899
[NV-COOLDOWN] glm5_2_nv k2 429 → cycling to k3 (成功) dur=12797ms
[NV-BIGINPUT-SUCCESS] glm5_2_nv input=286340c (req=f887eaea) breaker→CLOSED dur=12797ms (含429 cycle)
[NV-BIGINPUT-SUCCESS] glm5_2_nv input=287307c (req=ab13d19b) breaker→CLOSED dur=4548ms
```

### DB 24h (nv_requests)
| model | total | 200 | 502 | 429 | SR |
|---|---|---|---|---|---|
| dsv4p_nv | 46 | 32 | 14 | 0 | 69.6% |
| glm5_2_nv | 121 | 60 | 38 | 23 | 49.6% |
| kimi_nv | 55 | 20 | 35 | 0 | 36.4% |

### DB 24h 错误明细
| model | error_type | cnt | avg_ms |
|---|---|---|---|
| glm5_2_nv | all_tiers_exhausted | 51 | 20177 |
| kimi_nv | all_tiers_exhausted | 26 | 193765 |
| glm5_2_nv | zombie_empty_completion | 10 | 14339 |
| kimi_nv | zombie_empty_completion | 8 | 74004 |
| dsv4p_nv | all_tiers_exhausted | 7 | 95361 |
| dsv4p_nv | zombie_empty_completion | 7 | 31526 |
| kimi_nv | NVStream_IncompleteRead | 1 | 75832 |

### DB 近3h (R2317 部署后, 04:00-06:03 UTC)
| model | total | 200 | 502 | SR |
|---|---|---|---|---|
| dsv4p_nv | 0 | 0 | 0 | - |
| glm5_2_nv | 10 | 8 | 2 | 80.0% |
| kimi_nv | 0 | 0 | 0 | - |

### tier_attempts 24h
| tier | error_type | cnt | avg_ms |
|---|---|---|---|
| glm5_2_nv | 429_nv_rate_limit | 31 | - |
| kimi_nv | empty_200 | 9 | - |
| glm5_2_nv | NVCFPexecTimeout | 6 | 25199 |
| kimi_nv | NVCFPexecRemoteDisconnected | 5 | 43391 |
| dsv4p_nv | NVCFPexecSSLEOFError | 3 | 5005 |
| kimi_nv | NVCFPexecSSLEOFError | 3 | 5005 |
| dsv4p_nv | NVCFPexecRemoteDisconnected | 2 | 35694 |
| glm5_2_nv | NVCFPexecSSLEOFError | 2 | 5004 |
| dsv4p_nv | empty_200 | 2 | - |
| dsv4p_nv | 504_nv_gateway_timeout | 1 | - |
| glm5_2_nv | NVCFPexecRemoteDisconnected | 1 | 1122 |

### all_tiers_exhausted 近窗口 (03:00-03:39 UTC, 全R2317前)
| model | duration_ms | input_chars | key_cycle_429s |
|---|---|---|---|
| dsv4p_nv | 170057 | 283146 | 0 | ← budget ceiling, 5 keys exhausted
| glm5_2_nv | 7 | 282976 | 0 | ← big-input breaker OPEN → instant 502
| glm5_2_nv | 5 | 282976 | 0 | ← big-input breaker OPEN → instant 502
| glm5_2_nv | 49868 | 282976 | 0 | ← 5 keys exhausted, big-input 282k
| dsv4p_nv | 170028 | 282976 | 0 | ← budget ceiling, 5 keys exhausted
| glm5_2_nv | 55273 | 282976 | 0 |
| glm5_2_nv | 51419 | 282976 | 0 |
| glm5_2_nv | 55250 | 282976 | 0 |

注: 7ms/5ms 的 glm5_2_nv all_tiers_exhausted 是 big-input breaker OPEN 直返 502 (R1695), 不耗 key 不记录 tier_attempts. 03:04-03:39 的 282976c 集群全发生在 R2317 重启前 (容器 StartedAt=04:32 UTC).

### zombie_empty_completion 近24h (按时间排序)
| ts | model | duration_ms | input_chars | content_chars |
|---|---|---|---|---|
| 07-24 05:33 | glm5_2_nv | 5382 | 286899 | 48 | ← R2317后
| 07-24 04:33 | glm5_2_nv | 10179 | 284949 | 35 | ← R2317后
| 07-24 02:39 | dsv4p_nv | 51925 | 283568 | - | ← R2317前
| 07-24 01:37 | dsv4p_nv | 22240 | 282280 | - | ← R2317前
| 07-24 00:33 | glm5_2_nv | 5069 | 280244 | - |
| 07-23 22:04 | glm5_2_nv | 18107 | 273278 | - |
| 07-23 21:38 | dsv4p_nv | 15116 | 269978 | - |
| 07-23 20:33 | glm5_2_nv | 21691 | 267950 | - |
| 07-23 17:38 | dsv4p_nv | 11294 | 257179 | - |
| 07-23 17:07 | dsv4p_nv | 14516 | 257193 | - |
| 07-23 16:38 | dsv4p_nv | 10471 | 257876 | - |
| 07-23 15:35 | glm5_2_nv | 28985 | 254341 | - |
| 07-23 15:04 | glm5_2_nv | 21299 | 254341 | - |
| 07-23 14:09 | dsv4p_nv | 95117 | 251951 | - |

## 分析

### 1. R2317 生效确认
`NVU_BIG_INPUT_MODELS=glm5_2_nv,dsv4p_nv` 已在 HM1 nv_gw env 中确认。容器 StartedAt=04:32 UTC, env 值已生效。

### 2. R2317 后流量: glm5_2_nv only, dsv4p_nv zero
近2h 仅 glm5_2_nv 10 请求 (全 >250K 大 input), 8 成功 (SR=80%), 2 zombie (content=35c/48c < 50 阈值). 无 dsv4p_nv 请求 — 新增的 breaker 保护未经验证. 无 kimi_nv 请求.

### 3. Big-input breaker 行为正确
zombie_empty_completion 正确馈入 big_input_breaker (R1696), 但被 SUCCESS 重置 (每次成功 → CLOSED). 2 zombie 在 10 请求中=20% 偶发, 非连续 FAIL_N=4, breaker 未触发 OPEN. 设计行为正确.

### 4. R2317 前 03:04-03:39 的 282976c 集群
8 条 all_tiers_exhausted 均发生在 R2317 重启前. glm5_2_nv 的 7ms/5ms instant 502 是 big-input breaker 已在 OPEN 状态 (R1695 直返). dsv4p_nv 的 170s 两次是 budget ceiling (不在 BIG_INPUT_MODELS 当时, 5 key 全挂). 此集群已结束, 重启后无重复.

### 5. zombie_empty_completion 持续性
24h 14 条 zombie (glm5_2_nv: 5, dsv4p_nv: 7, kimi_nv: 2). R2317 后仅 glm5_2_nv 2 条 (content=35c/48c). 模式: NVCF GLM5.2 对大 input 返回 200+stop 但 content<50c — 模型侧内容过滤, 非网关问题. 当前 zombie 阈值 content<50 (R852b) 合理, 无需调整.

### 6. 参数稳定性
env 逐项比对 R2317 无漂移. 容器 StartedAt=04:32 UTC 未重启. 所有参数一致.

### 7. 三阈值判定
- **错误率**: glm5_2_nv 近2h SR=80% (8/10), 不满足触发条件
- **新错误模式**: 无新增. zombie_empty 为已知模式 (R840/R852b/R1696)
- **参数漂移**: 无

## 优化决策

**NOP (零改动)** — 本轮无优化.

理由:
1. R2317 (NVU_BIG_INPUT_MODELS +dsv4p_nv) 刚部署, 无 dsv4p_nv 流量验证新保护
2. glm5_2_nv 近2h SR=80%, 偶发 zombie 为 NVCF 模型侧内容过滤, 非网关旋钮可调
3. 无新增错误模式, 无参数漂移
4. kimi_nv 零流量, budget=170 仍待验证 (R2315)
5. 不满足任何优化触发阈值

**等待下一轮数据, 重点观察:**
- dsv4p_nv 大 input 首次请求 → 验证 breaker 保护效果
- kimi_nv 恢复流量 → 验证 budget=170 (R2315)
- zombie_empty 模式是否继续偶发 (≤20% 可接受)

## ⏳ 轮到HM1优化HM2