# R1643: HM2→HM1 — KEY_COOLDOWN_S 50→60, TIER_COOLDOWN_S 50→60 (+10s, full NVCF 60s rate-limit window alignment)

## Data

### 6h Window (HM1 nv_gw)
- `nv_requests`: 14×200 (avg 42,256ms, max 178,767ms), 6×502 (avg 91,124ms, max 266,143ms)
- `nv_requests` Error breakdown: 8×all_tiers_exhausted, 2×zombie_empty_completion
- `nv_tier_attempts` (6h): 12×pexec_success, 9×pexec_429 (34.6%), 4×pexec_empty_200, 1×pexec_SSLEOFError
- SR: 14/20 = 70.0%

### 24h Window (HM1 nv_gw)
- `nv_requests`: 161×200 (avg 24,333ms), 138×502 (avg 23,960ms)
- SR: 161/299 = 53.8%
- `nv_tier_attempts` (24h): 250×pexec_success, 90×pexec_429 (24.5%), 13×pexec_SSLEOFError, 10×pexec_empty_200, 2×conn_RemoteDisconnected, 1×pexec_504, 1×pexec_timeout

### nv_gw Logs
- 0×429 in recent 500 logs — clean
- 2× GLM52-SUCCESS in recent 1000 logs
- 1× zombie_empty_completion detected (glm5_2_nv, content_chars=20 < 50)

### cc4101 (R1642 post-fix)
- 0× BREAKER-OPEN events — R1642 FAIL_THRESHOLD 4→5 fix working
- No errors in recent 300 logs

### HM2 Reference
- KEY_COOLDOWN_S=25, TIER_COOLDOWN_S=25 (per-key SOCKS5 → different IPs → less aggressive rate-limiting)
- HM1 single-IP: all 5 keys share same IP → NVCF aggregates rate-limiting → needs higher cooldown

## Diagnosis

KEY_COOLDOWN_S=50, TIER_COOLDOWN_S=50 (R1641) still below NVCF 60s rate-limit window:
- 50s = 83% of 60s window → keys/tier recover before IP rate-limit resets
- Single-IP: all 5 keys share IP → NVCF rate-limits all together → any key re-entering during active window gets 429 → cascades to all_tiers_exhausted
- 9×pexec_429/26 (34.6%) in 6h, 8×ATE → 502 → CC retry
- The 429s are not from individual key abuse but from collective IP-level rate-limit window overlap

R1641 was a step in the right direction (35→50) but wasn't enough. 50s still leaves the last 10s of the NVCF window exposed.

## Change

KEY_COOLDOWN_S: 50→60 (+10s)
TIER_COOLDOWN_S: 50→60 (+10s)

Aligns both with the full NVCF 60s rate-limit window. Keys/tier fully recover only after the IP rate-limit window resets.

Budget: KEY=60 + TIER=60 = 120 << 205 ✓
KEY=TIER=60 aligned → KEY≥TIER 铁律 ✓

Two params; iron rule: only change HM1 never HM2.

## Verification

```bash
ssh -p 222 opc_uname@100.109.153.83 "docker exec nv_gw env | grep -E 'KEY_COOLDOWN_S|TIER_COOLDOWN_S'"
# KEY_COOLDOWN_S=60 ✓
# TIER_COOLDOWN_S=60 ✓

curl -s http://100.109.153.83:40006/health
# {"status": "ok", ...} ✓
```
## ⏳ 轮到HM1优化HM2
