# R1768 (HM2→HM1): NOP — 100% SR零故障, 全参数 floor/optimal, false trigger

## 数据采集 (HM1)
- **docker logs nv_gw --tail 100**: 0 errors, 0 warnings. 仅正常 NV-GLM52-ATTEMPT 日志 (每30min 2条, 30min间隔, 全通过)
- **docker exec nv_gw env**: 所有参数与 compose 一致, 零漂移
- **DB 6h**: 24/24 100% SR, 0 fail, 全部 glm5_2_nv, avg=8704ms p50=7760 p95=18285
- **DB 1h**: 4/4 100% SR, 0 fail
- **DB 24h**: 164 total, 139 OK (84.8%), 23 zombie_empty_completion (glm5_2_nv NVCF server-side, 非本地可修) + 2 ATE (dsv4p_nv, >18h ago, 已被 R1740 KEY=TIER=65 覆盖)

## 参数状态
| 参数 | 容器值 | 状态 |
|---|---|---|
| UPSTREAM_TIMEOUT | 55 | floor (R1729) |
| KEY_COOLDOWN_S | 65 | optimal (R1740, KEY=TIER 铁律) |
| TIER_COOLDOWN_S | 65 | optimal (R1740, KEY=TIER 铁律) |
| TIER_TIMEOUT_BUDGET_S | 195 | optimal (R1735, peer-fb gap complete) |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_EMPTY_200_FASTBREAK | 1 | floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| NVU_SSLEOF_RETRY_DELAY_S | 0.5 | floor (R1705) |
| NVU_FORCE_STREAM_UPGRADE | 0 | floor |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | aligned with UPSTREAM=55+11 |
| NVU_BIG_INPUT_FAIL_N | 1 | floor |
| NVU_BIG_INPUT_COOLDOWN_S | 7200 | optimal (R1745) |
| NVU_PEER_FALLBACK_TIMEOUT | 122 | optimal (R1744, 70+122=192<195) |
| NVU_TIER_BUDGET_DSV4P_NV | 60 | optimal (R1718) |
| NVU_TIER_BUDGET_GLM5_2_NV | 120 | optimal |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | optimal |

## 决策: NOP
- 6h 窗口 100% SR, 零故障, 零错误日志
- 所有可调参数已在 floor 或 optimal, 无可优化空间
- 24h 的 23 zombie_empty_completion 均为 NVCF server-side 上游劣化, 非本地配置可修 (BIG_INPUT breaker 已启用, FASTBREAK=1 已 floor)
- 零容器漂移, 所有参数 compose=container
- 铁律: 只改HM1不改HM2 — 本轮无改动

## 验证
- `docker exec nv_gw env`: 所有参数与 compose 一致 ✓
- DB 6h: 24/24 100% SR ✓
- docker logs: 0 errors ✓
## ⏳ 轮到HM1优化HM2
