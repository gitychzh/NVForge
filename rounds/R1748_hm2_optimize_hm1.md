# R1748 (HM2→HM1): NOP — false trigger, 零可配置修复故障

**方向**: HM2 → HM1 (铁律:只改HM1不改HM2)
**执行时间**: 2026-07-18 11:05 UTC
**前置commit**: 218d9cf R1747 (HM2→HM1): NOP
**数据窗口**: 6h (2026-07-18 05:00Z–11:00Z)

## 数据采集

### 容器状态
- `nv_gw`: Up, healthy, StartedAt=2026-07-18T01:59:44Z (post-R1745 restart)
- `logs_db`: Up, healthy
- `ms_gw`, `cc4101`: 正常
- 容器env=compose 零漂移 ✓

### 6h 窗口 (25 req)
```
total | ok | fail | avg_ok_ms | max_ok_ms | total_429 | req_with_429
    25 | 22 |    3 |      7556 |     19968 |        26 |          25
```

### 按模型 (6h)
```
mapped_model | cnt | ok | fail | avg_ok_ms | max_ok_ms
glm5_2_nv    |  25 | 22 |    3 |      7556 |     19968
```
- dsv4p_nv: 0 traffic
- kimi_nv: 0 traffic
- minimax_m3_nv: 0 traffic

### 错误明细 (6h)
```
error_type              | cnt | status | 说明
zombie_empty_completion |   3 |    502 | NVCF content-filter, >250K chars, BIG_INPUT breaker正确拦截
```
- 0 ATE (all_tiers_exhausted)
- 0 peer-fallback
- 0 ms-gw fallback
- 0 SSLEOF
- 0 pexec timeout
- 3 zombie: 21:33Z (7282ms), 22:33Z (4612ms), 23:03Z (2875ms) — all within R1747 window

### 日志 (docker logs --tail 50)
```
[11:03:20.5] NV-GLM52-ATTEMPT k4 pexec timeout=55s
[11:03:23.9] NV-GLM52-KEY-FAULT k4 fault → RR advance to k5
[11:03:29.4] NV-GLM52-SUCCESS k5 succeeded (8928ms)
[11:03:30.0] NV-GLM52-ATTEMPT k5 pexec timeout=55s
[11:03:49.9] NV-GLM52-SUCCESS k5 succeeded (19968ms)
```
- 1× KEY-FAULT (k4 transient, RR→k5 restored), 零 ERROR/WARN/exception
- 正常 pexec_us_rr 请求流，key轮转正常

### 上游路径 (6h)
```
upstream_type | cnt
nvcf_pexec    |  25
```
- 100% pexec, 0 integrate (NV_INTEGRATE_MODELS="" — integrate disabled)

### 24h 错误汇总
```
error_type              | status | cnt
zombie_empty_completion |    502 |  32
all_tiers_exhausted     |    502 |   2 (pre-R1745 dsv4p_nv)
```
- 24h SR: 144/178 = 80.9%
- 32 zombie = NVCF content-filter (BIG_INPUT)，2 dsv4p ATE = pre-R1745 restart

### 当前参数快照 (容器env=compose 零漂移 ✓)
```
UPSTREAM_TIMEOUT=55 (max_ok=19968ms << 55s, 充裕)
TIER_TIMEOUT_BUDGET_S=195 (充裕)
MIN_OUTBOUND_INTERVAL_S=0 (floor)
NVU_PEXEC_TIMEOUT_FASTBREAK=1 (floor)
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1 (floor)
KEY_COOLDOWN_S=65 (floor, single-IP NVCF 60s+5s buffer)
TIER_COOLDOWN_S=65 (KEY=TIER per iron law)
NVU_PEER_FALLBACK_TIMEOUT=122 (peer-fb: 70+122=192<195, 3s margin)
NVU_CONNECT_RESERVE_S=0 (floor)
NVU_SSLEOF_RETRY_DELAY_S=0.5 (near floor)
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_EMPTY_200_FASTBREAK=1 (floor)
NV_INTEGRATE_KEY_COOLDOWN_S=0 (floor)
NV_INTEGRATE_MODELS="" (disabled)
NVU_BIG_INPUT_COOLDOWN_S=7200 (max extension)
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
| KEY_COOLDOWN_S | 65 | R1740 floor, KEY=TIER=65 for single-IP NVCF | 不动 |
| TIER_COOLDOWN_S | 65 | KEY=TIER per iron law | 不动 |
| UPSTREAM_TIMEOUT | 55 | max_ok=19968ms, 35s buffer | 不动 |
| TIER_TIMEOUT_BUDGET_S | 195 | max_ok=19968ms << 195, 充裕 | 不动 |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 17 | OK p99 TTFB << 17s, zombie由FASTBREAK=1先触发 | 不动 |
| NVU_STREAM_TOTAL_DEADLINE_S | 25 | OK p99 << 25s, zombie由FASTBREAK=1先触发 | 不动 |
| 其余参数 | 全部 floor | MIN_OUTBOUND=0, FASTBREAK=1, CONNECT=0, SSLEOF=0.5, EMPTY_200=1, INTEGRATE=0, BIG_INPUT_FAIL_N=1 | 全部 floor |

**结论**: NOP — false trigger。零可配置修复故障。3× zombie=NVCF content-filter (>250K chars)，BIG_INPUT breaker 正确拦截(7200s cooldown, FAIL_N=1, THRESHOLD=250K)。所有参数 floor/optimal。无 dsv4p_nv/kimi_nv 流量，无 peer-fb 验证机会。R1745→R1746→R1747→R1748 连续四轮 NOP，等待 HM1 有新流量模式或 NVCF 状态变化。

## 执行

无变更。直接写回合文件。

## 验证

- 容器env=compose 零漂移 ✓
- 日志: 零 ERROR/WARN/exception，1× KEY-FAULT(k4 transient→k5 restored) ✓
- 6h SR=88.0% (22/25), 3 fail=zombie (NVCF级, 非可配置) ✓
- 24h: 32 zombie + 2 dsv4p ATE (pre-R1745) ✓
- 所有参数 floor/optimal ✓
## ⏳ 轮到HM1优化HM2
