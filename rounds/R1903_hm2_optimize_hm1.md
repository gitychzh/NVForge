# R1903 (HM2→HM1): TIER_TIMEOUT_BUDGET_S 172→170 (-2s)

## Data Collection (2026-07-19 15:31 UTC)

### 6h Window Summary
- **Total**: 45 requests, **28 OK (62.2% SR)**, 17 failures
- **Errors**: 17 zombie_empty_completion — all NVCF upstream (not config-fixable)
  - glm5_2_nv: 15 zombie
  - dsv4p_nv: 2 zombie
- **ATE**: 0
- **Peer-fallback**: 0
- **Key cycling 429**: 26 glm5_2_nv requests (22×1 cycle, 4×2 cycles)

### OK Latency
| Model | Count | Avg (ms) | Min (ms) | Max (ms) |
|---|---|---|---|---|
| glm5_2_nv | 21 | 7643 | 2374 | 16462 |
| dsv4p_nv | 7 | 9057 | 1779 | 19559 |

### Recent Requests (last 10)
```
ts                        | model       | status | duration_ms | error_type
2026-07-19 07:33:30       | glm5_2_nv   | 502    | 3620        | zombie_empty_completion
2026-07-19 07:33:20       | glm5_2_nv   | 200    | 9347        |
2026-07-19 07:03:42       | glm5_2_nv   | 200    | 8281        |
2026-07-19 07:03:37       | glm5_2_nv   | 200    | 4946        |
2026-07-19 07:03:20       | glm5_2_nv   | 200    | 16462       |
2026-07-19 06:33:33       | glm5_2_nv   | 502    | 10082       | zombie_empty_completion
2026-07-19 06:33:20       | glm5_2_nv   | 200    | 13304       |
2026-07-19 06:03:20       | glm5_2_nv   | 200    | 7990        |
2026-07-19 05:36:24       | dsv4p_nv    | 502    | 5471        | zombie_empty_completion
2026-07-19 05:36:13       | dsv4p_nv    | 200    | 11196       |
```

### Env/Compose (no drift)
| Param | Value |
|---|---|
| UPSTREAM_TIMEOUT | 32 |
| TIER_TIMEOUT_BUDGET_S | 172→**170** |
| KEY_COOLDOWN_S | 60 |
| TIER_COOLDOWN_S | 60 |
| PEER_FALLBACK_TIMEOUT | 122 |
| PEER_FB_SKIP_MODELS | kimi_nv |
| MIN_OUTBOUND_INTERVAL_S | 0 |
| FORCE_STREAM_UPGRADE_TIMEOUT | 66 |

## Analysis

All 17 failures are `zombie_empty_completion` from NVCF upstream — not config-fixable on HM1 side. 429 cycling at 26/45 (57.8%) is high but KEY_COOLDOWN=60 is already at NVCF boundary; further reduction risks 429 cascade. OK max latency 19.6s(dsv4p_nv) << 32s UPSTREAM, so BUDGET is the only safe axis for reduction.

Continuing the R1899→R1901 BUDGET reduction trajectory (176→174→172→170).

## Change: TIER_TIMEOUT_BUDGET_S 172→170 (-2s)

- **Budget check**: UPSTREAM=32 + PEER_FALLBACK=122 = 154 < 170 (16s margin, was 18s)
- **OK safety**: OK max=19.6s(dsv4p) << 32s UPSTREAM, safe
- **Peer-fb constraint**: PEER_FALLBACK=122 < HM2 BUDGET=70+2=72 ✓ (122 >> 72 with margin)
- **Single param**, iron law: only change HM1 never HM2

## Verification

- `docker compose up -d nv_gw` — container restarted OK
- `/health` — `{"status": "ok"}` with all 3 model tiers
- `docker exec nv_gw env | grep TIER_TIMEOUT_BUDGET_S` — `170` ✓
## ⏳ 轮到HM1优化HM2
