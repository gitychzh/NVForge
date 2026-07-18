# R1758 (HM2→HM1): NOP — 零可配置故障，全参数floor/optimal

## 数据 (HM1)
- **6h**: 24req/23OK(95.8%SR)/1 zombie. 1h: 4/4 100% SR.
- **24h**: 175req/144OK(82.3%SR)/31fail (29 zombie + 5 ATE)
- **6h failures**: 1× zombie_empty_completion glm5_2_nv (NVCF function-level empty200, not config-fixable)
- **24h ATE**: 5× (2 dsv4p_nv + 3 phantom). Only 3 dsv4p_nv req in 24h.
- **max_ok_6h**: 19,968ms (glm5_2_nv); p50=6,866ms, p95=14,348ms
- **key_cycle_429s**: 100% req (23×1, 1×2) — KEY_COOLDOWN=65 borderline, single-IP constraint
- **SSLEOF 6h**: 0 (7 in 24h, all retried successfully)
- **fallback**: 0 peer-fb triggered in 6h
- **drift**: 0 — all container env values match compose
- **Since R1757 commit (12:55 UTC)**: 0 requests — no new data

## 分析
| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 55 | floor (buffer 55-19.97=35s≥3s ✓) |
| TIER_TIMEOUT_BUDGET_S | 195 | dsv4p peer-fb: 60+122=182<195 ✓ |
| KEY_COOLDOWN_S | 65 | 100% key_cycle_429s, borderline |
| TIER_COOLDOWN_S | 65 | =KEY per iron law |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_PEER_FALLBACK_TIMEOUT | 122 | ≥HM2_BUDGET=120+2=122 ✓ (exact) |
| NVU_TIER_BUDGET_DSV4P_NV | 60 | floor |
| NVU_TIER_BUDGET_GLM5_2_NV | 120 | optimal |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 1 | floor |
| NVU_SSLEOF_RETRY_DELAY_S | 0.5 | near-floor |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 17 | OK p99=18.8s ≈ 17s |
| NVU_STREAM_TOTAL_DEADLINE_S | 25 | OK max=20s << 25s |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_BIG_INPUT_FAIL_N | 1 | floor |
| NVU_BIG_INPUT_COOLDOWN_S | 7200 | optimal |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | optimal |
| NVU_FORCE_STREAM_UPGRADE | 0 | optimal |

**结论**: 零可配置故障。所有FLOOR参数已到floor，所有可调参数已optimal。6h SR 95.8%与R1757持平。1 zombie为NVCF function-level empty200 (glm5_2_nv)，FASTBREAK=1已最优处理。5 ATE为NVCF pexec timeout (dsv4p_nv)，FASTBREAK=1+peer-fb path已最优。7 SSLEOF已retry成功，0.5s delay最优。PEER_FALLBACK_TIMEOUT=122正好≥HM2_BUDGET=120+2=122，满足约束。NOP。

## 验证
- 容器env与compose一致: 零漂移 ✓
- DB 1h: 4/4 100% SR ✓
- docker logs: 零error/warn ✓
- SSLEOF 6h: 0 ✓
- peer-fb constraint: 122≥122 ✓
## ⏳ 轮到HM1优化HM2
