# R1820 (HM2→HM1): NOP — 零可配置修复故障, 全部外部NVCF降级

## 数据快照

```
6h:  29req/25OK(86.2%SR)/4fail
24h: 122req/109OK(89.3%SR)/13fail
```

| model | total | ok | sr | avg_ms | failures |
|---|---|---|---|---|---|
| glm5_2_nv | 24 | 24 | 100% | 10327 | 0 |
| kimi_nv | 4 | 0 | 0% | 430 | 4 ATE (NVCF degradation) |
| dsv4p_nv | 1 | 1 | 100% | 2391 | 0 |

24h failures:
- 6 zombie_empty_completion (glm5_2_nv): NVCF function-level degradation, all 5 keys return empty200
- 4 kimi ATE: NVCF function-level degradation, all tiers exhausted instantly (duration 1ms, 1715ms)
- 3 dsv4p ATE: NVCF function-level degradation

## 分析

- **glm5_2_nv**: 100% SR (24/24), avg 10327ms, P50 ~9000ms — 健康
- **kimi ATE**: 4/4 全部 duration < 2s → 调度层 tier 瞬间耗尽, 非 key/cooldown 可修
- **zombie glm5_2**: 6/6 全部 empty200 from all 5 keys → NVCF function 级降级, FASTBREAK=1 已正确快速终止
- **dsv4p ATE**: 3/3 全部 NVCF function 级降级, peer-fb 未触发(外部原因)
- **nv_gw logs**: 零错误, 零 warn
- **key_cycle_429s**: 104/122 (85.2%) — 正常 key 轮转, 无异常
- **peer-fallback**: 0/122 触发 — 零次救援(无合适场景)
- **Post R1819 deploy 后**: 零新请求 (last request 2026-07-18 17:33 UTC)
- **零 zombie/fallback/peer-fb/429 异常**
- **零 container drift**: env 与 compose 完全一致

## 判定

全部 13 条失败(4 kimi ATE + 6 zombie + 3 dsv4p ATE) 均为外部 NVCF function-level 降级.
零可配置修复故障.
所有参数已在 floor/optimal:
- KEY_COOLDOWN_S=63 (floor: 60s NVCF boundary + 3s buffer)
- TIER_COOLDOWN_S=63 (=KEY per iron law)
- UPSTREAM_TIMEOUT=55 (max_ok=51.8s, buffer=3.2s ≥ 3s)
- TIER_TIMEOUT_BUDGET_S=180 (UPSTREAM 55+PEER 122=177 < 180, 3s margin)
- STREAM_FIRST_BYTE_DEADLINE_S=15 (OK p99=10.8s << 15s)
- STREAM_TOTAL_DEADLINE_S=25 (OK p99=10.8s << 25s)
- SSLEOF_RETRY_DELAY_S=0.2 (floor)
- PEXEC_TIMEOUT_FASTBREAK=1 (floor)
- EMPTY_200_FASTBREAK=1 (floor)
- MIN_OUTBOUND_INTERVAL_S=0 (floor)
- CONNECT_RESERVE_S=0 (floor)
- NV_INTEGRATE_KEY_COOLDOWN_S=0 (floor)
- 铁律:只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
