# HM2 Optimize HM1 — Round R954

> **2026-07-09 10:30 UTC** | Author: HM2 (opc2_uname) | Target: HM1 (opc_uname, 100.109.153.83)
> **Trigger**: False trigger (cron mis-dispatch). Script output: "这是我提交的, 不触发"
> **Iron Rule**: 只改HM1不改HM2

## 1. 触发分析

```
cron 脚本输出: "这是我提交的, 不触发"
最新 commit: 79773c2 (R953: HM2→HM1 — NOP, 70th consecutive)
作者: opc2_uname (HM2) — 自提交，非 HM1 触发
判定: FALSE TRIGGER — 71st consecutive false-trigger dispatch (R884→R954)
HM1 本地 git log 仍停留在 R821 (133 轮落后) — 未提交任何新内容
```

## 2. HM1 数据收集 (改前必有数据)

### 2.1 容器状态
| 容器 | 状态 | Uptime |
|------|------|--------|
| nv_gw | Up (healthy) | 6 hours |
| ms_gw | Up (healthy) | 11 hours |
| logs_db | Up (healthy) | 4 days |

### 2.2 docker logs nv_gw (最近100行)
```
(no error/warn found) — 零错误
tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback)
One fallback event: glm5_2_nv k4→504 timeout, k5→NVCFPexecTimeout (113s), 
fast-break→dsv4p_nv k5→success (NV-FALLBACK-SUCCESS). Normal NVCF transient.
All other requests: first-attempt success on glm5_2_nv.
```

### 2.3 nv_gw 运行时环境 (关键参数)
```
UPSTREAM_TIMEOUT=64
TIER_TIMEOUT_BUDGET_S=114
MIN_OUTBOUND_INTERVAL_S=0
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=3
NVU_PEER_FALLBACK_TIMEOUT=45
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=64
NVU_FORCE_STREAM_UPGRADE=0
NVU_CONNECT_RESERVE_S=0
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=25
KEY_AUTHFAIL_COOLDOWN_S=60
FALLBACK_HEALTH_THRESHOLD=0.05
NV_INTEGRATE_KEY_COOLDOWN_S=0
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
```

### 2.4 Compose vs Env 漂移检查
所有参数 compose 与 env 一致，零漂移。

### 2.5 DB: nv_requests 6h aggregate
| 指标 | 值 |
|------|----|
| Total | 34 |
| OK (200) | 34 (100.0% SR) |
| Fail | 0 |
| ATE | 0 |
| avg latency (OK) | 18,263ms |
| max latency (OK) | 143,949ms |
| avg TTFB (OK) | 18,263ms |

### 2.6 DB: nv_requests per-model 6h
| model | total | ok | fail | avg_lat | max_lat |
|-------|-------|-----|------|---------|---------|
| glm5_2_nv | 34 | 34 (100%) | 0 | 18,263ms | 143,949ms |

dsv4p_nv: 0 req (无流量). kimi_nv: 0 req (无流量).

### 2.7 DB: upstream_type 6h
| upstream_type | total | ok | fail |
|---------------|-------|-----|------|
| nvcf_pexec | 34 | 34 | 0 |

### 2.8 DB: nv_requests 24h ATE
| 指标 | 值 |
|------|----|
| 24h ATE count | 1 |
| error_type | all_tiers_exhausted |
| last_ate_ts | 2026-07-08 13:21 UTC |

NVCF upstream transient — not config-fixable. Same pattern as previous rounds.

### 2.9 DB: nv_tier_attempts 6h (仅失败尝试)
| tier | error_type | cnt |
|------|-----------|-----|
| glm5_2_nv | 504_nv_gateway_timeout | 1 |
| glm5_2_nv | NVCFPexecTimeout | 1 |
| glm5_2_nv | empty_200 | 1 |

3 failed key attempts, 2 cycled to success (empty_200→k4, 504→k5→timeout), 1 fallback to dsv4p_nv.

### 2.10 DB: ms_requests 6h
| total | ok | fail |
|-------|-----|------|
| 0 | 0 | 0 |

ms_gw 零流量，零错误。

### 2.11 ms_gw 运行时环境
```
EMPTY_200_FASTBREAK_THRESHOLD=3 (R900 floor)
PROXY_TIMEOUT=600
KEY_COOLDOWN_S=60
VARIANT_COOLDOWN_S=30
UPSTREAM_TIMEOUT=300
ALL_EXHAUSTED_COOLDOWN_S=30
```

### 2.12 DB: 最近10条 nv_requests
```
2026-07-09 02:03:21 | glm5_2_nv | 200 | 143,949ms | nvcf_pexec
2026-07-09 01:35:08 | glm5_2_nv | 200 | 113,315ms | nvcf_pexec
2026-07-09 01:34:19 | glm5_2_nv | 200 |  48,383ms | nvcf_pexec
2026-07-09 01:33:21 | glm5_2_nv | 200 |  54,813ms | nvcf_pexec
2026-07-09 01:04:02 | glm5_2_nv | 200 |  24,785ms | nvcf_pexec
2026-07-09 01:03:40 | glm5_2_nv | 200 |  21,272ms | nvcf_pexec
2026-07-09 01:03:37 | glm5_2_nv | 200 |   2,991ms | nvcf_pexec
2026-07-09 01:03:21 | glm5_2_nv | 200 |  12,351ms | nvcf_pexec
2026-07-09 00:33:43 | glm5_2_nv | 200 |   2,678ms | nvcf_pexec
2026-07-09 00:33:30 | glm5_2_nv | 200 |  12,075ms | nvcf_pexec
(all 200 OK, zero failures)
```

## 3. 候选参数评估

| 参数 | 当前值 | floor | 评估 | 决策 |
|------|--------|-------|------|------|
| UPSTREAM_TIMEOUT | 64 | ~25s | 零 ATE，glm5_2_nv max=143,949ms 走 fallback 成功 | 不变 |
| TIER_TIMEOUT_BUDGET_S | 114 | — | 100% SR 零 ATE | 不变 |
| MIN_OUTBOUND_INTERVAL_S | 0 | 0 | 已达 floor | 不变 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | 1 | 已达 floor | 不变 |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | 25 | 零 ATE | 不变 |
| NVU_EMPTY_200_FASTBREAK | 3 | 1 | R829 止血设置，零错误期稳定 | 不变 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 64 | — | 与 UPSTREAM=64 对齐，零漂移 | 不变 |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | 0.0 | 安全地板，零误杀 | 不变 |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | — | 防御性参数，零 auth-fail | 不变 |
| TIER_COOLDOWN_S | 25 | — | KEY=TIER=25 对齐，零 429 | 不变 |
| NVU_CONNECT_RESERVE_S | 0 | 0 | 已达 floor | 不变 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | 0 | 已达 floor | 不变 |
| ms_gw EMPTY_200_FASTBREAK_THRESHOLD | 3 | 1 | R900 floor，零流量 | 不变 |

## 4. 决策: NOP

**所有参数已达最优值或 floor。6h 100% SR (34/34)，零错误，零 ATE，零漂移。**

- nv_gw: 100% SR, 零 error, 零 ATE (6h window)
- ms_gw: 0 req (零流量), 零 error
- 24h 仅 1 次 ATE (NVCF upstream transient, not config-fixable)
- 所有参数 compose ↔ env 一致，零漂移
- 71st consecutive false-trigger dispatch (R884→R954)
- 无任何优化空间 — 等待 NVCF function 健康度变化或流量模式变化信号

## 5. 参数变更: 无

零参数变更。本轮纯 NOP。

## ⏳ 轮到HM1优化HM2