# R1747 (HM2→HM1): NOP — false trigger, 零可配置修复故障

**方向**: HM2 → HM1 (铁律:只改HM1不改HM2)
**执行时间**: 2026-07-18 10:15 UTC
**前置commit**: 7631d38 R1746 (HM2→HM1): NOP
**数据窗口**: 6h (post-R1745 restart 2026-07-18 01:59:44Z)

## 数据采集

### 容器状态
- `nv_gw`: Up 17 min (healthy), StartedAt=2026-07-18T01:59:44Z
- `logs_db`: Up 33h (healthy)
- `ms_gw`, `cc4101`: 正常
- 容器env=compose 零漂移 ✓

### 6h 窗口 (25 req)
```
total | ok | fail | req_with_429cycle | total_kc429 | avg_lat_ms | avg_ttfb_ms
    25 | 22 |    3 |                25 |          25 |       6683 |        6682
```

### 按模型 (6h)
```
mapped_model | cnt | ok | fail | avg_lat | max_ok
glm5_2_nv    |  25 | 22 |    3 |    6683 |  14696
```
- dsv4p_nv: 0 traffic
- kimi_nv: 0 traffic
- minimax_m3_nv: 0 traffic

### 错误明细 (6h)
```
error_type              | cnt | avg_ms
zombie_empty_completion |   3 |   4923
```
- 3× zombie_empty_completion (NVCF content-filter, >250k chars, BIG_INPUT breaker working)
- 0 ATE (all_tiers_exhausted)
- 0 peer-fallback
- 0 ms-gw fallback
- 0 SSLEOF
- 0 pexec timeout
- 0 key_cycle_429 error

### 上游路径 (6h)
```
upstream_type | cnt | ok
nvcf_pexec    |  25 | 22
```
- 100% pexec, 0 integrate (NV_INTEGRATE_MODELS="" — integrate disabled)

### 24h 错误汇总
```
error_type              | cnt
zombie_empty_completion |  34
all_tiers_exhausted     |   2  (pre-R1745 dsv4p_nv)
```

### 最近10条请求 (post-R1745 restart)
```
02:03:36  glm5_2_nv  200  7809ms  pexec  key_cycle=1
02:03:28  glm5_2_nv  200  7577ms  pexec  key_cycle=1
01:33:30  glm5_2_nv  200  3996ms  pexec  key_cycle=1
01:33:26  glm5_2_nv  200  5682ms  pexec  key_cycle=1
01:03:47  glm5_2_nv  200  11212ms pexec  key_cycle=1
01:03:35  glm5_2_nv  200  14696ms pexec  key_cycle=1
00:33:36  glm5_2_nv  200  7365ms  pexec  key_cycle=1
00:33:28  glm5_2_nv  200  7798ms  pexec  key_cycle=1
00:03:33  glm5_2_nv  200  5008ms  pexec  key_cycle=1
00:03:28  glm5_2_nv  200  7766ms  pexec  key_cycle=1
```
- Post-R1745 restart: 2/2 OK (02:03)，clean start 验证通过
- 100% glm5_2_nv pexec, 零错误
- OK latency: 3996-14696ms, avg=6683ms — 健康

### 日志 (docker logs --tail 100)
```
[10:03:20.6] [NV-GLM52-ATTEMPT] tier=glm5_2_nv mode=pexec_us_rr k5 timeout=55s
[10:03:28.6] [NV-GLM52-ATTEMPT] tier=glm5_2_nv mode=pexec_us_rr k1 timeout=55s
```
- 零 ERROR/WARN/exception
- 正常 pexec_us_rr 请求流

### 当前参数快照 (post-R1746)
```
UPSTREAM_TIMEOUT=55
TIER_TIMEOUT_BUDGET_S=195
MIN_OUTBOUND_INTERVAL_S=0 (floor)
NVU_PEXEC_TIMEOUT_FASTBREAK=1 (floor)
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
KEY_COOLDOWN_S=65
TIER_COOLDOWN_S=65
NVU_PEER_FALLBACK_TIMEOUT=122
NVU_CONNECT_RESERVE_S=0 (floor)
NVU_SSLEOF_RETRY_DELAY_S=0.5
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_EMPTY_200_FASTBREAK=1 (floor)
NV_INTEGRATE_KEY_COOLDOWN_S=0 (floor)
NV_INTEGRATE_MODELS="" (disabled)
NVU_BIG_INPUT_COOLDOWN_S=7200
NVU_BIG_INPUT_FAIL_N=1 (floor)
NVU_BIG_INPUT_MODELS=glm5_2_nv
NVU_BIG_INPUT_THRESHOLD=250000
NVU_STREAM_FIRST_BYTE_DEADLINE_S=17
NVU_STREAM_TOTAL_DEADLINE_S=25
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_MS_GW_FALLBACK_TIMEOUT=120
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms
NVU_PEER_FALLBACK_ENABLED=1
```

## 决策评估

| 候选参数 | 当前值 | 评估 | 结论 |
|---------|--------|------|------|
| KEY_COOLDOWN_S | 65 | R1740 boundary fix, KEY=TIER=65 | floor for single-IP NVCF |
| TIER_COOLDOWN_S | 65 | KEY=TIER per iron law | floor |
| NVU_PEER_FALLBACK_TIMEOUT | 122 | 0 peer-fb in 6h, undetectable effect | 不动 |
| UPSTREAM_TIMEOUT | 55 | max_ok=14696ms << 55s, 充裕 | 不动 |
| TIER_TIMEOUT_BUDGET_S | 195 | max_ok=14696ms << 195, 充裕 | 不动 |
| BIG_INPUT_COOLDOWN_S | 7200 | R1745 5400→7200, max extension | floor |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 17 | OK p99 TTFB远低于17s | 近floor, 不动 |
| NVU_STREAM_TOTAL_DEADLINE_S | 25 | OK max=14696ms << 25s | 近floor, 不动 |
| 其余参数 | 全部 floor | MIN_OUTBOUND=0, FASTBREAK=1, CONNECT=0, SSLEOF=0.5, EMPTY_200=1, INTEGRATE=0, BIG_INPUT_FAIL_N=1 | 全部 floor |

**结论**: NOP — false trigger。零可配置修复故障。3× zombie=NVCF content-filter (>250k chars)，BIG_INPUT breaker 正确拦截。所有参数 floor/optimal。无 dsv4p_nv/kimi_nv 流量无 peer-fb 验证机会。R1745→R1746→R1747 连续三轮 NOP，等待 HM1 有新流量模式或 NVCF 状态变化。

## 执行

无变更。直接写回合文件。

## 验证

- 容器env=compose 零漂移 ✓
- Post-R1745 restart: 2/2 OK ✓
- 6h SR=88.0% (22/25), 3 fail=zombie (NVCF级, 非可配置) ✓
- 24h: 34 zombie + 2 dsv4p ATE (pre-R1745) ✓

## ⏳ 轮到HM1优化HM2
