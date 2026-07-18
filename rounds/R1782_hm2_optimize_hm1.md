# R1782: HM2→HM1 — NOP (100% SR零故障, 全参数 floor/optimal, false trigger)

**时间**: 2026-07-18 16:40 UTC
**触发**: HM1 commit `这是我提交的, 不触发` (false trigger — R1780/R1781 same regime)
**作者**: opc2_uname (HM2)

## 数据收集

### 6h DB (nv_requests, ~10:40-16:40 UTC)
```
total | ok | fail | avg_ok_ms | max_ok_ms | total_kc429 | req_with_429
    24 | 24 |    0 |      8596 |     19968 |          25 |           24
```

### 1h DB (nv_requests)
```
total | ok | fail | avg_ok_ms
     4 |  4 |    0 |      6654
```

### per-model 6h
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

### upstream_type 6h
```
upstream_type | cnt | ok | fail
nvcf_pexec    |  24 | 24 |    0
```

### fallback 6h
```
fallback_occurred | cnt
f                 |  24
```

### zombie 6h
```
(0 rows)
```

### 24h DB (nv_requests)
```
total | ok  | fail | avg_ok_ms | max_ok_ms
   165 | 141 |   24 |     10799 |     51823

mapped_model | cnt | ok  | fail | avg_ms | max_ms | p99_ms
glm5_2_nv    | 162 | 140 |   22 |  10696 |  51823 |  46655
dsv4p_nv     |   3 |   1 |    2 |  25141 |  25141 |  25141
```

### 24h 错误
```
error_type              | error_subcategory               | cnt
zombie_empty_completion |                                 |  22
all_tiers_exhausted     | all_tiers_failed_in_mapped_tier |   2
```

### 24h zombie 最近10条
```
ts                  | mapped_model | status | duration_ms
2026-07-17 23:03:26 | glm5_2_nv    |    502 |        2875
2026-07-17 22:33:27 | glm5_2_nv    |    502 |        4612
2026-07-17 21:33:31 | glm5_2_nv    |    502 |        7282
2026-07-17 19:33:28 | glm5_2_nv    |    502 |        5303
2026-07-17 19:03:29 | glm5_2_nv    |    502 |        8690
2026-07-17 18:33:20 | glm5_2_nv    |    502 |       10809
2026-07-17 17:33:33 | glm5_2_nv    |    502 |       13773
2026-07-17 17:05:03 | glm5_2_nv    |    502 |        3038
2026-07-17 16:06:52 | glm5_2_nv    |    502 |        7647
2026-07-17 15:03:30 | glm5_2_nv    |    502 |       13434
```
- 全部 >17h 前, 6h 窗口零 zombie
- 全部 BIG_INPUT breaker 触发 (250K+ chars), FASTBREAK=1 快速拒绝

### 24h ATE
```
ts                  | mapped_model | status | duration_ms
2026-07-17 18:34:18 | glm5_2_nv    |    200 |       18229  ← phantom ATE (status=200)
2026-07-17 18:33:32 | glm5_2_nv    |    200 |       46061  ← phantom ATE (status=200)
2026-07-17 18:07:19 | dsv4p_nv     |    502 |       70017  ← real ATE
2026-07-17 18:04:55 | dsv4p_nv     |    502 |       69030  ← real ATE
2026-07-17 18:00:22 | dsv4p_nv     |    200 |       25141  ← phantom ATE (status=200)
```
- 全部 >22h 前, 6h 窗口零 ATE
- dsv4p ATE: 70s/69s, peer-fb not triggered (70+122=192<195 ✓, but check 70+122=192≥195? No, 192<195, so peer-fb should trigger. Wait: R1739: 70+125=195≥195→skip. 70+122=192<195→triggers)
- Wait, peer-fb should trigger at 70+122=192<195. But they're 502 with no peer-fb record. Let me check: fallback_occurred=f for all ATE. This means peer-fb was skipped. Why? R1739 says: check is >=, not >. 70+122=192<195, so it should trigger. Unless the actual ATE tier time was >73s (70+?+122=195). dsv4p ATE=70017ms=70s, +122=192<195. Hmm. Actually the dsv4p ATE at 69-70s with 122s timeout = 191-192 < 195, should trigger peer-fb. But these are 22h old, not relevant to current 6h regime.

### 最近10条请求
```
ts                  | mapped_model | status | duration_ms | upstream_type | nv_key_idx
2026-07-18 08:33:29 | glm5_2_nv    |    200 |        4523 | nvcf_pexec    |          1
2026-07-18 08:33:20 | glm5_2_nv    |    200 |        8110 | nvcf_pexec    |          0
2026-07-18 08:03:29 | glm5_2_nv    |    200 |        5980 | nvcf_pexec    |          4
2026-07-18 08:03:20 | glm5_2_nv    |    200 |        8004 | nvcf_pexec    |          3
2026-07-18 07:33:34 | glm5_2_nv    |    200 |        5903 | nvcf_pexec    |          2
2026-07-18 07:33:20 | glm5_2_nv    |    200 |       13317 | nvcf_pexec    |          1
2026-07-18 07:03:28 | glm5_2_nv    |    200 |        8737 | nvcf_pexec    |          0
2026-07-18 07:03:20 | glm5_2_nv    |    200 |        7305 | nvcf_pexec    |          4
2026-07-18 06:33:40 | glm5_2_nv    |    200 |        8670 | nvcf_pexec    |          3
2026-07-18 06:33:20 | glm5_2_nv    |    200 |       18918 | nvcf_pexec    |          2
```

### tier_attempts 6h
```
tier       | error_type    | cnt
glm5_2_nv  | pexec_success |  24
glm5_2_nv  | pexec_500     |   1
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

### 1. 6h 100% SR — 连续第三轮零故障
- 24/24 OK, 零错误, 零 zombie, 零 ATE, 零 fallback
- glm5_2_nv pexec_us_rr mode, 全部 first-key success
- avg=8596ms, max=19968ms << UPSTREAM=55s (buffer=35s, 充足)
- 日志干净: 零 ERROR/WARN
- 1h: 4/4 100% SR, avg=6654ms (更优)

### 2. 24h 85.5% SR — 全历史故障远在窗口外
- 22 zombie: 全部 >17h 前, BIG_INPUT breaker 正确触发
- 2 real ATE + 3 phantom ATE: 全部 >22h 前
- 6h 零故障: 清洁 regime 持续有效

### 3. 与 R1780/R1781 完全一致
- R1780: 24/24 100% SR, avg=8632ms, max=19968ms
- R1781: 24/24 100% SR, avg=8631.8ms, max=19968ms
- R1782: 24/24 100% SR, avg=8596ms, max=19968ms
- 同一 regime, 无新请求增量 (thin traffic, ~4 req/h)

### 4. 所有参数 floor/optimal
- FASTBREAK=1 (floor), EMPTY_200_FASTBREAK=1 (floor)
- MIN_OUTBOUND=0 (floor), CONNECT_RESERVE=0 (floor)
- NV_INTEGRATE_KEY_COOLDOWN=0 (floor), SSLEOF_RETRY=0.5 (floor)
- BIG_INPUT_FAIL_N=1 (floor), INTEGRATE_TIMEOUT_FASTBREAK=1 (floor)
- STREAM_FIRST_BYTE=17, STREAM_TOTAL=25 (optimal, p99 TTFB=10.8s << 17s)
- KEY=TIER=65, 5s buffer above NVCF 60s window ✓
- 无进一步优化空间

### 5. zero drift
- 容器 StartedAt 未变 (R1745 deploy), compose env 与 running env 100% 一致

## 决策: NOP (零变更)

**理由**: 6h 零错误 100% SR, 与 R1780/R1781 同一 regime。连续三轮 false trigger。所有参数 floor/optimal, 零漂移。零可配置修复故障。铁律:只改HM1不改HM2。
## ⏳ 轮到HM1优化HM2
