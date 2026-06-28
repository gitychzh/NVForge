# R214: HM2→HM1 — 无变更 (全7参数均衡; 30min 98.63% 15ATE全NVCFPexecTimeout+1NVStream 0 429 0 fallback; 40th consecutive R162+R158 validation; 少改多轮; 铁律:只改HM1不改HM2)

## 📊 数据采集 (14:41 UTC, 实时采集)

### Config Snapshot (HM1 hm40006)
```
UPSTREAM_TIMEOUT=70
TIER_TIMEOUT_BUDGET_S=156
KEY_COOLDOWN_S=38
TIER_COOLDOWN_S=38
MIN_OUTBOUND_INTERVAL_S=19.2
HM_CONNECT_RESERVE_S=24
PROXY_TIMEOUT=300
```

### Request Metrics
| Window | Total | Success | % | ATE | 429 | Fallback | P50 | P95 |
|--------|-------|---------|---|-----|-----|----------|-----|-----|
| 30min | 1171 | 1155 | 98.63% | 15 | 0 | 0 | 18.2s | 41.5s |
| 1h | 1241 | 1225 | 98.71% | 15 | 0 | 0 | 18.2s | 41.6s |
| 6h | 1940 | 1920 | 98.97% | 18 | 0 | 0 | 18.2s | 43.8s |

### 24h Segmented (Pitfall #49)
| Segment | Total | Success | ATE | 429 | Fallback |
|---------|-------|---------|-----|-----|----------|
| 0-6h | 1940 | 1920 (98.97%) | 18 | 0 | 0 |
| 6-12h | 768 | 762 (99.22%) | 3 | 0 | 0 |
| 12-24h | 1776 | 1736 (97.75%) | 38 | 4 | 574 |

**Key insight**: 0-12h = ZERO fallback + ZERO 429. The 574 fallback events are entirely in 12-24h (old-regime data from June 27). The 4 429s are also in 12-24h only. Current system is healthy — 24h aggregate is misleading.

### 24h Fallback by Hour
```
2026-06-27 06:00-12:00 UTC: 578 fallback events
2026-06-27 13:00+ → 2026-06-28 14:00+: 0 fallback events (24+ hours of zero fallback)
```
The fallback storm fully subsided at 13:00 UTC on June 27. Since then, 24+ hours of continuous zero-fallback operation.

### Per-Key Distribution (30min, deepseek_hm_nv)
| Key | Total | Success | Avg OK | P95 OK |
|-----|-------|---------|--------|--------|
| k0 | 244 | 244 | 19092ms | 44384ms |
| k1 | 230 | 229 | 20521ms | 44159ms |
| k2 | 224 | 224 | 19927ms | 36147ms |
| k3 | 229 | 229 | 19932ms | 39448ms |
| k4 | 229 | 229 | 20320ms | 38342ms |

**Per-key distribution even** (224-244 requests/key). All keys healthy with 0-1 failures each.

### Error Detail JSONL (all 15 ATE events — 30min)
```
Pattern identical across all events:
- deepseek_hm_nv: 5-6 attempts, 141-157s elapsed
  - NVCFPexecTimeout per-key: 5-60s (NVCF server-side timeout)
  - empty_200: 1 key per event (server returns empty 200)
  - SSLEOFError: occasional k3/k4/k5 (auto-retried)
  - budget_exhausted_after_connect: final attempt 275-2751ms
- kimi_hm_nv: num_attempts=0 across ALL 15 events
  - ZERO budget remaining for fallback tier
- total_attempts: 5-6 (all deepseek, zero kimi)
- startup_retry_attempted: false
```

### Docker Logs (30min window, error/warn only)
```
[HM-TIMEOUT] deepseek_hm_nv k0-k4 NVCFPexecTimeout (5-60s per key)
[HM-TIER-FAIL] deepseek_hm_nv all 5 keys failed → falling back to kimi_hm_nv
[HM-ALL-TIERS-FAIL] All 2 tiers failed → ABORT-NO-FALLBACK (141-157s)
[HM-ERR] deepseek_hm_nv k3/k4/k5 SSLEOFError (auto-retry same key)
```

## 🎯 优化分析

### Bottleneck Identification
**NVCF server-side PexecTimeout storm — ACTIVE and ONGOING (14:35-14:41 UTC).** All 5 deepseek keys experiencing NVCFPexecTimeout simultaneously. The deepseek tier consumes the entire 156s budget:

- Budget consumption: 5-6 keys × ~5-60s NVCF timeouts + CONNECT_RESERVE overhead = 141-157s consumed
- Remaining after deepseek: 0s (156 - 141-157 = exhausted)
- kimi_hm_nv: NEVER receives a single attempt — num_attempts=0 across ALL 15 events
- This confirms Pitfall #41 (fallback tier starvation under NVCFPexecTimeout storms)

### Critical Observation: NVCFPexecTimeout per-key is 5-60s, far below UPSTREAM_TIMEOUT=70
The NVCF server returns PexecTimeout at 5-60s per key, not at the HM-configured 70s. The HM UPSTREAM_TIMEOUT is a SOFT upper bound that the NVCF server never reaches in these failure paths. This means:

- **Reducing UPSTREAM_TIMEOUT below the actual NVCF timeout (~60s) would have NO effect on these ATE events** — the server already rejects before HM's timeout fires
- **The ATE events are NVCF server-side, not HM config-driven**

### Why No Change — Detailed Parameter Evaluation
| Parameter | Status | Reason |
|-----------|--------|--------|
| TIER_TIMEOUT_BUDGET_S=156 | ⚖️ Equilibrium | budget_exhausted_after_connect at 275-2751ms → not reserve issue. Budget fully consumed by NVCF storms. R154 proved diminishing returns beyond 10s threshold |
| UPSTREAM_TIMEOUT=70 | ⚖️ Equilibrium | R158 validated through 40 rounds. NVCFPexecTimeout per-key=5-60s << 70s. Reducing further would not help — server-side timeout fires first |
| KEY_COOLDOWN_S=38 | ⚖️ Equilibrium | KEY=TIER=38 invariant holds (Pitfall #44). 0 429 in 0-12h. Zero back-to-back 429 cycles |
| TIER_COOLDOWN_S=38 | ⚖️ Equilibrium | KEY≥TIER gap=0s confirmed optimal. 0 fallback in 0-12h |
| MIN_OUTBOUND_INTERVAL_S=19.2 | ⚖️ Equilibrium | Per-key even distribution (224-244). No RR counter issues. No back-to-back 429 |
| HM_CONNECT_RESERVE_S=24 | ⚖️ Equilibrium | budget_exhausted_after_connect overhead 275-2751ms << 24s reserve |
| PROXY_TIMEOUT=300 | ⚖️ Equilibrium | No proxy-level errors in any window |

### Why This Is NVCF Server-Side (conclusive)
1. **Error detail JSONL**: all 15 ATE events show kimi num_attempts=0 — config cannot create budget for fallback when primary tier consumes it all
2. **NVCFPexecTimeout per-key**: 5-60s (NVCF server rejects early), far below HM's UPSTREAM_TIMEOUT=70
3. **Multiple keys fail simultaneously**: k0-k4 all experience NVCFPexecTimeout in the same 6-minute window (14:35-14:41 UTC) — this is a server-side outage, not isolated key failures
4. **Same pattern as R191, R198, R202, R213**: all validated as NVCF server-side storms
5. **24h segmented**: 0-12h = 0 fallback, 12-24h = 574 fallback (old-regime, Pitfall #49). Fallback storm fully subsided >24h ago
6. **SSLEOFError on k3/k4/k5**: NVCF server-side connection issues, auto-retried successfully

### Comparison with R213
| Metric | R213 | R214 | Δ |
|--------|------|------|---|
| 30min success | 99.06% | 98.63% | -0.43pp |
| 30min ATE | 12 | 15 | +3 |
| P50 | 18.2s | 18.2s | 0 |
| P95 | 41.5s | 41.5s | 0 |
| 0-12h fallback | 0 | 0 | 0 |
| 0-12h 429 | 0 | 0 | 0 |

R214 shows slightly higher ATE count (15 vs 12) in 30min, with the same NVCFPexecTimeout pattern. The P50/P95 latencies are identical. The 0-12h window remains ZERO fallback + ZERO 429. This is within the expected variance of NVCF server-side storms — the storm intensity fluctuates but the root cause is unchanged.

## ⚖️ 评判标准

- **更少报错**: 30min 15 ATE (NVCF server-side), 0 429, 0 fallback in 0-12h → ✅ NVCF server-side errors cannot be fixed by HM config
- **更快请求**: P50=18.2s, P95=41.5s → ✅ Stable at equilibrium plateau
- **超低延迟**: Per-key P95 under 45s across all keys → ✅ All well within config bounds
- **稳定优先**: 40th consecutive R162+R158 validation, all 7 params at equilibrium → ✅ Stability plateau confirmed
- **铁律**: 只改HM1不改HM2 → ✅ No HM2 local config touched

**Conclusion**: The system is at a confirmed stability plateau. All 7 parameters are at equilibrium. The ongoing NVCFPexecTimeout storm is NVCF server-side and HM config cannot address it. No change is the correct action. This is the 40th consecutive R162+R158 validation.

## ⏳ 轮到HM1优化HM2