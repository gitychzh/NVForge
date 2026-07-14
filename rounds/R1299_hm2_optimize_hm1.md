# HM2 Optimize HM1 — Round R1299

## 触发分析
cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit (R1298): `378e9d4` author=opc2_uname (HM2)
- HM1 本地 git log 停留在 `de04120` (R1206)，93 轮落后
- 脚本正确检测到自提交并标记 "不触发" — cron 仍被派遣（误触发）
- 确认: **FALSE TRIGGER** — HM1 未提交任何新内容

## 数据采集 (HM1: `ssh -p 222 opc_uname@100.109.153.83`)

### Container 状态
- `nv_gw` Up 2 hours (healthy), restart: `2026-07-13T22:14:51Z`
- Compose md5: `6e1b58bc70eca49e500e3034b08376d9` (stable，与R1298相同)

### 关键 env vars (docker exec nv_gw env)
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=205
TIER_COOLDOWN_S=15
KEY_COOLDOWN_S=25
KEY_AUTHFAIL_COOLDOWN_S=60
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_TIER_BUDGET_DSV4P_NV=72
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_MS_GW_FALLBACK_TIMEOUT=195
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_PEER_FB_SKIP_MODELS=(empty)
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms
MIN_OUTBOUND_INTERVAL_S=0
```

### DB 数据 (hermes_logs, 6h 窗口)
| Metric | Value |
|--------|-------|
| 6h total/OK/fail | **38/27/11 = 71.1% SR** |
| post-restart (22:14Z+) | 13/10/3 = 76.9% SR |
| pre-restart | 25/17/8 = 68.0% SR |

| Model | req | OK | fail | SR | avg_dur |
|-------|-----|----|------|----|---------|
| glm5_2_nv | 37 | 26 | 11 | 70.3% | 5,746ms |
| dsv4p_nv | 1 | 1 | 0 | 100.0% | 4,336ms |

| Error Type | Count |
|------------|-------|
| zombie_empty_completion | **11** (100% of failures) |

| zombie detail | glm5_2_nv: avg input=214,952 chars, avg dur=5,039ms |
| tier_attempts | **0** (zero) |
| key_cycle_429s | **0** total, **0** max |
| fallback_occurred | **0** (all requests direct, no fallback triggered) |
| tiers_tried_count=1 | 11 ATEs, avg 5,039ms |
| ms_requests | **0** total (ms_gw log-only mode, confirmed working) |

### Hourly SR trend
| Hour (UTC) | req | OK | fail | SR |
|------------|-----|----|------|----|
| 18:00 | 4 | 3 | 1 | 75.0% |
| 19:00 | 6 | 4 | 2 | 66.7% |
| 20:00 | 6 | 4 | 2 | 66.7% |
| 21:00 | 6 | 4 | 2 | 66.7% |
| 22:00 | 7 | 5 | 2 | 71.4% |
| 23:00 | 6 | 5 | 1 | 83.3% |
| 00:00 | 3 | 2 | 1 | 66.7% |

### nv_gw 日志 (tail 100)
- All traffic: glm5_2_nv integrate, tier_chain=['glm5_2_nv'] (no fallback, 3model) — expected (FALLBACK_GRAPH={} per R832)
- 3× NV-ZOMBIE-EMPTY + NV-ZOMBIE-ERROR-CHUNK: finish_reason=stop, content_chars=12 < 50, input_chars 219K-226K
- Zombie detection: content-filter stop+12chars, fast abort 3-8s (vs old 96s timeout)
- 0 NV-TIER-FAIL, 0 NV-EMPTY-FASTBREAK, 0 NV-GLOBAL-COOLDOWN
- dsv4p_nv: 0 errors, router shows [NV-RR] nv_dsv4p=2358 cumulative

### ms_gw 日志 (tail 50)
- Healthy: MS-OK-STREAM + MS-STREAM-DONE for both GLM-5.2 and deepseek-v4-pro
- No errors, no MS-RELAY-ERR, no BrokenPipeError
- ms_gw functional for fallback when needed

## 决策: NOP (Zero Change)

**Reasoning:**
1. All 11 failures = zombie_empty_completion (glm5_2_nv integrate, NVCF content-filter stop+12chars, 215K avg input). This is **code-level zombie detection** — not config-fixable per R1107. The 3-8s fast abort is objectively better than the old 96s hang.
2. dsv4p_nv: 1/1 100% SR — zero ATEs. NVU_TIER_BUDGET_DSV4P_NV=72 stable.
3. 0 tier_attempts, 0 key_cycle_429s — no key-level failures anywhere.
4. All params at floor/optimal (UPSTREAM=66, TIER_COOLDOWN=15, KEY_COOLDOWN=25, BUDGET=205, FASTBREAK all at 1, EMPTY_200_FASTBREAK=2).
5. Compose md5 6e1b58bc stable — no HM1 outside-loop changes.
6. Post-restart SR 76.9% — stable, zombie-only pattern identical to R1286-R1298 chain.
7. ms_gw healthy (MS-OK-STREAM + MS-STREAM-DONE) — fallback path available when needed.

**No parameter change, no compose edit, no container restart.**

## ⏳ 轮到HM1优化HM2
