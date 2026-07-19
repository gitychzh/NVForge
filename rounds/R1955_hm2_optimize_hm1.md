# R1955 (HM2→HM1): NOP — 全参数 floor/optimal, 30min 100% SR, 5 zombie all glm5_2 big_input NVCF-degraded, 零配置可修

## 数据
- 6h: 34 req, 29 OK (85.3% SR), 5 fail (status=502)
- 30min: 2 req, 2 OK (100% SR)
- Post-deploy (R1953 deploy ~17:31 UTC): 2 req, 2 OK (100% SR)
- glm5_2_nv: 29 OK, avg=10221ms, min=3484ms, max=26165ms
- dsv4p_nv: 0 traffic (6h)
- kimi_nv: 0 traffic (6h)

## 错误分解
- 5× `zombie_empty_completion` (status=502), all glm5_2_nv, all input > 115K (BIG_INPUT)
  - Input sizes: 141578-144775 chars
  - Timestamps: 12:03, 12:33, 13:03, 14:03, 15:03 UTC (~30min spacing)
- 8× `all_tiers_exhausted` + status=200 (phantom ATE, rescued by BIG_INPUT breaker → peer-fb → empty200)
  - ttfb: 5-11ms (peer-fb response)
  - All input > 115K
- 0 real ATE, 0 new error types
- key_cycle_429s: 16 req with 1 cycle each, normal rotation

## 容器状态
- Container: nv_gw, StartedAt: 2026-07-19T17:31:47Z (R1953 deploy)
- docker logs --tail 100: (no error/warn found)
- env matches compose, no drift

## 参数验证
| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 30 | floor |
| TIER_TIMEOUT_BUDGET_S | 153 | R1953: 152→153 (break = boundary) |
| KEY_COOLDOWN_S | 60 | R1893: KEY=TIER=60 |
| TIER_COOLDOWN_S | 60 | R1893: KEY=TIER=60 |
| NVU_PEER_FALLBACK_TIMEOUT | 122 | R1744 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 1 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| NVU_BIG_INPUT_COOLDOWN_S | 21600 | 6h |
| NVU_BIG_INPUT_FAIL_N | 1 | floor |
| NVU_BIG_INPUT_THRESHOLD | 115000 | |
| NVU_BIG_INPUT_MODELS | glm5_2_nv,dsv4p_nv | |
| NVU_TIER_BUDGET_GLM5_2_NV | 30 | R1931 |
| NVU_TIER_BUDGET_DSV4P_NV | 25 | R1928 |
| NVU_SSLEOF_RETRY_DELAY_S | 0.1 | |

## 决策: NOP

介入四条全不满足:
1. 6h SR 85.3% 非持续跌破80% (30min 100%)
2. 5 zombie 全 NVCF empty200 已知类 (非配置可修), 0 real ATE
3. BIG_INPUT breaker 正常 (FAIL_N=1, COOLDOWN=21600, 8 phantom ATE rescued → peer-fb)
4. Peer-fallback 正常 (phantom ATE 200 with ttfb 5-11ms)
5. 0 新错误类型, 0 参数漂移

所有参数在 floor/optimal。BIG_INPUT breaker + peer-fb 100% 有效 (8 phantom rescue)。5 zombie 均为 NVCF 双端 empty200 降级 (非 HM1 配置可修)。NOP 无据不改。

铁律: 只改HM1不改HM2

## ⏳ 轮到HM1优化HM2
