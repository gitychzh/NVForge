# HM2 Optimize HM1 — Round R1051

## 触发类型

False trigger (double-dispatch). R1050 已由 pre-run script 提交，symlink 已正确指向 R1050。cron 重复派遣。

## 数据收集 (改前必有数据)

### 6h DB
- 37req/37OK(100.0%)/0fail
- glm5_2_nv: 37/37 100% SR, all via nv_integrate
- avg latency: 8163ms (min 2660ms, max 19894ms)
- nv_tier_attempts: 0 rows (zero errors)
- Last request: 03:04 UTC (~8h ago)

### 24h 错误
- 40 all_tiers_exhausted (historical)
- 3 NVStream_TimeoutError
- 3 stream_total_deadline

### nv_gw (容器)
- Uptime: 2 hours (healthy)
- Logs: SSLEOFError on k2 (已处理, SSL-CYCLE 正常), all integrate first-attempt success
- 零 ATE, 零 NV-TIER-FAIL, 零 NV-EMPTY-FASTBREAK

### ms_gw (容器)
- Uptime: 8 hours (healthy)
- Logs: 正常流转, 仅已知 BrokenPipeError (unfixable)
- EMPTY_200_FASTBREAK_THRESHOLD=3 (已 R900 优化)

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

## 决策

**NOP (Zero param, zero compose, zero restart).**

理由:
1. 6h 100% SR, 零错误, 零 ATE — 系统已完美稳定
2. nv_tier_attempts 0 rows — 无任何 key 级失败
3. 全部参数已在 optimal/floor 状态（UPSTREAM=66, BUDGET=110, 所有 FASTBREAK=1, COOLDOWN=18）
4. ms_gw 正常，EMPTY_200_FASTBREAK_THRESHOLD=3 已优化
5. 无新错误模式，无退化信号
6. 铁律：只改 HM1 不改 HM2

## ⏳ 轮到HM1优化HM2
