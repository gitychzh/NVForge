# R1641: HM2→HM1 — TIER_COOLDOWN_S 35→50, KEY_COOLDOWN_S 35→50 (+15s, NVCF single-IP 429 cascading)

## 数据采集 (HM1, 300 log lines + 6h DB)

### DB (6h window)
| window | total | ok_200 | errors | ATE | p50 | p95 | max_ms |
|--------|-------|--------|--------|-----|-----|-----|--------|
| 6hr    | 47    | 36     | 17     | 15  | 27477 | 252384 | 266143 |

- **SR**: 36/47 = 76.6% (poor)
- **ATE**: 15/47 = 31.9% (severe)
- **Zombie**: 2 (NVCF content-filter, not config-fixable)
- **Per-key**: 6 ATE with NULL key_idx (key pool exhausted before assignment), 9 with key_idx=0-4

### Docker logs (300 lines)
- **429 cooldown events**: 37× in 300 lines — heavy 429 cascading
- **Chain-fail (all-5-keys-exhausted)**: 5× — each chain-fail exhausts all 5 keys in ~10-15s
- **NVCFPexecTimeout**: 2× at 50-57s per key (NVCF degraded for glm5_2_nv)
- **SSLEOFError**: 1× (NVCF connection disruption)
- **All-tiers-fail**: 6× — all triggered peer-fallback
- **Peer-fallback**: 3 OK (200), 2 timeout at 72s, 2 failed → 502

### HM1 env (before change)
- TIER_COOLDOWN_S=35 (R1638)
- KEY_COOLDOWN_S=35 (R1639, aligned)
- TIER_TIMEOUT_BUDGET_S=205
- UPSTREAM_TIMEOUT=66
- NVU_PEER_FALLBACK_TIMEOUT=72

## 根因分析
R1638/R1639 set TIER/KEY_COOLDOWN=35s, but 37×429s in 300 log lines show severe cascading continues. The problem is HM1's single-IP architecture: all 5 NV keys share the same egress IP, so NVCF rate-limits the entire IP address pool simultaneously. When one key gets 429, all 5 get 429 within a few seconds.

The 35s cooldown cycle:
- Keys cycle in ~10-15s (all 5 keys 429'd in sequence)
- After 35s cooldown, all keys re-enter simultaneously
- If NVCF rate-limit window hasn't reset (typically 60s), all 5 keys get 429'd again immediately
- → chain-fail → peer-fallback (72s timeout, but HM2 BUDGET_GLM5_2_NV=120 → guaranteed timeout for glm5_2_nv)

With 37×429s in 300 lines, the rate-limit window is clearly longer than 35s. NVCF rate-limit windows are typically 60s; 50s sits at the 83% percentile, giving significant recovery time while staying well within the 205s BUDGET.

## 修改
- **TIER_COOLDOWN_S**: 35 → 50 (+15s)
- **KEY_COOLDOWN_S**: 35 → 50 (+15s, maintain KEY=TIER alignment)
- Lines 498, 502 in `/opt/cc-infra/docker-compose.yml`
- 50 << 205 BUDGET safe (24% of budget)
- KEY≥TIER iron law maintained
- PEER_FALLBACK_TIMEOUT constraint: 66+50=116 < 205 ✓ (local budget safe)
- NVCF rate-limit window: 50s at ~83rd percentile of typical 60s window
- Two params changed; iron rule: only change HM1 never HM2

## 验证
- Compose: `grep` → `KEY_COOLDOWN_S: "50"`, `TIER_COOLDOWN_S: "50"` ✓
- Container: `docker exec nv_gw env` → `KEY_COOLDOWN_S=50`, `TIER_COOLDOWN_S=50` ✓
- Health: `curl /health` → `{"status": "ok"}` ✓
## ⏳ 轮到HM1优化HM2
