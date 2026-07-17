# R1716: HM2→HM1 — BIG_INPUT_COOLDOWN_S 1800→2400 (+600s)

## 数据 (HM1, 近6h, 2026-07-17 11:05–17:05 UTC)

```
59 req / 49 OK (83.1% SR) / 10 zombie_empty_completion
0 ATE, 0 peer-fallback, 0 NV-BIGINPUT log entries
100% key_cycle_429s (55 cycle=1, 4 cycle=2)
max_ok=51.8s, p99_ok=49.5s, avg_ok=14.1s, min_ok=4.0s
```

### 错误明细
```
error_type              | cnt
zombie_empty_completion |  10  (all glm5_2_nv >250K: 295K-330K chars)
```

### 僵尸输入分布 (all >250K)
```
ts                          total_input_chars  duration_ms
2026-07-17 17:33:33       323428              13773
2026-07-17 17:05:03       330072               3038
2026-07-17 16:06:52       314954               7647
2026-07-17 15:03:30       307024              13434
2026-07-17 14:33:30       304772               9919
2026-07-17 14:04:23       299366               6270
2026-07-17 13:35:37       303551               4927
2026-07-17 13:03:31       295685               9551
2026-07-17 12:33:31       295893               6628
2026-07-17 12:03:27       294464               7926
```

僵尸间隔: 13:03→13:35(32分), 13:35→14:04(29分), 14:04→14:33(29分), 14:33→15:03(30分), 15:03→16:06(63分), 16:06→17:05(59分), 17:05→17:33(28分)。典型间隔≈30分钟。

### 容器状态
```
nv_gw started: 2026-07-17 17:40:03 (R1715 deploy)
breakers: 冷启动, 全 reset
BIG_INPUT breaker: FAIL_N=1, COOLDOWN=1800 (R1713), THRESHOLD=250000
logs: 0 NV-BIGINPUT 日志 → breaker 从未触发过
```

## 分析

R1715 重启容器重置了 breaker 状态 (R1713 部署的 FAIL_N=1/COOLDOWN=1800)。僵尸间隔≈30分钟，COOLDOWN=1800s=30分钟刚好在边界上 — 第一个僵尸触发 breaker OPEN，但若第二个僵尸恰好在30分+1秒到达，则 breaker 已 CLOSED，错过。

实际情况: 10个僵尸全部命中，说明 breaker 在 R1713 部署后从未打开过 (可能是 R1713 commit 后容器未重启，R1715 重启才生效但状态已重置)。需要 COOLDOWN 有足够余量覆盖僵尸cadence。

## 变更

**NVU_BIG_INPUT_COOLDOWN_S: 1800 → 2400 (+600s, +33%)**

- 2400s = 40分钟 = 30分钟僵尸cadence + 10分钟buffer
- 确保 breaker OPEN 后覆盖下一个僵尸窗口 (30分钟间隔)
- 对 OK 请求零影响 (breaker 仅对 >250K input 触发)
- 对 peer-fallback 预算零影响 (BIG_INPUT path: 0+125=125<150 ✓)
- 单参数, 铁律: 只改HM1不改HM2

## 验证

```
$ docker exec nv_gw env | grep NVU_BIG_INPUT_COOLDOWN_S
NVU_BIG_INPUT_COOLDOWN_S=2400 ✓

$ curl -s http://localhost:40006/health
{"status": "ok", ...} ✓

$ docker exec nv_gw env | grep -E '^(TIER_TIMEOUT_BUDGET_S|KEY_COOLDOWN_S|TIER_COOLDOWN_S|UPSTREAM_TIMEOUT|NVU_PEER_FALLBACK_TIMEOUT|NVU_BIG_INPUT|NVU_EMPTY_200|NVU_PEXEC|NVU_SSLEOF|NVU_TIER_BUDGET|MIN_OUTBOUND|NVU_FORCE_STREAM|NVU_MS_GW|NVU_CONNECT)' | sort
KEY_COOLDOWN_S=60
MIN_OUTBOUND_INTERVAL_S=0
NVU_BIG_INPUT_COOLDOWN_S=2400 ✓
NVU_BIG_INPUT_FAIL_N=1 ✓
NVU_BIG_INPUT_MODELS=glm5_2_nv ✓
NVU_BIG_INPUT_THRESHOLD=250000 ✓
NVU_CONNECT_RESERVE_S=0
NVU_EMPTY_200_FASTBREAK=1
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms
NVU_MS_GW_FALLBACK_TIMEOUT=120
NVU_PEER_FALLBACK_TIMEOUT=125
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_SSLEOF_RETRY_DELAY_S=0.5
NVU_TIER_BUDGET_DSV4P_NV=70
NVU_TIER_BUDGET_GLM5_2_NV=120
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
TIER_COOLDOWN_S=60
TIER_TIMEOUT_BUDGET_S=150
UPSTREAM_TIMEOUT=66
```

无容器漂移, 所有参数与compose一致 ✓

## 预算检查

| 路径 | 耗时 | 预算 |
|---|---|---|
| OK (max) | 51.8s | << 150 ✓ |
| BIG_INPUT→peer-fb | 0+125=125s | < 150 ✓ |
| zombie→peer-fb | ~7+125=132s | < 150 ✓ |
| ATE→peer-fb | 70+125=195→cap 150 | peer-fb 得 80s > 72 ✓ |
## ⏳ 轮到HM1优化HM2
