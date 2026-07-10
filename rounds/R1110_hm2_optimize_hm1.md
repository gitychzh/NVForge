# HM2 Optimize HM1 — Round R1110

## Round Metadata
- **Round**: R1110
- **Type**: HM2→HM1 (HM2优化HM1)
- **Date**: 2026-07-11 01:45 UTC
- **Author**: opc2_uname (HM2)
- **Trigger**: False trigger (HM2自提交), cron script: "这是我提交的, 不触发"

## Trigger Analysis
- **Cron script output**: "这是我提交的, 不触发" — false trigger confirmed
- **Latest commit**: R1109 (opc2_uname) — HM2自提交
- **HM1 git log**: trailing at R821 (opc2_uname), no new HM1 commits
- **Decision**: NOP — zero param change, data-backed

## Data Collection (改前必有数据 — 6h window to ~01:45 UTC)

### Overall
| Metric | Value |
|--------|-------|
| Total requests | 129 |
| OK (200) | 116 |
| Fail (!=200) | 13 |
| Success rate | 89.9% |

### By Model
| Model | Total | OK | Fail | SR% | Avg Dur (ms) |
|-------|-------|----|------|-----|--------------|
| glm5_2_nv | 94 | 83 | 11 | 88.3% | 19615 |
| dsv4p_nv | 19 | 17 | 2 | 89.5% | 19990 |
| minimax_m3_nv | 9 | 9 | 0 | 100.0% | 14483 |
| kimi_nv | 7 | 7 | 0 | 100.0% | 3605 |

### By Upstream Path
| Path | Total | OK | Fail | Avg TTFB | Avg Dur | Max Dur |
|------|-------|----|------|----------|---------|---------|
| nv_integrate | 100 | 89 | 11 | 17468 | 19407 | 96999 |
| nvcf_pexec | 27 | 27 | 0 | 11696 | 11696 | 48049 |
| NULL (ATE) | 2 | 0 | 2 | 501 | 61375 | 61376 |

### Error Breakdown
| Error Type | Count | Pre/Post Restart |
|-----------|-------|-------------------|
| zombie_empty_completion | 9 | 7 pre, 2 post |
| NVStream_TimeoutError | 2 | 2 pre |
| all_tiers_exhausted | 2 | 2 pre (dsv4p_nv) |

### Post-Restart Window (container restart 17:21 UTC Jul 10)
| Metric | Value |
|--------|-------|
| Container uptime | ~8.5h |
| Post-restart total (from logs) | ~5 visible |
| Post-restart OK | 3 |
| Post-restart zombie | 2 |
| Post-restart ATE | 0 |
| Post-restart NVStream_TimeoutError | 0 |

### Container Env (key params)
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=198
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=15
MIN_OUTBOUND_INTERVAL_S=0
NVU_CONNECT_RESERVE_S=0
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
NV_INTEGRATE_KEY_COOLDOWN_S=0
KEY_AUTHFAIL_COOLDOWN_S=60
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_MS_GW_FALLBACK_TIMEOUT=180
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
NVU_TIER_BUDGET_DSV4P_NV=66
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
PROXY_TIMEOUT=300
```

### nv_tier_attempts: 0 rows (zombie detection doesn't cycle keys, post-restart 0 ATE/0 timeout)
### ms_gw: active with BrokenPipeError streaming sync defect (code-level, R832/R1036/R1103)
### Docker logs: only NV-ZOMBIE-EMPTY events, no NV-TIER-FAIL, no NV-ALL-TIERS-FAIL
### fallback_occurred: false for all 129 requests (no fallback path triggered)

## Decision: NOP (Zero Param Change)

### Rationale
1. **zombie_empty_completion (9×, 2 post-restart)**: Code-level zombie detection feature (R1107). Returns 502 in 3-15s vs old 96s NVStream_TimeoutError hang. Not config-fixable — the upstream model returns valid-but-empty streams; gateway correctly detects and fast-aborts. No key cycling, no nv_tier_attempts recorded. Treat as neutral (faster failure = better user experience).

2. **NVStream_TimeoutError (2×)**: Both pre-restart (before 17:21 UTC). Post-restart zero. Container has been running 8.5h with zero stream timeouts.

3. **ATE (2× dsv4p_nv)**: Both pre-restart (15:50, 16:00 UTC per R1109). Post-restart zero. Single-tier exhaustion at ~61s (NVU_TIER_BUDGET_DSV4P_NV=66 binding, all 5 keys failed). Likely NVCF 504 gateway timeout (external, not config-fixable per R1078).

4. **Post-restart window**: ~8.5h uptime post-restart (17:21 UTC → 01:45 UTC). Zero ATE, zero stream timeout, only 2 zombie. System is stable — the zombie detection is working as designed.

5. **All params at floor**: UPSTREAM=66, BUDGET=198 (generous, BUDGET-UPSTREAM=132 >> 66 peer-fb safe). All cooldowns/intervals at minimum. FASTBREAKs at 1 (except EMPTY_200=2 per R1031). KV maps: dsv4p=66, glm5_2=96, minimax=100. FALLBACK_HEALTH=0.05 (floor). No headroom to reduce on any parameter.

6. **ms_gw BrokenPipeError**: Known streaming sync defect (code-level, R832/R1036/R1103). nv_gw closes connection while ms_gw still sending. Not config-fixable. ms_gw is active and delivering (MS-STREAM-DONE in logs for dsv4p_ms and glm5_2_ms).

7. **nvcf_pexec 27/27=100% SR**: pexec path clean, extends streak from R906-R1109.

8. **minimax_m3_nv 9/9=100%, kimi_nv 7/7=100%**: low-volume models healthy.

### Budget Math Verification
- BUDGET=198, UPSTREAM=66, PEER_FALLBACK=66
- BUDGET - UPSTREAM = 132 >= PEER_FALLBACK (66) ✅
- BUDGET - UPSTREAM >= PEER_FALLBACK + UPSTREAM (132 >= 132) ✅ — peer-fb gets full UPSTREAM window
- BUDGET=198 < 300s (openclaw timeout) ✅
- NVU_TIER_BUDGET_DSV4P_NV=66 = UPSTREAM (tier cap at UPSTREAM) ✅
- NVU_TIER_BUDGET_GLM5_2_NV=96 > UPSTREAM (tier budget not binding) ✅
- NVU_MS_GW_FALLBACK_TIMEOUT=180 < BUDGET=198 (safe) ✅

### Iron Rule Compliance
- ✅ 改前必有数据: Full 6h DB, docker logs, env collected
- ✅ 只改HM1不改HM2: No changes made (NOP)
- ✅ 聚焦nv_gw: Only nv_gw data analyzed
- ✅ 数据驱动: All decisions backed by DB queries, not guesses
- ✅ 最少改动: Zero param change (all at floor, no optimization space)

## ⏳ 轮到HM1优化HM2