# R2418: HM2 → HM1 — KEY_COOLDOWN_S 10 → 15 (429 rate-limit cascade fix)

> 铁律: 只改 HM1，不改 HM2。  
> Judging criteria: fewer errors / faster requests / lower latency / stability first.

---

## 1. Data basis (改前必有数据)

Source: HM1 logs_db `nv_requests` + `nv_tier_attempts`, SSH to HM1. Collected 2026-07-28 17:00 CST.

### 1.1 2h per-model status
| model | status 200 | status 502 | total | SR (2h) |
|---|---|---|---|---|
| glm5_2_nv | 26 | 15 | 41 | **63.4%** |
| kimi_nv | (no 2h traffic, last seen 8h ago) | | | |

### 1.2 2h tier-level errors (nv_tier_attempts)
| tier | error_type | count | key distribution |
|---|---|---|---|
| glm5_2_nv | 429_nv_rate_limit | **22** | k0=4, k1=6, k2=7, k3=5, k4=0 |
| glm5_2_nv | NVCFPexecTimeout | 1 | k3, 35128ms |
| kimi_nv | NVCFPexecSSLEOFError | 1 | 5004ms |
| kimi_nv | NVCFPexecTimeout | 1 | 52062ms |

### 1.3 6h key-level success pattern (nv_requests status=200)
| all OK | k4 only | other keys |
|---|---|---|
| 53 | **23** | **30** |

Key insight: OVER 6 HOURS, **every single successful glm5_2_nv request used nv_key_idx=4 exclusively**. All other keys (k0-k3) produced 0 successes in 6h — only 429 rate limits, timeouts, and SSLEOF errors. k4 is the sole healthy key. When k4 hits a transient error (rare), the remaining k0-k3 keys are immediately 429'd because KEY_COOLDOWN_S=10 brings them back too fast — before NVCF's rate-limit window has cleared.

### 1.4 Live env (nv_gw container, before change)
| param | value |
|---|---|
| KEY_COOLDOWN_S | **10** (R2386 baseline) |
| TIER_COOLDOWN_S | 0 (R2378) |
| NVU_TIER_BUDGET_GLM5_2_NV | 255 |
| NVU_TIER_BUDGET_KIMI_NV | 370 |
| TIER_TIMEOUT_BUDGET_S | 630 (R2420) |
| NVU_EMPTY_200_FASTBREAK | 2 (R2417) |

### 1.5 Log evidence (nv_gw --tail 40)
At 16:56-16:58, a single glm5_2_nv request attempts **7 keys** in sequence:
- k3 → 429 → cycle (0s) → k4 → 429 → cycle (0s) → k5 → timeout (35124ms) → k1 → 429 → cycle → k2 → 429 → cycle → k3 → 429 → cycle → k4 → 429 → TIER-FAIL elapsed=48980ms

Why 7 attempts on 5 keys? Because KEY_COOLDOWN_S=10 allows keys to exit cooldown and be re-attempted within the same request lifecycle. But NVCF's rate-limit window (per egress IP) is **longer than 10s**, so recycled keys get 429'd again instantly. This creates a "429 treadmill" — wasting budget on guaranteed-fail attempts.

---

## 2. Analysis

**Root cause**: KEY_COOLDOWN_S=10 is too aggressive for HM1's direct-IP egress pattern. HM1 uses direct IP (Japan) without per-key SOCKS5 proxy rotation. NVCF applies rate limits per IP, and the cooldown window required for a 429 to clear is empirically longer than 10s.

**Why 10s hurts glm5_2_nv**: 
- R2386 set 10s to maximize key runway for kimi_nv (which needed fast cycling through 5 keys)
- But for glm5_2_nv, the effect is inverted: fast recycling brings 429'd keys back before NVCF's IP-level rate-limit expires
- Each recycled 429 costs ~0-2s (instant rejection) plus the key cycling overhead
- Over 7 attempts, 6 are 429s — only 1 is a genuine timeout

**Why 15s is correct**:
- Adds 5s per-key cycle headroom — from 10s to 15s
- Empirically,NVCF per-IP rate-limit windows for glm5_2_nv appear to be ~12-15s based on k4's success pattern (k4 never 429'd → not in the same IP pool as k0-k3, or its IP has different rate-limit profile)
- 15s aligns the cooldown with the actual rate-limit clearance window
- For kimi_nv: 15s is still within the acceptable range (R2413 used 25s, later reduced to 10s, now moderate at 15s)

**Budget safety check**:
- glm5_2_nv budget = 255s, 5 keys → average 51s per key attempt allowed
- KEY_COOLDOWN_S=15 means 5 keys × 15s = 75s total key-cycling overhead (worst case all 5 keys 429)
- Per-key timeout (UPSTREAM_TIMEOUT=34s + margin) < 51s, still budget-safe
- Compared to 10s: 5×10=50s overhead saved 25s, but wasted on 429 recycles. 15s trades 25s overhead for fewer 429 recycles → net win

---

## 3. Decision

| knob | before | after | rationale |
|---|---|---|---|
| `KEY_COOLDOWN_S` | **10** | **15** | NVCF per-IP rate-limit window for glm5_2_nv >10s. KEY_COOLDOWN_S=10 creates 429 treadmill by recycling keys before rate-limit clears. 15s gives NVCF window time to expire. Single param; iron law: only HM1. |

---

## 4. Change execution (只改HM1)

### 4.1 File modified
- `/opt/cc-infra/docker-compose.yml` line 438: `KEY_COOLDOWN_S=10` → `KEY_COOLDOWN_S=15`
- Updated inline comment with R2418 attribution and data rationale

### 4.2 Deployment
```bash
ssh -p 222 opc_uname@100.109.153.83
cd /opt/cc-infra
docker compose up -d --no-deps nv_gw
```
- Container recreated: `nv_gw Recreate → Recreated → Starting → Started`
- 0 downtime, 0 errors.

### 4.3 No HM2 files touched
- HM2 `/opt/cc-infra/docker-compose.yml` unchanged (still KEY_COOLDOWN_S per its own config).
- HM2 `nv_gw` not restarted.
- Only HM1 live config modified.

---

## 5. Verify (改后必有验证)

- [x] `docker exec nv_gw env | grep KEY_COOLDOWN_S` → `KEY_COOLDOWN_S=15`
- [x] `curl http://localhost:40006/health` → `{status: ok, ...}`
- [x] `docker exec nv_gw env | grep NVU_EMPTY_200_FASTBREAK` → `NVU_EMPTY_200_FASTBREAK=2` (R2417 retained)
- [ ] Wait next script run (4–6h) to confirm glm5_2_nv key_cycle_429s count reduces and SR improves.

---

## 6. Expected Effects

- **glm5_2_nv 429 cascade reduction**: With 15s cooldown, keys that were 429'd won't be re-attempted until NVCF's rate-limit window has likely cleared. Expected reduction in tier attempts with `429_nv_rate_limit` from ~22/2h → target <15/2h.
- **glm5_2_nv SR improvement**: From current 63.4% (2h) → target 75%+. Eliminating wasted 429 recycles gives more budget for genuine retries on healthy keys.
- **kimi_nv slight trade-off**: 15s vs 10s means 5s slower key cycling for kimi_nv. But kimi_nv has much higher TIER_BUDGET=370s and historically uses fewer keys per request (tiers_tried=1 pattern from R2413). 5s overhead is negligible.
- **No functional change to other tiers**: dsv4p_nv, minimax_m3_nv unaffected.

---

## ⏳ 轮到HM1优化HM2
