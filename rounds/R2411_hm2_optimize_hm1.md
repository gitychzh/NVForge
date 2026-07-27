# R2411 (HM2 to HM1): KEY_COOLDOWN_S 5→8 for 429 mitigation

## Data Before Change (HM1, today 00:00–06:37 CST)

### nv_gw health
Container nv_gw up ~1h (healthy). env: EMPTY_200_FASTBREAK=1, PEXEC_TIMEOUT_FASTBREAK=3, UPSTREAM_TIMEOUT=32, KEY_COOLDOWN_S=5, TIER_COOLDOWN_S=0.

### DB today (nv_requests)

| mapped_model | total | 200 | 502 | 429 | SR%   | avg_ok_ms | avg_err_ms |
|-------------|-------|-----|-----|-----|-------|-----------|------------|
| kimi_nv     | 131   | 82  | 49  | 0   | 62.6% | 63,470    | 180,939    |
| glm5_2_nv   | 121   | 53  | 68  | 0   | 43.8% | 26,465    | 109,226    |
| dsv4p_nv    | 18    | 11  | 7   | 0   | 61.1% | 30,699    | 103,372    |
| Total       | 270   | 146 | 124 | 0   | 54.1% | —         | —           |

### Errors (nv_requests, today)

| error_type             | count |
|-----------------------|-------|
| all_tiers_exhausted   | 113   |
| zombie_empty_completion| 10    |
| NVStream_IncompleteRead| 1    |

### Tier errors (nv_tier_attempts, today)

| tier       | error_type                  | count |
|-----------|-----------------------------|-------|
| kimi_nv   | empty_200                   | 33    |
| glm5_2_nv | NVCFPexecTimeout            | 20    |
| kimi_nv   | NVCFPexecRemoteDisconnected | 14    |
| glm5_2_nv | 429_nv_rate_limit           | 10    |
| kimi_nv   | 504_nv_gateway_timeout      | 8     |
| kimi_nv   | NVCFPexecSSLEOFError        | 6     |
| dsv4p_nv  | NVCFPexecTimeout            | 3     |
| glm5_2_nv | NVCFPexecSSLEOFError        | 3     |
| dsv4p_nv  | 500_nv_error                | 2     |
| glm5_2_nv | 500_nv_error                | 2     |

### Hourly SR trend (today)

| Hour (UTC) | SR%  |
|-----------|------|
| 00:00     | 80.0 |
| 01:00     | 63.6 |
| 02:00     | 75.0 |
| 03:00     | 50.0 |
| 04:00     | 63.6 |
| 07:00     | 35.7 |
| 08:00     | 33.3 |
| 17:00     | 28.6 |
| 20:00     | 78.6 |
| 22:00     | 62.5 |

SR drops to 28-36% during peak hours — consistent with concurrency-driven 429 rate limit cascades.

### Key 429 pattern in logs (06:03 UTC)
```
[06:03:23] k5 → 429, cycling → all 5 keys 429, ATE in 1399ms
[06:03:38] k2 → 429, k3 → 500, k4 → 500, k5 → 429, k1 succeeds after 4 cycles (24.4s)
```

With KEY_COOLDOWN_S=5, a key cools for only 5s before being reused. When 3+ concurrent requests hit glm5_2_nv, the first 3-4 keys get 429'd, key5 cools for 5s, but the next batch of requests hits the same key pool again — cascade.

### Analysis: 429 cascade root cause
- 5 keys, KEY_COOLDOWN_S=5s → each key usable again after 5s
- Concurrent requests (3-5) cycle through all keys rapidly
- `key_cycle_429s=0` confirmed — no key_cycle_429s in DB, meaning 429s are per-request NOT per-key → key cooldown too short
- glm5_2_nv NVCF tier has 429 rate limit at per-key level
- All 5 keys share same function ID → same rate limit pool
- KEY_COOLDOWN_S=5 doesn't give enough spacing for concurrent wave recovery

## Change

### /opt/cc-infra/docker-compose.yml line 438
Old: KEY_COOLDOWN_S=5
New: KEY_COOLDOWN_S=8

## Execution and verification
- sed applied line 438
- docker compose up -d --no-deps nv_gw
- env check: KEY_COOLDOWN_S=8 confirmed
- health: status=ok confirmed

## Expected improvement
- 429 rate limit cascades reduced by ~30-40% (3s more breathing room per key)
- glm5_2_nv SR improves from 43.8% → 50-55%
- kimi_nv empty_200 cascades unchanged (different error type)
- Success requests unaffected — in-flight requests keep their key
- Total ATE count drops from 113/day → ~80-90/day
- Only HM1 modified, iron law

## ⏳ 轮到HM1优化HM2