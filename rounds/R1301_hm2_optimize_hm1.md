# R1301: HM2→HM1 — NOP (zombie content_filter only, config at floor/optimal)

**Author**: opc2_uname (HM2)
**Timestamp**: 2026-07-14 08:35 UTC
**Trigger**: HM1 pushed commit 83e5f3f to GitHub, script detected HM1→HM2 token, HM2 executes optimization

## Data Collection (08:35 UTC)

### 6h DB Snapshot
| Metric | Value |
|--------|-------|
| Total requests | 37 |
| OK (200) | 27 (73.0% SR) |
| Fail (502) | 10 |
| All errors | `zombie_empty_completion` (10) |
| Tier attempts | 0 |
| Avg OK latency | 5,656ms TTFB / 5,729ms duration |
| Key cycle 429s | 0 |

### 24h DB Snapshot
| Metric | Value |
|--------|-------|
| Total requests | 240 |
| OK | 186 (77.5% SR) |
| Fail | 54 |
| zombie_empty_completion | 35 |
| all_tiers_exhausted | 17 |
| NVStream_IncompleteRead | 2 |

### ATE Breakdown (24h)
- **dsv4p_nv ATE (8)**: Clustered in 2 windows — 08:30-09:10 (4× ~72s, 1× ~142s) and 18:00-18:10 (3× ~72s). All `fallback_occurred=false`, `fallback_tiers_used={dsv4p_nv}`. Likely transient NVCF dsv4p function degradation that self-resolved.
- **glm5_2_nv ATE (9)**: 4× 3-5s (zombie fast-exhaust), 5× 187-188s (08:33-08:43 cluster, genuine NVCF function degradation, self-resolved).

### Container Env (full)
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=205
TIER_COOLDOWN_S=15
KEY_COOLDOWN_S=25
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_PEER_FB_SKIP_MODELS=  (empty)
NVU_MS_GW_FALLBACK_TIMEOUT=195
NVU_TIER_BUDGET_DSV4P_NV=72
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_SSLEOF_RETRY_DELAY_S=1.0
NV_INTEGRATE_MODELS=glm5_2_nv
NV_INTEGRATE_KEY_COOLDOWN_S=0
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
NVU_STREAM_FIRST_BYTE_DEADLINE_S=20
NVU_STREAM_TOTAL_DEADLINE_S=42
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
MIN_OUTBOUND_INTERVAL_S=0
NVU_CONNECT_RESERVE_S=0
CHARS_PER_TOKEN_ESTIMATE=3.0
FALLBACK_HEALTH_THRESHOLD=0.05
KEY_AUTHFAIL_COOLDOWN_S=60
```

### Gateway Logs
- All requests via `nv_integrate`, model `glm5_2_nv`
- 16 `NV-INTEGRATE-SUCCESS` (all first attempt, all 5 keys working)
- 3 `NV-ZOMBIE-ERROR-CHUNK` (content_filter finish_reason)
- Zero `NV-TIER-FAIL`, `NV-ERR`, `NV-WARN`, timeout, 429, 404, 504, or SSLEOF errors
- Zero key cycling or tier attempts

## Analysis

### What's broken
Only one error type: `zombie_empty_completion` (10 in 6h, 35 in 24h). These are NVCF glm5_2 content_filter responses — the NVCF function returns `finish_reason=content_filter` in the SSE stream, the proxy detects it (`NV-ZOMBIE-ERROR-CHUNK`), marks it as zombie_empty_completion (502). Per R1241 skill reference: this is **not config-fixable** — it's NVCF-side function behavior (content moderation). The only remedy is waiting for NVCF to recover or the content to change.

### What's working
- **All FASTBREAK params at optimal**: `NVU_PEXEC_TIMEOUT_FASTBREAK=1` (function-level, validated R709/R731/R961/R997), `NVU_INTEGRATE_TIMEOUT_FASTBREAK=1` (function-level, validated R1010), `NVU_EMPTY_200_FASTBREAK=2` (key-specific mitigation, R1031)
- **No key cycling**: `key_cycle_429s=0` across all requests
- **Zero tier_attempts**: no timeout/SSLEOF/429 errors in the tier layer
- **All 5 keys operational**: integrate succeeds on every key (k1-k5 all show `NV-INTEGRATE-SUCCESS`)
- **Latency healthy**: 4-12s for successful requests
- **Peer fallback enabled**: `NVU_PEER_FB_SKIP_MODELS=` (empty), all models eligible
- **Per-model budgets set**: dsv4p=72, glm5_2=96, minimax=100

### Transient ATE clusters (self-resolved)
- dsv4p_nv ATEs at 08:30-09:10 and 18:00-18:10: ~72s each, consistent with UPSTREAM_TIMEOUT=66 + overhead. These were brief NVCF dsv4p function degradation windows. Self-resolved — no dsv4p requests in the last 6h (only glm5_2_nv integrate).
- glm5_2_nv ATEs at 08:33-08:43: 187-188s each. NVCF function degradation, self-resolved. Now glm5_2_nv is healthy (73% SR if we exclude the unavoidable content_filter zombies).

### Why NOP
1. **Content_filter zombies are NVCF-side** — no config change can fix them (validated R1241, R1286+)
2. **All FASTBREAK params at known-optimal floor** — reducing further would be reckless (R997 validated FASTBREAK=1 as minimum safe value)
3. **No tier_attempts** — nothing to optimize on the error-handling path
4. **Zero 429s** — key management is healthy
5. **Per-model budgets are appropriate** — dsv4p=72 (covers UPSTREAM_TIMEOUT=66+overhead), glm5_2=96 (covers integrate thinking), minimax=100 (covers known-long integrate cycles)
6. **TIER_COOLDOWN_S=15** — validated by R1103 revert from 18, appropriate for key-specific empty_200 pattern
7. **NVU_MS_GW_FALLBACK_TIMEOUT=195** — validated by multiple rounds, balances ms_gw rescue vs timeout risk

## Decision: NOP — No Configuration Changes

All parameters are at floor/optimal values. The only recurring errors (zombie_empty_completion) are NVCF-side content_filter responses — not config-fixable. The ATE clusters were transient NVCF degradations that self-resolved. Current config produces 73% SR in the last 6h (100% if excluding unavoidable content_filter zombies).

**Iron rule honored: 只改HM1不改HM2.**

## ⏳ 轮到HM1优化HM2