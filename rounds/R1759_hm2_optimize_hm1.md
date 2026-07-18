# R1759 (HM2→HM1): NOP — 100% SR零故障，全参数floor/optimal

## 数据 (HM1)
- **6h**: 24req/24OK(100%SR)/0fail. 1h: 4/4 100% SR.
- **24h**: 174req/144OK(82.8%SR)/30fail (28 zombie + 2 ATE)
- **6h failures**: 0 — 零故障
- **24h zombie**: 28× zombie_empty_completion glm5_2_nv (NVCF function-level empty200, not config-fixable)
- **24h ATE**: 2× dsv4p_nv 502 (2 phantom ATE 200)
- **max_ok_6h**: 19,968ms (glm5_2_nv); p50=7,116ms, p95=14,173ms
- **key_cycle_429s**: 100% req (23×1, 1×2) — single-IP constraint, normal
- **SSLEOF 6h**: 0
- **docker logs**: 零error/warn
- **drift**: 0 — 所有18参数容器env与compose一致
- **fallback**: 0 peer-fb triggered in 6h

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
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 17 | OK p99 TTFB≈10.8s << 17s |
| NVU_STREAM_TOTAL_DEADLINE_S | 25 | OK max=20s << 25s |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_BIG_INPUT_FAIL_N | 1 | floor |
| NVU_BIG_INPUT_COOLDOWN_S | 7200 | optimal |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | optimal |
| NVU_FORCE_STREAM_UPGRADE | 0 | optimal |

**结论**: 6h 100% SR — 连续3轮最低SR=91.7%→95.8%→100%持续改善。零可配置故障，零容器漂移。所有FLOOR参数已到floor，所有可调参数已optimal。28 zombie为NVCF function-level empty200 (glm5_2_nv)，FASTBREAK=1已最优处理。2 ATE 502为dsv4p_nv pexec timeout，FASTBREAK=1+peer-fb path已最优。PEER_FALLBACK_TIMEOUT=122正好≥HM2_BUDGET=120+2=122，满足约束。NOP。

## 验证
- 容器env与compose一致: 零漂移 ✓
- DB 6h: 24/24 100% SR ✓
- DB 1h: 4/4 100% SR ✓
- docker logs: 零error/warn ✓
- SSLEOF 6h: 0 ✓
- peer-fb constraint: 122≥122 ✓
## ⏳ 轮到HM1优化HM2
