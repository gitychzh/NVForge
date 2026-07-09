# R1026: HM2→HM1 — NOP (false trigger, all params at floor/optimal)

## 触发分析
- **cron script output**: `这是我提交的, 不触发`
- **Latest commit**: 9f8920e (opc2_uname, R1025)
- **Verdict**: FALSE TRIGGER / double-dispatch. HM2 committed R1025, cron still dispatched agent.

## 数据收集 (改前必有数据)

### 6h Overall
| Metric | R1025 | R1026 |
|--------|-------|-------|
| Total | 423 | 421 |
| OK | 394 | 392 |
| Fail | 29 | 29 |
| SR | 93.1% | 93.1% |

### 6h By Upstream
| Upstream | R1026 cnt | R1026 OK | R1026 SR | avg_dur | max_dur |
|----------|-----------|----------|----------|---------|---------|
| nvcf_pexec | 114 | 114 | 100% | 13,836ms | 93,363ms |
| nv_integrate | 278 | 272 | 97.8% | 19,770ms | 129,132ms |
| NULL (ATE) | 29 | 6 | 20.7% | 94,811ms | 208,108ms |

### 6h By Model
| Model | Total | OK | SR | avg_dur | max_dur |
|-------|-------|-----|-----|---------|---------|
| glm5_2_nv | 260 | 249 | 95.8% | 23,788ms | 208,108ms |
| dsv4p_nv | 70 | 61 | 87.1% | 19,511ms | 61,249ms |
| kimi_nv | 53 | 52 | 98.1% | 11,439ms | 60,811ms |
| minimax_m3_nv | 38 | 30 | 78.9% | 43,838ms | 159,342ms |

### 6h Error Breakdown
| Error | Count | avg_dur |
|-------|-------|---------|
| all_tiers_exhausted | 23 | 111,046ms |
| NVStream_TimeoutError | 3 | 94,904ms |
| stream_total_deadline | 3 | 69,014ms |

### 6h Tier Attempts
| Tier | Error | Count | avg_ms | max_ms |
|------|-------|-------|--------|--------|
| minimax_m3_nv | IntegrateTimeout | 1 | 90,762 | 90,762 |

### NV-TIER-FAIL (recent logs)
- `dsv4p_nv all 5 keys failed: empty200=1, timeout=0, elapsed=61,244ms` (04:17)
  - FASTBREAK=1 triggered correctly: `NV-EMPTY-FASTBREAK tier=dsv4p_nv 1 consecutive empty_200 ≥ threshold 1`
  - ms_gw fallback attempted: BrokenPipeError after 3,096ms (relay_started=True) — transient

### 6h Fallback
| Fallback | Count | OK |
|----------|-------|-----|
| false | 419 | 390 |
| true | 2 | 2 |

### Recent 10 Requests (latest)
All glm5_2_nv integrate successes (3-6s) + one dsv4p_nv ATE (61,249ms) + one glm5_2_nv NVStreamTimeout (94,360ms). No pexec failures.

### ms_gw Status
- `/health`: OK, all cooldowns empty, 3 models active (glm5_2_ms, dsv4p_ms, kimi_ms)
- rr_counters: ms_glm5_2=117, ms_dsv4p=3
- Healthy, no issues

### HM1 nv_gw Params (all at floor/optimal — identical to R1024/R1025)
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=110
MIN_OUTBOUND_INTERVAL_S=0
KEY_COOLDOWN_S=25
KEY_AUTHFAIL_COOLDOWN_S=60
TIER_COOLDOWN_S=18
NV_INTEGRATE_KEY_COOLDOWN_S=0
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_FALLBACK_HEALTH_THRESHOLD=0.10
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_STREAM_TOTAL_DEADLINE_S=42
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=180
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,dsv4p_nv:dsv4p_ms
NVU_MS_GW_FALLBACK_TIMEOUT=45
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006
NVU_PEER_FALLBACK_TIMEOUT=45
NVU_CONNECT_RESERVE_S=0
```

## 决策

**NOP — 零参数变更。**

1. **数据与R1025一致**: 6h SR 93.1% (exact match), 421 vs 423 total, 29 fail identical
2. **所有参数已在地板/最优**: UPSTREAM=66, MIN_OUTBOUND=0, INTEGRATE_COOLDOWN=0, 所有FASTBREAK=1, CONNECT_RESERVE=0
3. **nvcf_pexec 100% SR**: 114/114 — pexec路径完全健康，连续第4轮零NVCFPexecTimeout
4. **dsv4p_nv ATE**: NVCF function-level empty_200, FASTBREAK=1已最小化浪费 (1 key → fast-break, 61s vs 5 keys × 34s = 170s)
5. **minimax ATE**: 6h仅1次IntegrateTimeout (NVCF function-level), FASTBREAK=1已最小化
6. **ms_gw**: 健康，所有cooldown为空，2次fallback全部成功，1次BrokenPipe为瞬时
7. **铁律**: 只改HM1不改HM2, 改前必有数据, 数据不支持任何变更

## ⏳ 轮到HM1优化HM2