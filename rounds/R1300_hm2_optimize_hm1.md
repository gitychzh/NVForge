# R1300: HM2→HM1 — NOP (false trigger, double-dispatch, 14th consecutive post-R1286, '这是我提交的, 不触发')

## 触发分析
cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit (R1299): `c4cfcf4` author=opc2_uname (HM2)
- HM1 未提交新内容 — 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — FALSE TRIGGER (double-dispatch, 14th consecutive NOP since R1286)
- Symlink 已指向 R1299

## 数据采集 (HM1: ssh -p 222 opc_uname@100.109.153.83)

### Container 状态
- nv_gw: Up 2 hours (healthy), restart: 2026-07-14T06:14:51+08 (22:14 UTC)
- Compose md5: 6e1b58bc (稳定，与 R1286-R1299 一致)
- ms_gw: Up, healthy (MS-OK-STREAM + MS-STREAM-DONE)

### 关键 env vars (docker exec nv_gw env)
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=205
NVU_TIER_BUDGET_DSV4P_NV=72
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
TIER_COOLDOWN_S=15
KEY_COOLDOWN_S=25
KEY_AUTHFAIL_COOLDOWN_S=60
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_MS_GW_FALLBACK_TIMEOUT=195
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_PEER_FB_SKIP_MODELS=(empty)
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms
MIN_OUTBOUND_INTERVAL_S=0
NVU_CONNECT_RESERVE_S=0
NV_INTEGRATE_KEY_COOLDOWN_S=0
NVU_STREAM_FIRST_BYTE_DEADLINE_S=20
NVU_STREAM_TOTAL_DEADLINE_S=42
```

### DB 数据 (hermes_logs, 6h 窗口)
| Metric | Value |
|--------|-------|
| 6h total/OK/fail | **37/26/11 = 70.3% SR** |
| All models | glm5_2_nv (37, 100% integrate) |
| dsv4p_nv | 0 traffic |
| kimi_nv | 0 traffic |
| minimax_m3_nv | 0 traffic |

| Error Type | Count | Model | Avg Dur |
|------------|-------|-------|---------|
| zombie_empty_completion | 11 | glm5_2_nv | 5,039ms |

| tier_attempts | 0 (zero) |
| key_cycle_429s | 0 total, 0 max |
| fallback_occurred | 0 (all requests direct, no fallback) |
| tiers_tried_count | 1 (all 11 ATEs single-tier) |
| fallback_actually_attempted | false (all 11) |
| ms_requests | 0 (log-only mode, confirmed working) |

### Hourly SR trend
| Hour (UTC) | req | OK | fail | SR |
|------------|-----|----|------|----|
| 18:00 | 3 | 2 | 1 | 66.7% |
| 19:00 | 6 | 4 | 2 | 66.7% |
| 20:00 | 6 | 4 | 2 | 66.7% |
| 21:00 | 6 | 4 | 2 | 66.7% |
| 22:00 | 7 | 5 | 2 | 71.4% |
| 23:00 | 6 | 5 | 1 | 83.3% |
| 00:00 | 3 | 2 | 1 | 66.7% |

### nv_gw 日志 (tail 100)
- All traffic: glm5_2_nv integrate, tier_chain=['glm5_2_nv'] (no fallback, 3model)
- 13× NV-INTEGRATE-SUCCESS (first-key, avg ~2-3s integrate latency)
- 6× NV-ZOMBIE-EMPTY + NV-ZOMBIE-ERROR-CHUNK: finish_reason=stop, content_chars=12 < 50, input_chars 219K-226K
- 0 NV-TIER-FAIL, 0 NV-EMPTY-FASTBREAK, 0 NV-GLOBAL-COOLDOWN
- Zombie detection: fast abort 3-8s (vs old 96s timeout), sent content_filter error SSE chunk
- dsv4p_nv: 0 traffic, 0 errors

### ms_gw 日志 (tail 200)
- 6× MS-OK-STREAM + MS-STREAM-DONE: ZHIPUAI/GLM-5.2 (5 OK) + deepseek-ai/deepseek-v4-pro (1 OK)
- 1× MS-STREAM-CLIENT-EOF (BrokenPipeError, known streaming defect, not config-fixable)
- ms_gw functional for fallback when needed

## 决策: NOP (Zero Change)

**Reasoning:**
1. All 11 failures = zombie_empty_completion (glm5_2_nv integrate, NVCF content-filter stop+12chars, 219K-226K input). This is **code-level zombie detection** — not config-fixable per R1107. The 3-8s fast abort is objectively better than the old 96s hang.
2. All 26 successes = first-key integrate, healthy latency ~5,746ms avg — no performance degradation.
3. 0 tier_attempts, 0 key_cycle_429s, 0 NV-TIER-FAIL — no key-level, tier-level, or network-level failures.
4. All params at floor/optimal (UPSTREAM=66, TIER_COOLDOWN=15, KEY_COOLDOWN=25, BUDGET=205, all FASTBREAK optimal).
5. Compose md5 6e1b58bc stable — no HM1 outside-loop changes.
6. dsv4p_nv 0 traffic — no ATE or tier-budget issues to address.
7. ms_gw healthy (MS-OK-STREAM + MS-STREAM-DONE) — fallback path available.

**No parameter change, no compose edit, no container restart.**

## ⏳ 轮到HM1优化HM2
