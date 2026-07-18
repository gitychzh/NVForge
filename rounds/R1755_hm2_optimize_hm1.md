# R1755 (HM2→HM1): NOP — 零可配置故障，全参数floor/optimal

## 数据 (HM1)
- **6h**: 24req/22OK(91.7%SR)/2 zombie. 1h: 4/4 100% SR.
- **24h**: 177req/145OK(81.9%SR)/30 zombie+2 ATE dsv4p_nv
- **6h failures**: 2× zombie_empty_completion glm5_2_nv (NVCF function-level empty200, not config-fixable)
- **24h ATE**: 2× dsv4p_nv @ 70,017ms/69,030ms (single-key pexec timeout, NVCF function degraded)
- **max_ok_6h**: 19,968ms (glm5_2_nv); max_ok_24h: 51,823ms
- **key_cycle_429s**: 100% req (23×1, 1×2) — KEY_COOLDOWN=65 borderline, can't reduce
- **fallback**: 0 peer-fb triggered in 6h
- **drift**: 0 — all container env values match compose

## 分析
| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 55 | floor (buffer 55-51.8=3.2s≥3s ✓) |
| TIER_TIMEOUT_BUDGET_S | 195 | dsv4p peer-fb: 70+122=192<195 ✓ |
| KEY_COOLDOWN_S | 65 | 100% key_cycle_429s, borderline |
| TIER_COOLDOWN_S | 65 | =KEY per iron law |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_PEER_FALLBACK_TIMEOUT | 122 | ≥HM2_BUDGET(70)+2 ✓ |
| NVU_TIER_BUDGET_DSV4P_NV | 60 | floor |
| NVU_TIER_BUDGET_GLM5_2_NV | 120 | optimal |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 1 | floor |
| NVU_SSLEOF_RETRY_DELAY_S | 0.5 | near-floor |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 17 | OK p99=10.8s << 17s |
| NVU_STREAM_TOTAL_DEADLINE_S | 25 | OK max=20s << 25s |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_BIG_INPUT_FAIL_N | 1 | floor |
| NVU_BIG_INPUT_COOLDOWN_S | 7200 | optimal |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | optimal |

**结论**: 零可配置故障。所有FLOOR参数已到floor，所有可调参数已optimal。2 zombie为NVCF function-level empty200 (glm5_2_nv)，FASTBREAK=1已最优处理。2 ATE为NVCF pexec timeout (dsv4p_nv)，FASTBREAK=1+peer-fb path已最优。NOP。

## 验证
- 容器env与compose一致: 零漂移 ✓
- DB 1h: 4/4 100% SR ✓
- docker logs: 零error/warn ✓

## ⏳ 轮到HM1优化HM2
