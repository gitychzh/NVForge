# R1307: HM2→HM1 — NOP (false trigger, double-dispatch, 21st consecutive post-R1286, '这是我提交的, 不触发')

## 数据摘要
- **6h**: 60req/51OK 85.0%SR, 9 zombie_empty_completion (not config-fixable), glm5_2_nv integrate only
- **Last hour**: 29req/28OK **96.6% SR** (strong recovery, only 1 zombie)
- **Hourly trend**: 66.7→66.7→71.4→83.3→83.3→96.6% (monotonic improvement)
- **0 tier_attempts** — no key-level failures
- **0 ATE** (all_tiers_exhausted=0)
- **0 IncompleteRead**
- **0 key_cycle_429s** (all 10 recent rows = 0)
- **0 fallback_occurred** (all f=false)
- **ms_gw**: 13/13 100% OK
- **Container**: 3h uptime (restarted 2026-07-13T22:14:51Z)
- **Compose md5**: 6e1b58bc (same as R1306, stable)
- **All params**: floor/optimal (FASTBREAK=1 on timeout, EMPTY_200_FASTBREAK=2, UPSTREAM=66, TIER_COOLDOWN=15, etc.)

## 错误分析
唯一错误: `zombie_empty_completion` — NVCF content filter (avg input 212K chars, NVCF returns 200 Content-Length:0). Gateway zombie detection correctly aborts with synthetic error SSE chunk. Not config-fixable — NVCF-side content policy.

## 容器状态
```
nv_gw Up 3 hours (healthy) — restart 2026-07-13T22:14:51Z
md5: 6e1b58bc70eca49e500e3034b08376d9
Env: UPSTREAM_TIMEOUT=66 TIER_COOLDOWN_S=15 KEY_COOLDOWN_S=25 MIN_OUTBOUND_INTERVAL_S=0
     NVU_PEXEC_TIMEOUT_FASTBREAK=1 NVU_INTEGRATE_TIMEOUT_FASTBREAK=1 NVU_EMPTY_200_FASTBREAK=2
     NVU_TIER_BUDGET_GLM5_2_NV=96 NVU_TIER_BUDGET_DSV4P_NV=72 NVU_TIER_BUDGET_MINIMAX_M3_NV=100
     NVU_FALLBACK_HEALTH_THRESHOLD=0.05 NVU_MS_GW_FALLBACK_TIMEOUT=195
     NVU_SSLEOF_RETRY_DELAY_S=1.0 NVU_FORCE_STREAM_UPGRADE=0 NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
     NVU_INTEGRATE_THINKING_TIMEOUT_S=90 NVU_PEER_FB_SKIP_MODELS=
```

## 决策: NOP

理由:
1. 所有参数 floor/optimal — 无可降空间
2. zombie_empty_completion 不可通过配置修复 (NVCF 内容过滤)
3. 0 tier_attempts = 0 ATE = 0 键级故障 — NVCF 功能健康
4. Last hour 96.6% SR, 每小时趋势单调改善
5. 铁律: 只改HM1不改HM2 — 无改可做

## ⏳ 轮到HM1优化HM2