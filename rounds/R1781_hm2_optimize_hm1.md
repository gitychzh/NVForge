# R1781: HM2→HM1 — NOP (100% SR零故障, 全参数 floor/optimal, false trigger)

**时间**: 2026-07-18 16:30 UTC
**触发**: HM1 commit `这是我提交的, 不触发` (false trigger — R1780 already NOP, same regime)
**作者**: opc2_uname (HM2)

## 数据收集

### 6h DB (nv_requests, ~10:00-16:30 UTC)
```
total | ok | fail | avg_ok_ms | max_ok_ms | total_kc429 | req_with_429
    24 | 24 |    0 |    8631.8 |     19968 |          25 |           24
```

### 1h DB (nv_requests)
```
total | ok | fail | avg_ok_ms
     4 |  4 |    0 |    8301.0
```

### per-model 6h
```
mapped_model | cnt | ok | fail | avg_ms | max_ms
glm5_2_nv    |  24 | 24 |    0 | 8631.8 |  19968
```

### 6h 错误
```
error_type | error_subcategory | cnt
-----------+-------------------+-----
(0 rows)
```

### upstream_type 6h
```
upstream_type | cnt | ok | fail
nvcf_pexec    |  24 | 24 |    0
```

### fallback 6h
```
peer_fb | tried_fb | ms_fb
      0 |        1 |     0
```

### zombie 6h
```
zombie | avg_ms
     0 |
```

### 最近10条请求
```
created_at           | mapped_model | status | error_type | duration_ms | upstream_type | nv_key_idx
2026-07-18 08:03:35  | glm5_2_nv    |    200 |            |        5980 | nvcf_pexec    |          4
2026-07-18 08:03:28  | glm5_2_nv    |    200 |            |        8004 | nvcf_pexec    |          3
2026-07-18 07:33:40  | glm5_2_nv    |    200 |            |        5903 | nvcf_pexec    |          2
2026-07-18 07:33:33  | glm5_2_nv    |    200 |            |       13317 | nvcf_pexec    |          1
2026-07-18 07:03:37  | glm5_2_nv    |    200 |            |        8737 | nvcf_pexec    |          0
2026-07-18 07:03:27  | glm5_2_nv    |    200 |            |        7305 | nvcf_pexec    |          4
2026-07-18 06:33:48  | glm5_2_nv    |    200 |            |        8670 | nvcf_pexec    |          3
2026-07-18 06:33:39  | glm5_2_nv    |    200 |            |       18918 | nvcf_pexec    |          2
2026-07-18 06:03:35  | glm5_2_nv    |    200 |            |        6002 | nvcf_pexec    |          1
2026-07-18 06:03:28  | glm5_2_nv    |    200 |            |        7825 | nvcf_pexec    |          0
```

### 日志 (docker logs nv_gw --tail 100)
```
(no error/warn found)
```

### 容器状态 (docker exec nv_gw env)
```
UPSTREAM_TIMEOUT=55
TIER_TIMEOUT_BUDGET_S=195
KEY_COOLDOWN_S=65
TIER_COOLDOWN_S=65
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=1
NVU_TIER_BUDGET_GLM5_2_NV=120
NVU_TIER_BUDGET_DSV4P_NV=60
NVU_PEER_FALLBACK_TIMEOUT=122
NVU_MS_GW_FALLBACK_TIMEOUT=120
NV_INTEGRATE_KEY_COOLDOWN_S=0
NV_INTEGRATE_MODELS="" (空)
NV_GLM52_MODE_CHAIN=pexec_us_rr
MIN_OUTBOUND_INTERVAL_S=0
NVU_CONNECT_RESERVE_S=0
NVU_SSLEOF_RETRY_DELAY_S=0.5
NVU_STREAM_FIRST_BYTE_DEADLINE_S=17
NVU_STREAM_TOTAL_DEADLINE_S=25
NVU_BIG_INPUT_FAIL_N=1
NVU_BIG_INPUT_COOLDOWN_S=7200
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
```
StartedAt: 2026-07-18T01:59:44Z (R1745 deploy, 未变)

### 容器漂移检测
- 所有参数 compose ↔ container env 一致: **零漂移** ✓

## 分析

### 1. 6h 100% SR — 与 R1780 完全一致
- 24/24 OK, 零错误, 零 fallback, 零 ATE, 零 zombie
- glm5_2_nv pexec_us_rr mode, 全部 first-key success
- avg=8632ms, max=19968ms << UPSTREAM=55s (buffer=35s, 充足)
- 日志干净: 零 ERROR/WARN

### 2. 数据与 R1780 几乎完全相同
- R1780: 24/24 100% SR, avg=8632ms, max=19968ms
- R1781: 24/24 100% SR, avg=8631.8ms, max=19968ms
- 同一 regime, 无新请求增量 (thin traffic, ~4 req/h)

### 3. 所有参数 floor/optimal
- FASTBREAK=1 (floor), EMPTY_200_FASTBREAK=1 (floor)
- MIN_OUTBOUND=0 (floor), CONNECT_RESERVE=0 (floor)
- NV_INTEGRATE_KEY_COOLDOWN=0 (floor), SSLEOF_RETRY=0.5 (floor)
- BIG_INPUT_FAIL_N=1 (floor), INTEGRATE_TIMEOUT_FASTBREAK=1 (floor)
- STREAM_FIRST_BYTE=17, STREAM_TOTAL=25 (optimal, p99 TTFB=10.8s << 17s)
- 无进一步优化空间

### 4. zero drift
- 容器 StartedAt 未变 (R1745 deploy), compose env 与 running env 100% 一致

## 决策: NOP (零变更)

**理由**: 6h 零错误 100% SR, 与 R1780 同一 regime。所有参数 floor/optimal, 零漂移。零可配置修复故障。铁律:只改HM1不改HM2。

## ⏳ 轮到HM1优化HM2
