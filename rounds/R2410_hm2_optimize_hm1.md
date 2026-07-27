# R2410 (HM2 to HM1): NVU_EMPTY_200_FASTBREAK 2 to 1

## Data Before Change (HM1, 4h ending 05:00 CST)

### nv_gw health
Container nv_gw up 5h healthy. env: PEXEC_FASTBREAK=3, EMPTY_200_FASTBREAK=2, UPSTREAM_TIMEOUT=32, KEY_COOLDOWN=5

### DB 4h (nv_requests)

| mapped_model | total | 200 | 502 | SR%   | avg_ok_s | avg_502_s |
|-------------|-------|-----|-----|-------|----------|-----------|
| glm5_2_nv   | 25    | 14  | 13  | 56.0% | 12.7     | 107.5     |
| kimi_nv     | 22    | 16  | 6   | 72.7% | 40.3     | 135.1     |
| dsv4p_nv    | 18    | 11  | 7   | 61.1% | 30.7     | 103.4     |

### Errors (nv_tier_attempts, 4h)

| error_type           | count | tier     |
|---------------------|-------|----------|
| empty_200           | 4     | kimi_nv  |
| NVCFPexecTimeout    | 3     | dsv4p_nv |
| 429_nv_rate_limit   | 3     | glm5_2_nv|
| 500_nv_error        | 2     | dsv4p_nv |
| NVCFPexecSSLEOFError| 1     | dsv4p_nv |
| RemoteDisconnected  | 1     | kimi_nv  |

### kimi_nv empty_200 cascade proof FASTBREAK=2 no recovery

4h: 4 empty_200 + 5 ATE at 122-158s. Logs prove sequential cross-key:

Event1: [04:00:16] k4 empty_200, [04:01:17] k5 empty_200, [04:01:17] ATE 122s
Event2: [04:55:30] k5 empty_200, [04:56:32] k1 empty_200, [04:56:32] ATE 158s

Two independent events both show empty_200 propagates across ALL keys. FASTBREAK=2 breaks at k2 but k2 ALSO empty_200, so zero recovery benefit. Total saved by FASTBREAK=1 vs 2: ~30s per cascade. One glm5_2_nv and dsv4p_nv have 0 empty_200 in 4h window.

## Change

### /opt/cc-infra/docker-compose.yml line 466
Old: NVU_EMPTY_200_FASTBREAK=2
New: NVU_EMPTY_200_FASTBREAK=1

## Execution and verification
- sed applied line 466
- docker compose up -d --no-deps nv_gw
- env check: EMPTY_200_FASTBREAK=1 confirmed
- health: status=ok confirmed

## Expected improvement
- kimi_nv empty_200 cascade per-event -30s
- 4 fetches in 4h -> ~120s saved
- 200 success unaffected
- Only HM1 modified, iron law

## Card to HM1 optimize HM2 script detection
