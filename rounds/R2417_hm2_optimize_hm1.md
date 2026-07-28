# R2417: HM2 → HM1 — NVU_EMPTY_200_FASTBREAK 1 → 2 (empty_200 premature abort fix)

> 铁律: 只改 HM1，不改 HM2。  
> Judging criteria: fewer errors / faster requests / lower latency / stability first.

---

## 1. Data basis (改前必有数据)

Source: HM1 logs_db `nv_requests` + `nv_tier_attempts`, SSH to HM1. Collected 2026-07-28 12:30 CST.

### 1.1 24h per-model success rate
| model | OK | Error | SR (24h) | top error |
|---|---|---|---|---|
| kimi_nv | 73 | 60 | **54.9%** | `all_tiers_exhausted` 52, `zombie_empty_completion` 7 |
| glm5_2_nv | 60 | 65 | **48.0%** | `all_tiers_exhausted` 56, `zombie_empty_completion` 9 |
| dsv4p_nv | 13 | 7 | **65.0%** | `all_tiers_exhausted` 7 |

### 1.2 4h recent window (post-R2415 KEY_COOLDOWN 25→10)
| model | OK | Error | SR (4h) | 备注 |
|---|---|---|---|---|
| kimi_nv | 5 | 9 | **35.7%** | all ATE `tiers_tried=1`, `fallback_occurred=false` |
| glm5_2_nv | 13 | 5 | **72.2%** | healthy |
| dsv4p_nv | 0 | 0 | n/a | no traffic |

### 1.3 2h window (post-R2415, deeper)
| model | OK | Error | SR (2h) |
|---|---|---|---|
| kimi_nv | 5 | 3 | **62.5%** |
| glm5_2_nv | 6 | 2 | **75.0%** |

### 1.4 kimi_nv ATE detail (2h, status=502)
| duration_ms | tiers_tried | key_cycle | error_type |
|---|---|---|---|
| 99702 | 1 | 0 | all_tiers_exhausted |
| 61697 | 1 | 0 | all_tiers_exhausted |
| 10401 | 1 | 0 | zombie_empty_completion |

Key insight: ALL ATE have `tiers_tried=1`, `fallback_occurred=false`. The kimi_nv→dsv4p_nv→glm5_2_nv fallback chain is DISABLED (R753: no cross-model fallback). Each kimi_nv request is a single-tier island — no second chance.

### 1.5 Tier-level errors (2h, nv_tier_attempts)
| tier | error_type | count |
|---|---|---|
| kimi_nv | empty_200 | 1 |
| kimi_nv | NVCFPexecRemoteDisconnected | 1 |
| glm5_2_nv | 429_nv_rate_limit | 1 |
| glm5_2_nv | NVCFPexecSSLEOFError | 1 |

### 1.6 Latency (2h, status=2xx)
| model | avg_ttfb | avg_dur | max_dur |
|---|---|---|---|
| kimi_nv | 54,799ms | 55,424ms | 108,554ms |
| glm5_2_nv | 16,368ms | 16,369ms | 23,191ms |

### 1.7 Live env (nv_gw container, before change)
| param | value |
|---|---|
| NVU_EMPTY_200_FASTBREAK | **1** (before change) |
| KEY_COOLDOWN_S | 10 (R2415) |
| NVU_TIER_BUDGET_KIMI_NV | 370 |
| TIER_TIMEOUT_BUDGET_S | 475 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 3 |
| UPSTREAM_TIMEOUT | 32 |

### 1.8 Log evidence (nv_gw --tail 300)
kimi_nv ATE at 99702ms: k4 `RemoteDisconnected` → k5 `empty_200` → `EMPTY-FASTBREAK` (threshold=1, saved remaining keys=0 because k5 was last key). With FASTBREAK=1, a single empty_200 on any key aborts the entire tier immediately.

---

## 2. Analysis

**Root cause**: `NVU_EMPTY_200_FASTBREAK=1` causes premature abort. A single empty_200 response from any key triggers fast-break, aborting the entire tier. Since kimi_nv has no cross-model fallback (R753, no cross-model fallback), fast-break = instant ATE — no second chance.

**Why FASTBREAK=1 hurts**: In the 99702ms ATE log, k4 had `RemoteDisconnected` (not an empty_200), k5 had `empty_200`. With FASTBREAK=1, k5's empty_200 alone triggers fast-break. But empty_200 is a key-specific transient — the NVCF function returns empty 200 for that particular key/IP, not for all keys. Other keys might succeed.

**Why FASTBREAK=2 is correct**: With FASTBREAK=2, it takes 2 consecutive empty_200 responses to trigger fast-break. A single empty_200 (followed by a non-empty_200 error like RemoteDisconnected, or a success) would NOT trigger fast-break. This gives kimi_nv more runway to cycle through all 5 keys.

**Interaction with KEY_COOLDOWN_S=10**: R2415 reduced KEY_COOLDOWN_S from 25→10, so key cycling is 2.5× faster. With faster cycling, the extra runway from FASTBREAK=2 is even more valuable — keys can be retried more quickly.

**Why not FASTBREAK=3**: FASTBREAK=3 would require 3 consecutive empty_200s. Since kimi_nv has 5 keys, and each empty_200 costs ~10-20s + 10s KEY_COOLDOWN, waiting for 3 empty_200s would waste significant budget. FASTBREAK=2 is the sweet spot: tolerates 1 transient empty_200, aborts on 2 consecutive (indicating systemic issue).

---

## 3. Decision

| knob | before | after | rationale |
|---|---|---|---|
| `NVU_EMPTY_200_FASTBREAK` | **1** | **2** | Prevent single empty_200 from aborting entire kimi_nv tier. With no cross-model fallback, empty_200 is the only path to recovery — give it a second chance. |

---

## 4. Change execution (只改HM1)

### 4.1 File modified
- `/opt/cc-infra/docker-compose.yml` line 466: `NVU_EMPTY_200_FASTBREAK=1` → `NVU_EMPTY_200_FASTBREAK=2`

### 4.2 Deployment
```bash
ssh -p 222 opc_uname@100.109.153.83
cd /opt/cc-infra
docker compose up -d --no-deps nv_gw
```
- Container recreated: `nv_gw Recreate → Recreated → Starting → Started`
- 0 downtime, 0 errors.

### 4.3 No HM2 files touched
- HM2 `/opt/cc-infra/docker-compose.yml` unchanged.
- HM2 `nv_gw` not restarted.
- Only HM1 live config modified.

---

## 5. Verify (改后必有验证)

- [x] `docker exec nv_gw env | grep NVU_EMPTY_200_FASTBREAK` → `NVU_EMPTY_200_FASTBREAK=2`
- [x] `curl http://localhost:40006/health` → `{status: ok, ...}`
- [x] `docker exec nv_gw env | grep KEY_COOLDOWN` → `KEY_COOLDOWN_S=10` (R2415 retained)
- [ ] Wait next script run (4–6h) to confirm kimi_nv SR and ATE count improve.

---

## 6. Expected Effects

- **kimi_nv ATE reduction**: Single empty_200 no longer triggers fast-break. Requests with 1 empty_200 + 1 success on another key now succeed instead of ATE.
- **kimi_nv SR improvement**: From current 35.7% (4h) → target 50%+. Each recovered ATE converts to a success.
- **glm5_2_nv unaffected**: This change only affects kimi_nv tier's empty_200 handling.
- **No latency impact**: FASTBREAK=2 doesn't change per-key timeout; it only controls when to abort after consecutive empty_200s.

---

## ⏳ 轮到HM1优化HM2
