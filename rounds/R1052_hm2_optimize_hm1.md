# HM2 Optimize HM1 — Round R1052

## 触发类型

False trigger (double-dispatch). R1051 already submitted as NOP; cron re-dispatched.

## 数据收集 (改前必有数据)

### 6h DB
- 36req/36OK(100.0%)/0fail
- All requests: nv_integrate (glm5_2_nv only)
- avg TTFB: 7986ms, avg duration: 8314ms, max: 19894ms
- nv_tier_attempts: 0 rows (zero errors)
- 0 fallbacks triggered

### 6h 错误分类
- 0 errors (perfect regime)

### nv_gw 日志 (tail 500)
- 18 integrate successes, 2 SSLEOFErrors on k2 (proxy 7895)
  - Both recovered by SSL-CYCLE to k3 in ~4s
  - SSLEOFError at 5001ms and 5002ms — consistent k2 proxy issue
- 零 NV-TIER-FAIL, 零 NV-EMPTY-FASTBREAK, 零 NV-TIMEOUT-FASTBREAK
- 零 NV-MS-FB, 零 NV-PEER-FB, 零 ATE

### nv_gw env (关键参数)
- UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=110
- TIER_COOLDOWN_S=18, KEY_COOLDOWN_S=25
- NV_INTEGRATE_KEY_COOLDOWN_S=0
- NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_EMPTY_200_FASTBREAK=2
- NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
- NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
- NVU_TIER_BUDGET_GLM5_2_NV=96, NVU_TIER_BUDGET_MINIMAX_M3_NV=100
- NVU_STREAM_TOTAL_DEADLINE_S=90
- NVU_INTEGRATE_THINKING_TIMEOUT_S=90
- NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
- NVU_MS_GW_FALLBACK_TIMEOUT=90
- FALLBACK_HEALTH_THRESHOLD=0.05, NVU_FALLBACK_HEALTH_THRESHOLD=0.10
- NVU_CONNECT_RESERVE_S=0, NVU_SSLEOF_RETRY_DELAY_S=1.0
- NVU_PEER_FALLBACK_ENABLED=1, NVU_PEER_FALLBACK_TIMEOUT=45
- MIN_OUTBOUND_INTERVAL_S=0

### 容器状态
- nv_gw: Up 2 hours (healthy)
- ms_gw: Up 8 hours (healthy)
- All 9 containers healthy

## 决策

**NOP (Zero param, zero compose, zero restart).**

理由:
1. 6h 100% SR (36/36), 零错误, 零 ATE — 系统已完美稳定
2. nv_tier_attempts 0 rows — 无任何 key 级失败
3. 全部参数已在 optimal/floor 状态:
   - FASTBREAK 全部=1 (floor), EMPTY_200_FASTBREAK=2
   - NV_INTEGRATE_KEY_COOLDOWN_S=0 (floor)
   - NVU_CONNECT_RESERVE_S=0 (floor)
   - NVU_SSLEOF_RETRY_DELAY_S=1.0 (floor)
   - MIN_OUTBOUND_INTERVAL_S=0 (floor)
   - FALLBACK_HEALTH_THRESHOLD=0.05 (floor)
4. k2 SSLEOFError (2 occurrences) 是 mihomo proxy 7895 已知问题，SSL-CYCLE 机制完美处理，非 config 可修
5. 无新错误模式，无退化信号
6. 铁律：只改 HM1 不改 HM2

## ⏳ 轮到HM1优化HM2