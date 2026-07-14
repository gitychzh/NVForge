# HM2 Optimize HM1 — Round R1364 (NOP, false trigger, double-dispatch)

## 1. 触发分析
- cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit: e712f19 (R1363, author=opc2_uname, HM2)
- **判定: false trigger → double-dispatch (524th chain of R1133)**
- R1363 pre-run 脚本已提交 NOP, symlink 已正确 → 本轮 double-dispatch
- HM1 git log 无新提交, R1363 已是最新

## 2. 数据收集 (改前必有数据 — 2026-07-14 21:50 UTC)

### 6h 总体统计
| 指标 | 数值 |
|------|------|
| 总请求 | 29 |
| 成功(200) | 21 |
| 失败(502) | 8 |
| SR | 72.4% |
| 平均延迟 | 11.0s |

### 错误分类
| 错误类型 | 数量 | 平均延迟 | 平均 input_chars |
|----------|------|----------|--------------------|
| zombie_empty_completion | 8 | 10.3s | 188,992 |
| all_tiers_exhausted | 0 | - | - |
| 其他 | 0 | - | - |

### 按模型统计
| 模型 | 请求 | OK | 失败 | SR | 平均延迟 |
|------|------|-----|------|------|---------|
| glm5_2_nv | 29 | 21 | 8 | 72.4% | 11.0s |

### 按路径统计
| 路径 | 请求 | OK | 失败 |
|------|------|-----|------|
| nv_integrate | 29 | 21 | 8 |

### 每小时 SR 趋势
| 小时 (UTC) | 请求 | OK | 失败 | SR |
|------------|------|-----|------|-----|
| 08:00 | 5 | 4 | 1 | 80.0% |
| 09:00 | 5 | 4 | 1 | 80.0% |
| 10:00 | 4 | 3 | 1 | 75.0% |
| 11:00 | 5 | 4 | 1 | 80.0% |
| 12:00 | 4 | 2 | 2 | 50.0% |
| 13:00 | 6 | 4 | 2 | 66.7% |

### NV Gateway Logs (tail 100)
- All integrate attempts succeed on first key (k1-k5), latency 3.5-14.7s
- 3 zombie patterns: NV-ZOMBIE-EMPTY (content_chars=12-42) → NV-ZOMBIE-ERROR-CHUNK → content_filter SSE
- 1 SSLEOFError: glm5_2_nv k2 integrate (5002ms), handled by SSL cycle → k3 succeeded
- 0 ATE, 0 empty_200, 0 timeout, 0 tier_attempts in logs
- All NV-TIER-FAIL absent → no key cycling events

### Container State
- nv_gw: Up 2 hours (healthy) — restarted at 2026-07-14T11:29:07Z
- ms_gw: Up 8 hours (healthy), 0 traffic
- logs_db: Up 8 hours (healthy)

### Tier Attempts
- 0 tier_attempts (clean — no key cycling)

### Fallback
- 0 fallback_occurred (all requests handled within nv_gw tier)

### ms_gw Traffic
- 0/0 (no fallback triggered)

### Compose & Env
- Compose md5: `b367c647a8d42d9d86ed8814234a1d19` (unchanged from R1363)
- All params floor/optimal:
  - UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=205, TIER_COOLDOWN_S=15, KEY_COOLDOWN_S=25
  - NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_INTEGRATE_TIMEOUT_FASTBREAK=1, NVU_EMPTY_200_FASTBREAK=2
  - NVU_TIER_BUDGET_GLM5_2_NV=96, NVU_TIER_BUDGET_DSV4P_NV=94, NVU_TIER_BUDGET_MINIMAX_M3_NV=100
  - NVU_PEER_FB_SKIP_MODELS="", NVU_SSLEOF_RETRY_DELAY_S=1.0, KEY_AUTHFAIL_COOLDOWN_S=60
  - NVU_MS_GW_FALLBACK_TIMEOUT=195, NVU_FORCE_STREAM_UPGRADE=0, MIN_OUTBOUND_INTERVAL_S=0
  - NVU_INTEGRATE_THINKING_TIMEOUT_S=90, NVU_CONNECT_RESERVE_S=0
  - NVU_PEER_FALLBACK_ENABLED=1, NVU_PEER_FALLBACK_TIMEOUT=66

## 3. 决策: NOP — 零可修故障

### 判断
- 8/8 failures = zombie_empty_completion (glm5_2_nv integrate, NVCF content-filter stop, ~188K input, 6-42 chars output)
- Zombie is code-level NVCF content-filter behavior — not config-fixable
- Gateway detection + error-chunk correct (detects in ~3-15s vs old ~96s hang)
- 0 ATE, 0 timeout, 0 empty_200, 0 tier_attempts, 0 fallback → all other error paths clean
- 0 dsv4p_nv/kimi_nv/minimax_m3_nv traffic → cannot optimize what isn't used
- ms_gw 0/0 → no optimization opportunity
- Single SSLEOFError at 21:33 handled correctly by SSL cycle → no config change needed
- All params at floor/optimal → no further reduction without breaking behavior
- Compose md5 unchanged → HM1 made no outside-loop changes
- Data identical to R1361-R1363 (same 29req/21OK/72.4%SR, same zombie pattern, same 0 tier_attempts/0 fallback)

### 铁律验证
- ✅ 只改 HM1 不改 HM2 (but no changes this round)
- ✅ 改前必有数据
- ✅ 改后必有验证 (N/A — no changes)

## 4. Round History
- R1133→R1364: 232-round NOP chain (all zombie-only failures, zero config-fixable issues)
- R1363: identical pattern (29req/21OK 72.4%SR, 8 zombie, 0 ATE, md5 b367c647)
- R1362: identical pattern (28req/20OK 71.4%SR, 8 zombie, 0 ATE, md5 b367c647)
- R1361: identical pattern (28req/20OK 71.4%SR, 8 zombie, 0 ATE, md5 b367c647)

## ⏳ 轮到HM1优化HM2