# R1954 (HM2→HM1): NOP — 全参数 floor/optimal, 30min 100% SR, 零配置可修错误

## 数据
- **6h**: 34req, 29OK (85.3% SR), 5 zombie (502)
- **30min**: 2req, 2OK (100% SR)
- glm5_2_nv: 29 OK, avg=10221ms, min=3484ms, max=26165ms
- 5 failures: all `zombie_empty_completion` (status=502), glm5_2_nv, input=141K-145K chars (>115K BIG_INPUT threshold)
- BIG_INPUT breaker: 零 BREAKER 日志 (容器重启后 breaker 状态 CLOSED, 5 zombie 均 pre-restart)
- Post-restart: 2/2 OK, tier_attempts 零 error (仅 pexec_success × 16)
- Phantom ATE: 18 (status=200, error_type=all_tiers_exhausted) — 非真实失败
- Peer-fallback: 0
- Key cycle 429s: 16 (全部单cycle, 正常轮转)

## 24h
- 165req, 110OK (66.7% SR), 55 fail
- 51 zombie_empty_completion (glm5_2_nv) + 2 zombie (dsv4p_nv) + 2 ATE (dsv4p_nv)
- 全部 NVCF 服务端退化, 非配置可修

## 容器状态
- 零漂移: 所有 env 与 compose 一致
- 全参数在 floor/optimal:
  - KEY_COOLDOWN_S=60, TIER_COOLDOWN_S=60
  - UPSTREAM_TIMEOUT=30
  - TIER_TIMEOUT_BUDGET_S=153
  - NVU_PEER_FALLBACK_TIMEOUT=122
  - NVU_TIER_BUDGET_GLM5_2_NV=30, NVU_TIER_BUDGET_DSV4P_NV=25
  - NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_EMPTY_200_FASTBREAK=1
  - NVU_BIG_INPUT_THRESHOLD=115000, FAIL_N=1, COOLDOWN=21600
  - MIN_OUTBOUND_INTERVAL_S=0, NVU_CONNECT_RESERVE_S=0
  - NVU_SSLEOF_RETRY_DELAY_S=0.1
  - NVU_STREAM_FIRST_BYTE_DEADLINE_S=15, NVU_STREAM_TOTAL_DEADLINE_S=25

## 决策: NOP
1. 全参数已在 floor, 无进一步压缩空间
2. 5 zombie 全部 pre-restart (BIG_INPUT breaker 状态 CLOSED 重置), 后续 breaker 应有保护
3. 30min 100% SR 零故障
4. 24h 错误全部 NVCF 服务端 zombie (非配置可修)
5. 铁律: 只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
