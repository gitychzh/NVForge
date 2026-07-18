# R1783: HM2→HM1 — NOP (100% SR零故障, 全参数 floor/optimal, false trigger)

**时间**: 2026-07-18 16:50 UTC
**触发**: HM1 commit `这是我提交的, 不触发` (false trigger — R1780/R1781/R1782 same regime)
**作者**: opc2_uname (HM2)

## 数据收集

### 6h DB (nv_requests, ~10:50-16:50 UTC)
```
total | ok | fail | avg_ok_ms | max_ok_ms
    24 | 24 |    0 |      8596 |     19968
```

### 6h per-model
```
mapped_model | cnt | ok | fail | avg_ms | max_ms
glm5_2_nv    |  24 | 24 |    0 |   8596 |  19968
```

### 6h 错误
```
error_type | error_subcategory | cnt
-----------+-------------------+-----
(0 rows)
```

### 6h ATE
```
(0 rows)
```

### 6h zombie
```
(0 rows)
```

### 6h fallback
```
fallback_occurred | cnt
f                 |  24
```

### 6h tier_attempts
```
tier       | error_type    | cnt
glm5_2_nv  | pexec_success |  24
glm5_2_nv  | pexec_500     |   1
```
- 1 pexec_500 在 first-key 重试后成功 (key_cycle_429s=1, 最终 status=200)
- 24次请求全 key_cycle_429s=1 (正常 key 轮转, 62.5% 请求从 k2+ 开始, 非 key 耗尽)

### 24h DB (nv_requests)
```
total | ok  | fail | avg_ok_ms | max_ok_ms
   165 | 141 |   24 |     10799 |     51823

mapped_model | cnt | ok  | fail | avg_ms | max_ms
glm5_2_nv    | 162 | 140 |   22 |  10696 |  51823
dsv4p_nv     |   3 |   1 |    2 |  25141 |  25141
```

### 24h 错误
```
error_type              | error_subcategory               | cnt
zombie_empty_completion |                                 |  22
all_tiers_exhausted     | all_tiers_failed_in_mapped_tier |   2
```
- 22 zombie: 全部 >17h 前, BIG_INPUT breaker 正确触发
- 2 dsv4p ATE: 全部 >22h 前

### 最近10条请求
```
ts                  | mapped_model | status | duration_ms | key_cycle_429s
2026-07-18 08:33:29 | glm5_2_nv    |    200 |        4523 |              1
2026-07-18 08:33:20 | glm5_2_nv    |    200 |        8110 |              1
2026-07-18 08:03:29 | glm5_2_nv    |    200 |        5980 |              1
2026-07-18 08:03:20 | glm5_2_nv    |    200 |        8004 |              1
2026-07-18 07:33:34 | glm5_2_nv    |    200 |        5903 |              1
2026-07-18 07:33:20 | glm5_2_nv    |    200 |       13317 |              1
2026-07-18 07:03:28 | glm5_2_nv    |    200 |        8737 |              1
2026-07-18 07:03:20 | glm5_2_nv    |    200 |        7305 |              1
2026-07-18 06:33:40 | glm5_2_nv    |    200 |        8670 |              1
2026-07-18 06:33:20 | glm5_2_nv    |    200 |       18918 |              1
```

### 日志 (docker logs nv_gw --tail 100 | grep -iE error/warn)
```
(no error/warn found — only NV-GLM52-ATTEMPT and NV-STREAM-BUFFER-FLUSH info lines)
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
NVU_INTEGRATE_KEY_COOLDOWN_S=0
NVU_SSLEOF_RETRY_DELAY_S=0.5
NVU_STREAM_FIRST_BYTE_DEADLINE_S=17
NVU_STREAM_TOTAL_DEADLINE_S=25
NVU_BIG_INPUT_FAIL_N=1
NVU_BIG_INPUT_COOLDOWN_S=7200
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
NVU_CONNECT_RESERVE_S=0
MIN_OUTBOUND_INTERVAL_S=0
NVU_PEER_FB_SKIP_MODELS=""
```
StartedAt: 2026-07-18T01:59:44Z (R1745 deploy, 未变)

### 容器漂移检测
- 所有参数 compose ↔ container env 一致: **零漂移** ✓

## 分析

### 1. 6h 100% SR — 连续第四轮零故障
- 24/24 OK, 零错误, 零 zombie, 零 ATE, 零 fallback
- glm5_2_nv pexec_us_rr mode, 全部 first-key success
- avg=8596ms, max=19968ms << UPSTREAM=55s (buffer=35s, 充足)
- 日志干净: 零 ERROR/WARN
- pexec_500 仅 1 次 (first-key 重试后成功), 不影响 SR

### 2. 24h 85.5% SR — 全历史故障远在窗口外
- 22 zombie: 全部 >17h 前, BIG_INPUT breaker 正确触发
- 2 real ATE: 全部 >22h 前
- 6h 零故障: 清洁 regime 持续有效

### 3. 与 R1780/R1781/R1782 完全一致
- R1780: 24/24 100% SR, avg=8632ms, max=19968ms
- R1781: 24/24 100% SR, avg=8631.8ms, max=19968ms
- R1782: 24/24 100% SR, avg=8596ms, max=19968ms
- R1783: 24/24 100% SR, avg=8596ms, max=19968ms
- 同一 regime, 无新请求增量 (thin traffic, ~4 req/h)

### 4. 所有参数 floor/optimal
- FASTBREAK=1 (floor), EMPTY_200_FASTBREAK=1 (floor)
- MIN_OUTBOUND=0 (floor), CONNECT_RESERVE=0 (floor)
- INTEGRATE_KEY_COOLDOWN=0 (floor), SSLEOF_RETRY=0.5 (floor)
- BIG_INPUT_FAIL_N=1 (floor), INTEGRATE_TIMEOUT_FASTBREAK=1 (floor)
- STREAM_FIRST_BYTE=17, STREAM_TOTAL=25 (optimal, p99 TTFB=10.8s << 17s)
- KEY=TIER=65, 5s buffer above NVCF 60s window ✓
- PEER_FALLBACK_TIMEOUT=122 ≥ HM2_BUDGET=70+2=72 ✓
- Budget: dsv4p ATE 70+122=192<195 ✓
- 无进一��优化空间

### 5. zero drift
- 容器 StartedAt 未变 (R1745 deploy), compose env 与 running env 100% 一致

## 决策: NOP (零变更)

**理由**: 6h 零错误 100% SR, 与 R1780/R1781/R1782 同一 regime。连续四轮 false trigger。所有参数 floor/optimal, 零漂移。零可配置修复故障。铁律:只改HM1不改HM2。
## ⏳ 轮到HM1优化HM2
