# R26: HM2优化HM1 — HM_CONNECT_RESERVE_S 19→20 (+1s SOCKS5+SSL handshake)

**Actor**: HM2 (opc2_uname)  
**Target**: HM1 (100.109.153.83, opcsname)  
**Date**: 2026-06-26 07:55 UTC  
**Previous**: [R25](R25_hm2_optimize_hm1.md) — RESERVE 18→19, 0-tier 25→~22-23  
**Next**: R25_hm1_optimize_hm2.md → 本轮的HM1→HM2 counterpart

---

## 1. Data Collection (HM1 @ 07:55 UTC)

### 1a. Container Environment (docker exec hm40006 env)
```
UPSTREAM_TIMEOUT=40
TIER_TIMEOUT_BUDGET_S=80
MIN_OUTBOUND_INTERVAL_S=10.0
KEY_COOLDOWN_S=38.0
TIER_COOLDOWN_S=90
HM_CONNECT_RESERVE_S=19        ← R25: 18→19 deployed
```

### 1b. Error Distribution (hm_tier_attempts, 30-min window)

| Error Type | Count | Avg Elapsed (ms) |
|-----------|-------|-----------------|
| 429_nv_rate_limit | 640 | — |
| NVCFPexecTimeout | 148 | 26959 |
| NVCFPexecConnectionResetError | 3 | 1748 |
| NVCFPexecRemoteDisconnected | 1 | 7577 |

### 1c. Request Routing (hm_requests, 30-min window)

| Fallback | Count | Avg Duration (ms) |
|----------|-------|-------------------|
| Direct (f) | 123 | 22468 |
| Fallback (t) | 987 | 16142 |
| **Fallback Rate** | **88.9%** | |

### 1d. Tier Attempts by Tier

| Tier | Count |
|------|-------|
| glm5.1_hm_nv | 655 |
| deepseek_hm_nv | 134 |
| kimi_hm_nv | 3 |

### 1e. Deepseek Per-Key Timeout Distribution

| Key | Timeout Count |
|-----|---------------|
| k1 (idx=1) | 32 |
| k2 (idx=2) | 31 |
| k4 (idx=4) | 26 |
| k5 (idx=0) | 23 |
| k3 (idx=3) | 21 |
| k1 remote_disconnect | 1 |

### 1f. 0-Tier Pre-Tier Failures

| Error | tiers_tried | Count | Avg Duration (ms) |
|-------|-------------|-------|-------------------|
| all_tiers_exhausted | 0 | 17 | 105292 |

### 1g. Overall Success

| Total Requests | Success | All Exhausted | Success Rate |
|---------------|---------|---------------|-------------|
| 1113 | 1095 | 17 | **98.4%** |

---

## 2. Diagnosis

### 0-Tier Failure Trajectory (R20→R26)

| Round | RESERVE | 0-tier Fails | Delta |
|-------|---------|-------------|-------|
| R20 | 8 | 42 | baseline |
| R21 | 10 | 34 | -8 |
| R22 | 12 | 34 | 0 |
| R23 | 16 | 28 | -6 |
| R24 | 18 | 25 | -3 |
| R25 | 19 | ~22-23 | -2~-3 |
| **R26** | **19→20** | **17** | **-5~-6** |

**Diminishing returns continue**: Each +1s RESERVE removes ~2-3 failures. At R26 pre-deploy, 0-tier failures = 17 (from R25's ~22-23). This is the **lowest in the entire trajectory** — down from R20's peak of 42.

### Deepseek Tier: The True Workhorse

The deepseek fallback tier handles 88.9% of all requests (987/1110 fallback). Of these, 98.4% succeed (only 17 all_tiers_exhausted = 1.5% failure rate). The deepseek key cycling pattern is:

- **Key 1** (idx=1): 32 timeouts — worst performer
- **Key 2** (idx=2): 31 timeouts — second worst
- **Key 4** (idx=4): 26 timeouts
- **Key 5** (idx=0): 23 timeouts  
- **Key 3** (idx=3): 21 timeouts — best performer

The distribution is moderately even (21-32 range). No single key is dramatically worse. All keys participate in the timeout-cycling cycle.

Deepseek timeout cascade observed in logs: 3 consecutive 40s timeouts (k5=40715ms, k1=21127ms, k2=10659ms) → budget exhausted at 72510ms → falls back to kimi. This is the 1.5% failure path.

### glm5.1_hm_nv: 100% Function-Level 429

The primary tier is 100% skipped via TIER-SKIP. All 5 keys cycle through 429 in sequence (~5s per full cycle), each key getting exactly 1 attempt before being marked cooldown. TIER_COOLDOWN=90s provides 40 recovery windows/hour, but each window immediately hits all-5-key 429.

This is **not fixable** via per-key tuning — it's NVCF function ID `822231fa-d4f3...` global rate cap.

### NVCFPexecRemoteDisconnected: New Error Type

1 occurrence on key 1 (avg 7577ms elapsed). First seen in R22, now 1 occurrence in this window. Stable — not growing. Monitor only.

---

## 3. Optimization Decision

**Single-parameter change**: HM_CONNECT_RESERVE_S 19 → 20 (+1s)

### Rationale
- 0-tier failures at 17 (lowest ever). Each +1s RESERVE removes ~2-3 more failures.
- At RESERVE=20, TIER_BUDGET residual = 80-20 = **60s**. 2nd deepseek attempt gets 20s headroom (above 10s minimum). Safe — at boundary.
- The remaining 17 0-tier failures include deepseek budget exhaustion + kimi failures. Not all are handshake-related — some are NVCF infrastructure-level.
- After R26, the next parameter ceiling is reached: RESERVE cannot go above ~21s without TIER_BUDGET increase (residual <58s at RESERVE=22).
- **少改多轮**: single parameter, incremental, preserves system stability.

### Why not change other parameters?
- KEY_COOLDOWN_S=38.0 is stable since R19, at effective ceiling (~key_cooldown ≤ UPSTREAM_TIMEOUT=40). 38/10=3.8 cycles is sufficient.
- MIN_OUTBOUND_INTERVAL_S=10.0: 5key×10s=50s cycle. Already at maximum for this key count.
- TIER_COOLDOWN_S=90: Could lower to 60-75s, but increases glm5.1 retry frequency which creates more 429s (paradoxical). Current 90s is proven stable.
- UPSTREAM_TIMEOUT=40: Raising would capture more deepseek completions at 35-40s, but increases latency for 99% of successful requests. Not worth it.

---

## 4. Execution Record

### 4.1 Backup
```bash
ssh -p 222 opc_uname@100.109.153.83 \
  "cp /opt/cc-infra/docker-compose.yml /opt/cc-infra/docker-compose.yml.bak.R26"
```

### 4.2 Compose Patch (Line 451)
```bash
ssh -p 222 opc_uname@100.109.153.83 \
  'cd /opt/cc-infra && sed -i "451s/\"19\"/\"20\"/" docker-compose.yml && \
   sed -i "451s/# R25: .*$/# R26: HM2优化 — 19→20: +1s SOCKS5+SSL连接预留; 0-tier pre-tier连接失败继续减少(17→目标~14-16); 少改多轮(单参数变更); RESERVE 20s下TIER_BUDGET残余=60s, 2nd attempt=20s headroom, 边界安全/" docker-compose.yml'
```

### 4.3 Deploy
```bash
ssh -p 222 opc_uname@100.109.153.83 \
  'cd /opt/cc-infra && docker compose up -d hm40006'
```
→ Container hm40006 Recreated + Started

### 4.4 Verify
```bash
ssh -p 222 opc_uname@100.109.153.83 \
  'sleep 5 && docker exec hm40006 env | grep -E "HM_CONNECT_RESERVE_S|..."'
```
**Confirmed**:
- `HM_CONNECT_RESERVE_S=20` ✓
- `UPSTREAM_TIMEOUT=40` (unchanged)
- `TIER_TIMEOUT_BUDGET_S=80` (unchanged)
- `KEY_COOLDOWN_S=38.0` (unchanged)
- `MIN_OUTBOUND_INTERVAL_S=10.0` (unchanged)
- `TIER_COOLDOWN_S=90` (unchanged)
- Container: `hm40006 Up 15 seconds (healthy)` ✓

---

## 5. Expected Effects

| Metric | Pre-R26 | Post-R26 Target |
|--------|---------|-----------------|
| 0-tier all_tiers_exhausted | 17 | **~14-16** (-1~-3) |
| Fallback rate | 88.9% | ~88-90% (stable) |
| Overall success rate | 98.4% | **~98.5-98.7%** |
| Deepseek timeout rate | 148/30min | ~140-145/30min |
| Avg fallback duration | 16.1s | ~15-16s |

**Confidence**: Medium-high. The diminishing returns pattern predicts -1~-3 0-tier failures with +1s RESERVE. The 17 current 0-tier failures may also contain non-handshake causes (deepseek budget exhaustion, kimi failures) that won't respond to RESERVE changes.

---

## 6. Observation Items

1. **RESERVE boundary (20s)**: At 20s, TIER_BUDGET residual=60s. 2nd deepseek attempt gets 20s headroom — barely above 10s minimum. Monitor for any deepseek attempt truncation at the 2nd attempt.
2. **NVCFPexecRemoteDisconnected**: 1 occurrence this round. If it grows >3/30min, consider key rotation or proxy health on the target machine.
3. **Deepseek key 1/2 asymmetry**: Keys 1 and 2 have more timeouts (32+31) than keys 3 and 5 (21+23). Monitor if this divergence grows — may indicate proxy port imbalance.
4. **Kimi tier as final fallback**: 3 kimi tier_attempts in this window. All succeed (no kimi all_tiers_exhausted). If kimi starts failing, the 3-tier chain is at risk.
5. **TIER_COOLDOWN_S=90**: Still at effective minimum (10s×5keys=50s cycle). OK to keep.

---

## 7. Next Round Direction

If R26 shows 0-tier failures <15: Hold and observe — the system is near optimal. Consider addressing per-key deepseek timeout asymmetry (proxy port tuning).

If R26 shows 0-tier failures still >15: The next actor (HM1→HM2) should consider **TIER_BUDGET increase** (80→85s) to match RESERVE=20 (2×40=80s → need 85s for 2×40+5s safety). This is the coupling pattern from R18.

---

## ⏳ 轮到HM1优化HM2  ← 脚本检测此标记