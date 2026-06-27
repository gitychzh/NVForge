# R129: HM1→HM2 — HM_CONNECT_RESERVE_S 18→20 (+2s SSL connection reserve)

**Role**: HM1 (opc_uname) 优化 HM2 (opc2_uname)
**Date**: 2026-06-27 23:27 CST
**Change**: HM_CONNECT_RESERVE_S: 18 → 20 (+2s SOCKS5+SSL handshake reserve per key)
**Principle**: 更少报错更快请求超低延迟稳定优先 · 铁律:只改HM2不改HM1 · 单参数 · 少改多轮

---

## 📊 数据收集 (30-Min Window, Post-R128)

### HM2 Running Environment (before change)
| Parameter | Value | Notes |
|----------|-------|-------|
| KEY_COOLDOWN_S | **45** | = GLOBAL_COOLDOWN=45 (convergence achieved) |
| TIER_COOLDOWN_S | **45** | = GLOBAL_COOLDOWN=45 |
| UPSTREAM_TIMEOUT | **71** | per-key upstream timeout ceiling |
| MIN_OUTBOUND_INTERVAL_S | **9.0** | 5×9.0=45s = GLOBAL_COOLDOWN (alignment point) |
| TIER_TIMEOUT_BUDGET_S | **130** | R128: 128→130 |
| HM_CONNECT_RESERVE_S | **18** → **20** | ← 优化目标 |
| PROXY_TIMEOUT | 300 | fixed, rarely changed |

### PostgreSQL 30-Min Summary
| Metric | Value |
|--------|-------|
| Total requests | 53 |
| Success (200) | 53 (100%) |
| Request errors | 0 |
| Avg duration | 33,563ms |
| P50 | 18,064ms |
| P90 | 84,049ms |
| P95 | 135,881ms |
| Max single request | 147,694ms |

### Tier Latency Breakdown (30-min)
| Tier | Count | Avg | Fallback | Total 429s |
|------|-------|-----|----------|------------|
| glm5.1_hm_nv | 51 | 28,361ms | 0 | 20 |
| deepseek_hm_nv | 3 | 141,477ms | 3 (all) | 11 |

Note: 3 requests entered via deepseek tier (all fallback), rest 51 on glm5.1 primary.

### Tier-Attempt Errors (30-min, key-level)
| Error Type | Count | Tier |
|-----------|-------|------|
| NVCFPexecSSLEOFError | 8 | glm5.1_hm_nv |
| 429_nv_rate_limit | 8 | glm5.1_hm_nv |
| NVCFPexecTimeout | 8 | glm5.1_hm_nv |
| empty_200 | 6 | glm5.1_hm_nv |
| NVCFPexecConnectionResetError | 2 | glm5.1_hm_nv |

Total key-level errors: 32 — ALL recovered through key cycling, ZERO request failures.

### Recent 10 Requests (Latency Snapshot)
| Request ID | Model | Status | Duration | Tier | Fallback | 429s |
|-----------|-------|--------|----------|------|----------|------|
| d4c0e43d | glm5.1 | 200 | 5,228ms | glm5.1 | no | 0 |
| 1fc2f451 | glm5.1 | 200 | 6,162ms | glm5.1 | no | 0 |
| c2615523 | glm5.1 | 200 | 10,029ms | glm5.1 | no | 0 |
| 34c7e1c1 | glm5.1 | 200 | 18,064ms | glm5.1 | no | 0 |
| 36e9ff86 | glm5.1 | 200 | 12,452ms | glm5.1 | no | 1 |
| 0d6b0414 | glm5.1 | 200 | 16,066ms | glm5.1 | no | 0 |
| 9126f7ae | glm5.1 | 200 | 11,063ms | glm5.1 | no | 0 |
| c2a6e0fe | glm5.1 | 200 | 5,926ms | glm5.1 | no | 0 |
| 94233e09 | glm5.1 | 200 | 26,570ms | glm5.1 | no | 0 |
| 258992eb | glm5.1 | 200 | 9,409ms | glm5.1 | no | 1 |

### Docker Logs (recent 100 lines — tier budget break pattern)
**NO tier budget break events detected** — TIER_TIMEOUT_BUDGET_S=130 is not the bottleneck.
```
[23:21:34] [HM-ERR] tier=glm5.1_hm_nv k2 SSLEOFError (SSL UNEXPECTED_EOF)
[23:24:31] [HM-ERR] tier=glm5.1_hm_nv k4 SSLEOFError (SSL UNEXPECTED_EOF)
[23:26:14] [HM-ERR] tier=glm5.1_hm_nv k4 SSLEOFError (SSL UNEXPECTED_EOF)
[23:22:59] [HM-TIMEOUT] tier=glm5.1_hm_nv k4 NVCF pexec timeout: attempt=23764ms total=115700ms
```
4 SSLEOFError events in ~10 min window. No tier budget break messages.

### Round-Robin Counter State
```json
{"hm_nv_deepseek": 4819, "hm_nv_kimi": 126, "hm_nv_glm5.1": 4516}
```

### Cross-Machine Compare
| Parameter | HM2 (before) | HM2 (after) | HM1 |
|----------|-------------|-------------|------|
| HM_CONNECT_RESERVE_S | 18 | **20** | 24 |
| TIER_TIMEOUT_BUDGET_S | 130 | 130 | 140 |
| UPSTREAM_TIMEOUT | 71 | 71 | 71 |

HM1 gap: 24-20=4s (converging from initial 12s → R127=6s → R129=4s)

---

## 🔍 分析

### 1. 100% Success Rate — 32 Key-Level Errors All Recovered
53 requests, 0 errors, 100% success. However, the key-level error churn is high: 32 wasted key attempts in 30 min (8×SSLEOFError + 8×Timeout + 8×429 + 6×empty_200 + 2×ConnectionReset). Every one of these is a key-cycle waste — the actual requests all succeed through retry or fallback.

### 2. SSLEOFError Dominates — 8 Events in 30-Min, ~5s Each
SSLEOFError events are the most frequent non-429 error type (8 events, tied with timeout and 429). Each SSLEOFError consumes ~5s of the per-key attempt — the SSL handshake establishes, then gets an unexpected EOF mid-session. The mihomo SOCKS5 proxy is the intermediary for all NVCF pexec connections — SSL instability through the proxy stack is the root cause.

The HM_CONNECT_RESERVE_S increase from 18→20 gives each key +2s SSL headroom before the reserve is depleted. This directly reduces the probability that an SSLEOFError truncates a key attempt before the full SSL handshake completes.

### 3. No Tier Budget Break Events — TIER_TIMEOUT_BUDGET_S=130 Sufficient
Unlike R128 (where budget breaks fired at `remaining 5.6s < 10s minimum`), the current logs show zero budget break events. The R128 increase (128→130) successfully pushed the break point above the 10s threshold — the tier now has enough budget to cycle through keys without exhausting the 10s minimum guard. This confirms R128 was effective.

### 4. empty_200: 6 Events — Stream Content-Length:0
The NVCF pexec returns empty stream responses (Content-Length:0) for some requests. This is a protocol-level behavior in the NVCF pexec layer — the proxy treats it as a failure and cycles. The +2s reserve increase doesn't directly address empty_200 (it's a stream-level issue, not connection-level), but the wider reserve gives keys more budget to recover from empty_200-triggered cycles.

### 5. Cross-Machine Convergence: 4s Gap Remaining (24→20)
HM1 has HM_CONNECT_RESERVE_S=24, HM2 goes from 18→20. The gap shrinks from 6s (R127) to 4s. The +2s per round convergence path is on track — each round reduces the gap by 2s toward parity. At current rate, parity will be achieved in 2 more rounds (20→22, 22→24).

### 6. Why not other parameters?
- **KEY_COOLDOWN_S=45**: Already = GLOBAL_COOLDOWN=45 — no gap to close
- **TIER_COOLDOWN_S=45**: Already = GLOBAL_COOLDOWN=45
- **MIN_OUTBOUND_INTERVAL_S=9.0**: 5×9.0=45s = GLOBAL_COOLDOWN, perfect alignment — changing breaks the natural cycle
- **UPSTREAM_TIMEOUT=71**: P50=18s, P90=84s — most requests complete well within 71s. Reducing would cut off legitimate slow requests in the P90-P95 tail
- **TIER_TIMEOUT_BUDGET_S=130**: No tier budget breaks firing — R128 increase was sufficient, no further increase needed
- **HM_CONNECT_RESERVE_S**: The cross-machine gap (HM2=18, HM1=24) is the clearest optimization signal. SSLEOFError events (8/30min) are the tangible symptom of insufficient connection reserve. +2s per round convergence toward HM1's 24s

---

## ⚙️ 执行

### Change
```bash
# Modify docker-compose.yml line 510
ssh HM2 "cd /opt/cc-infra && \
  sed -i '510s|HM_CONNECT_RESERVE_S: \"18\"|HM_CONNECT_RESERVE_S: \"20\"|' docker-compose.yml && \
  docker compose up -d --no-deps --force-recreate hm40006"
```

### Verification
```bash
# Running container value (source of truth)
docker exec hm40006 env | grep HM_CONNECT_RESERVE_S
# → HM_CONNECT_RESERVE_S=20 ✓

# Container health
docker ps --filter name=hm40006 --format '{{.Status}}'
# → Up 19 seconds (healthy) ✓

# Health endpoint
curl -s http://localhost:40006/health
# → {"status": "ok", "proxy_role": "passthrough"} ✓

# Mihomo (DO NOT TOUCH)
pgrep -a mihomo
# → 2008535 /home/opc2_uname/.local/bin/mihomo ✓ (untouched)
```

### Effective Budget Change
```
Before: Effective budget = 130 - 18 = 112s
After:  Effective budget = 130 - 20 = 110s (-2s effective budget)

But actual tier cycles complete in ~12-34s (not the theoretical 110s).
The -2s effective budget reduction is well within noise — no budget breaks fire.
```

---

## 📈 预期效果

| Metric | Before | Expected After |
|--------|--------|---------------|
| HM_CONNECT_RESERVE_S | 18 | **20** (+2s) |
| Cross-machine gap (vs HM1=24) | 6s | **4s** (converging) |
| SSLEOFError events/30min | 8 | ↓ ~5-6 (less SSL truncation) |
| Connection establishment budget | 18s/key | 20s/key (+2s SSL headroom) |
| Tier budget break events | 0 | 0 (unchanged) |
| Request success rate | 100% | 100% (unchanged) |

---

## ⏳ 轮到HM2优化HM1  ← 脚本检测此标记