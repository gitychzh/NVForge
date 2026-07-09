# R1025: HM2→HM1 — NOP (false trigger, all params at floor/optimal)

## 触发分析
- **cron script output**: `这是我提交的, 不触发`
- **Latest commit**: 716d8b7 (opc2_uname, R1024)
- **Verdict**: FALSE TRIGGER / double-dispatch. HM2 committed R1024, cron still dispatched agent.

## 数据收集 (改前必有数据)

### 6h Overall
| Metric | R1024 | R1025 |
|--------|-------|-------|
| Total | 426 | 423 |
| OK | 398 | 394 |
| Fail | 28 | 29 |
| SR | 93.4% | 93.1% |

### 6h By Upstream
| Upstream | R1025 cnt | R1025 OK | R1025 SR |
|----------|-----------|----------|----------|
| nvcf_pexec | 116 | 116 | 100% |
| nv_integrate | 278 | 272 | 97.8% |
| NULL (ATE) | 29 | 6 | 20.7% |

### 6h By Model
| Model | Total | OK | SR | avg_ms |
|-------|-------|-----|-----|--------|
| glm5_2_nv | 258 | 247 | 95.7% | 19,381ms |
| dsv4p_nv | 70 | 61 | 87.1% | 15,385ms |
| kimi_nv | 55 | 54 | 98.2% | 11,465ms |
| minimax_m3_nv | 40 | 32 | 80.0% | 18,924ms |

### 6h Error Breakdown
| Error | Count |
|-------|-------|
| all_tiers_exhausted | ~22 |
| NVStream_TimeoutError | ~3 |
| stream_total_deadline | ~4 |

### NV-TIER-FAIL (recent)
- `dsv4p_nv all 5 keys failed: empty200=1, timeout=0, elapsed=61,100ms` (03:38)
- `dsv4p_nv all 5 keys failed: empty200=1, timeout=0, elapsed=61,244ms` (04:17)

### Tier Attempts 6h
| Tier | Error | Count | avg_ms | max_ms |
|------|-------|-------|--------|--------|
| kimi_nv | empty_200 | 1 | - | - |
| minimax_m3_nv | IntegrateTimeout | 1 | 90,762 | 90,762 |

### ms_gw Status
- `/health`: OK, all cooldowns empty, 3 models active (glm5_2_ms, dsv4p_ms, kimi_ms)
- rr_counters: ms_glm5_2=117, ms_dsv4p=3
- Healthy, no issues

### HM1 nv_gw Params (all at floor/optimal — identical to R1024)
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
```

## 决策

**NOP — 零参数变更。**

1. **数据与R1024一致**: 6h SR 93.1% vs 93.4%, ATE 29 vs 28, 错误分布相同
2. **所有参数已在地板/最优**: UPSTREAM=66, MIN_OUTBOUND=0, INTEGRATE_COOLDOWN=0, 所有FASTBREAK=1
3. **nvcf_pexec 100% SR**: 116/116 — pexec路径完全健康
4. **dsv4p_nv ATE**: NVCF function-level empty_200, 非本地配置可修复 (FASTBREAK=1已最小化浪费)
5. **ms_gw**: 健康，所有cooldown为空，无优化空间
6. **铁律**: 只改HM1不改HM2, 改前必有数据, 数据不支持任何变更

## ⏳ 轮到HM1优化HM2