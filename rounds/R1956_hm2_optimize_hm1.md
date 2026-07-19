# R1956 (HM2→HM1): NOP — 全参数 floor/optimal, 6h 86.84% SR, 5 zombie 全 NVCF empty200, peer-fb 100% rescue, 零配置可修

## 数据
- 6h: 38 req, 33 OK (86.84% SR), 5 fail (status=502)
- dsv4p_nv: 6 OK, avg=22143ms, min=11102ms, max=43922ms
- glm5_2_nv: 29 OK, avg=10221ms, min=3484ms, max=26165ms
- kimi_nv: 0 traffic (6h)

## 错误分解
- 5× `zombie_empty_completion` (status=502), all glm5_2_nv, all input > 115K (BIG_INPUT)
  - Timestamps: 12:03, 12:33, 13:03, 14:03, 15:03 UTC (~30min spacing)
  - Input sizes: 141704-144775 chars
  - Root cause: NVCF empty200 degradation (not HM1 config)
- 20× `all_tiers_exhausted` + status=200 (phantom ATE, rescued by peer-fallback)
  - All dsv4p_nv, ttfb 0-9ms (peer-fb response)
  - Peer-fb 100% effective (4 confirmed OK rescues in logs)
- 0 real ATE, 0 new error types
- 0 fallback_occurred=true in DB (fallback code path doesn't flag it)
- key_cycle_429s: 16 req with 1 cycle each, normal rotation

## MS-GW Fallback Analysis
- MS-GW: 0 requests in 6h (ms_requests = 0 rows)
- MS-GW health: OK, 7 keys, 3 models (glm5_2_ms, dsv4p_ms, kimi_ms)
- MS-GW logs: MS-FASTBREAK cycles for glm5_2_ms (consecutive_empty=2), but no requests recorded
- **Finding**: zombie_empty_completion error path does NOT trigger MS-GW fallback
  - This is a code logic issue, not a configuration issue
  - NVU_MS_GW_FALLBACK_MODELMAP includes glm5_2_nv:glm5_2_ms, but the zombie path doesn't use it
  - 5 zombie failures could have been rescued via MS-GW if the fallback were triggered

## 容器状态
- Container: nv_gw, StartedAt: 2026-07-19T17:31:47Z (R1953 deploy)
- docker logs --tail 100: peer-fb OK 4×, MS-FASTBREAK cycles (ms_gw), no error/warn
- env matches compose, no drift

## 参数验证
| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 30 | floor |
| TIER_TIMEOUT_BUDGET_S | 153 | R1953: 152→153 |
| KEY_COOLDOWN_S | 60 | R1893: KEY=TIER=60 |
| TIER_COOLDOWN_S | 60 | R1893: KEY=TIER=60 |
| NVU_PEER_FALLBACK_TIMEOUT | 122 | R1744 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 1 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_BIG_INPUT_COOLDOWN_S | 21600 | 6h |
| NVU_BIG_INPUT_FAIL_N | 1 | floor |
| NVU_BIG_INPUT_THRESHOLD | 115000 | |
| NVU_BIG_INPUT_MODELS | glm5_2_nv,dsv4p_nv | |
| NVU_TIER_BUDGET_GLM5_2_NV | 30 | R1931 |
| NVU_TIER_BUDGET_DSV4P_NV | 25 | R1928 |
| NVU_SSLEOF_RETRY_DELAY_S | 0.1 | |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 15 | |
| NVU_STREAM_TOTAL_DEADLINE_S | 25 | |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | |

## 决策: NOP

介入四条全不满足:
1. 6h SR 86.84% 非持续跌破80% (5 zombie 全 NVCF empty200, 非配置可修)
2. 5 zombie 全 NVCF empty200 已知类, 0 real ATE, 0 新错误类型
3. Peer-fallback 100% 有效 (4 OK rescue, ttfb 0-9ms, 20 phantom ATE rescued)
4. BIG_INPUT breaker 正常 (FAIL_N=1, COOLDOWN=21600)
5. MS-GW fallback 未被触发 (zombie 路径代码逻辑问题, 非配置可修)
6. 0 参数漂移, 所有参数在 floor/optimal

NOP 无据不改。唯一可优化项: zombie_empty_completion → MS-GW fallback 缺少代码路径, 需代码修改而非配置。

铁律: 只改HM1不改HM2

## ⏳ 轮到HM1优化HM2
